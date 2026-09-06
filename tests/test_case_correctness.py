"""PR-02 financial regression tests use only synthetic, isolated SQLite data."""
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone, timedelta
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

import database as db
from case_schema import backfill
from case_service import CaseService, CaseConflict
from main import app

NOW = datetime(2026, 9, 6, 12, tzinfo=timezone.utc)


@pytest.fixture
def service():
    db.init_db()
    with db.get_connection() as conn:
        conn.execute("""INSERT INTO cases(case_id,loan_id,debtor_cif,full_name,phone_e164,product_code,dpd,
            overdue_amount,total_balance,status,experiment_arm,created_at,updated_at,data_origin)
            VALUES('C1','L1','D1','Synthetic customer','+84000000000','LOAN',10,1000,10000,'IN_TREATMENT','A',?,?,'SYNTHETIC')""", (NOW.isoformat(), NOW.isoformat()))
        backfill(conn)
    return CaseService(lambda: NOW)


def command(s, kind, payload, command_id=None, version=None):
    return s.execute("C1", command_id or str(uuid4()), db.get_case_by_id("C1")["case_version"] if version is None else version, kind, payload)


def snapshot(amount=1000, version=1, loan="L1", at=NOW):
    return {"loan_id": loan, "debtor_cif": "D1", "overdue_amount": amount,
            "outstanding_principal": 9000, "outstanding_interest": 1000,
            "dpd": 10 if amount else 0, "source_version": version, "as_of": at.isoformat()}


def balance(s, amount=1000, version=1, loan="L1"):
    return command(s, "balance", {"snapshots": [snapshot(amount, version, loan)]})


def rows(table):
    conn = db.get_connection()
    try:
        return [dict(r) for r in conn.execute(f"SELECT * FROM {table}")]
    finally:
        conn.close()


def promise(s):
    command(s, "wrapup", {"outcome": "PTP_AGREED", "ptp_amount": 1000,
        "ptp_date": (NOW + timedelta(hours=1)).isoformat(), "guardrail_token": "demo"})
    return rows("ptps")[0]["ptp_id"]


def payment(s, amount=400, ptp=None, event="P1", at=NOW):
    return command(s, "payment", {"event_id": event, "loan_id": "L1", "debtor_cif": "D1", "kind": "POSTED", "amount_vnd": amount, "occurred_at": at.isoformat(), "ptp_id": ptp})


def test_partial_payment_holds_contact_without_cure_or_balance_guess(service):
    result = payment(service)
    assert result["lifecycle"] == "OPEN"
    assert result["contact_hold_reason"] == "PAYMENT_RECONCILIATION"
    assert db.get_case_by_id("C1")["overdue_amount"] == 1000
    balance(service, 600)
    assert db.get_case_by_id("C1")["overdue_amount"] == 600
    assert db.get_case_by_id("C1")["resolution"] is None


def test_clear_arrears_not_loan_settlement_or_ptp_kept(service):
    promise(service)
    result = balance(service, 0)
    assert result["resolution"] == "CURED"
    assert db.get_case_by_id("C1")["total_balance"] == 10000
    assert rows("ptps")[0]["status"] == "SCHEDULED"


def test_wrapup_idempotent_and_stale_conflicts_do_not_reopen(service):
    payload = {"outcome": "BUSY_NO_ANSWER"}
    first = command(service, "wrapup", payload, "W1", 0)
    replay = command(service, "wrapup", payload, "W1", 0)
    assert first["case_version"] == replay["case_version"] == 1
    assert replay["replayed"] and len(rows("case_interactions")) == 1
    with pytest.raises(CaseConflict):
        command(service, "wrapup", {"outcome": "REFUSED"}, "W1", 1)
    balance(service, 0)
    for version in (0, db.get_case_by_id("C1")["case_version"]):
        with pytest.raises(CaseConflict):
            command(service, "wrapup", payload, version=version)
    assert db.get_case_by_id("C1")["lifecycle"] == "CLOSED"


def test_multiple_exposures_all_required_for_cure(service):
    command(service, "link_exposure", {"loan_id": "L2", "debtor_cif": "D1"})
    assert balance(service, 0)["lifecycle"] == "OPEN"
    assert balance(service, 500, loan="L2")["lifecycle"] == "OPEN"
    assert db.get_case_by_id("C1")["overdue_amount"] == 500
    assert balance(service, 0, version=2, loan="L2")["lifecycle"] == "CLOSED"
    assert len(rows("cases")) == 1
    assert db.get_case_by_id("C1")["loan_id"] == "L1"


def test_wrong_debtor_link_rejected(service):
    with pytest.raises(CaseConflict):
        command(service, "link_exposure", {"loan_id": "L2", "debtor_cif": "D2"})
    assert len(rows("case_exposures")) == 1


def test_late_snapshot_and_conflicting_source_version(service):
    balance(service, 500, 2)
    balance(service, 0, 1)
    assert db.get_case_by_id("C1")["overdue_amount"] == 500
    with pytest.raises(CaseConflict):
        balance(service, 0, 2)
    assert db.get_case_by_id("C1")["overdue_amount"] == 500


@pytest.mark.parametrize("change", [
    {"overdue_amount": -1}, {"overdue_amount": 1.5}, {"overdue_amount": "NaN"},
    {"as_of": "2026-09-06T12:00:00"}, {"as_of": (NOW - timedelta(hours=1)).isoformat()},
    {"as_of": (NOW + timedelta(hours=1)).isoformat()}, {"debtor_cif": "D2"},
    {"dpd": -1}, {"source_version": True},
])
def test_bad_core_evidence_atomic_rejection(service, change):
    with pytest.raises(ValueError):
        command(service, "balance", {"snapshots": [{**snapshot(), **change}]})
    assert db.get_case_by_id("C1")["case_version"] == 0
    assert rows("case_transition_log") == []


def test_duplicate_payment_event_and_conflict(service):
    payment(service)
    balance(service, 600)
    command(service, "reconcile", {"reason": "Core reconciled"})
    version = db.get_case_by_id("C1")["case_version"]
    replay = payment(service)
    assert replay["replayed"] and replay["case_version"] == version
    assert replay["contact_hold_reason"] is None
    assert len(rows("payment_ledger")) == 1
    with pytest.raises(CaseConflict):
        payment(service, 500)
    assert rows("payment_ledger")[0]["amount_vnd"] == 400


def test_ptp_partial_kept_and_full_reversal(service):
    ptp = promise(service)
    payment(service, ptp=ptp)
    assert rows("ptps")[0]["status"] == "PARTIALLY_KEPT"
    payment(service, 600, ptp, "P2")
    assert rows("ptps")[0]["status"] == "KEPT"
    balance(service, 0)
    result = command(service, "payment", {"event_id": "R2", "loan_id": "L1", "debtor_cif": "D1", "kind": "REVERSED", "amount_vnd": 600, "occurred_at": NOW.isoformat(), "reverses_event_id": "P2"})
    assert result["lifecycle"] == "PROBATION"
    assert rows("ptps")[0]["status"] == "PARTIALLY_KEPT"
    with pytest.raises(CaseConflict):
        command(service, "reconcile", {"reason": "review"})
    balance(service, 600, 2)
    result = command(service, "reconcile", {"reason": "Core confirms reversal and remaining arrears"})
    assert result["lifecycle"] == "OPEN" and result["contact_hold_reason"] is None


def test_break_requires_completeness_and_late_delivery_corrects_outcome(service):
    ptp = promise(service)
    service.clock = lambda: NOW + timedelta(hours=2)
    # Passing time alone or unrelated balance does not prove a broken promise.
    command(service, "wrapup", {"outcome": "BUSY_NO_ANSWER"})
    assert rows("ptps")[0]["status"] == "SCHEDULED"
    command(service, "observe_ptp", {"ptp_id": ptp, "payments_complete_through": (NOW + timedelta(hours=2)).isoformat()})
    assert rows("ptps")[0]["status"] == "BROKEN"
    payment(service, 1000, ptp, at=NOW + timedelta(minutes=30))
    assert rows("ptps")[0]["status"] == "KEPT"
    assert db.get_debtor_behavioral_metrics("D1", "C1")["ptp_kept_rate"] == 1


def test_late_payment_not_on_time_kept(service):
    ptp = promise(service)
    service.clock = lambda: NOW + timedelta(hours=2)
    payment(service, 1000, ptp, at=NOW + timedelta(hours=2))
    command(service, "observe_ptp", {"ptp_id": ptp, "payments_complete_through": (NOW + timedelta(hours=2)).isoformat()})
    assert rows("ptps")[0]["status"] == "BROKEN"
    assert rows("ptps")[0]["paid_vnd"] == 1000
    assert rows("ptps")[0]["on_time_vnd"] == 0


def test_reversal_before_original_rejected_without_side_effects(service):
    with pytest.raises(CaseConflict):
        command(service, "payment", {"event_id": "R1", "loan_id": "L1", "debtor_cif": "D1", "kind": "REVERSED", "amount_vnd": 100, "occurred_at": NOW.isoformat(), "reverses_event_id": "missing"})
    assert rows("payment_ledger") == []
    assert db.get_case_by_id("C1")["case_version"] == 0


def test_concurrent_commands_only_one_wins(service):
    def attempt(n):
        try:
            command(service, "wrapup", {"outcome": "REFUSED"}, str(n), 0)
            return True
        except CaseConflict:
            return False
    with ThreadPoolExecutor(max_workers=2) as pool:
        assert sorted(pool.map(attempt, range(2))) == [False, True]
    assert len(rows("case_interactions")) == 1
    assert len(rows("case_transition_log")) == 1


def test_migration_idempotent_and_legacy_promise_not_evidence(service):
    with db.get_connection() as conn:
        conn.execute("DELETE FROM case_exposures")
        conn.execute("UPDATE cases SET ptp_amount=1000,ptp_date='2026-09-01',status='PTP_SCHEDULED'")
    before = rows("cases")
    db.init_db()
    db.init_db()
    assert rows("cases") == before
    assert len(rows("case_exposures")) == len(rows("ptps")) == 1
    assert rows("ptps")[0]["status"] == "UNVERIFIED"
    assert db.get_debtor_behavioral_metrics("D1", "C1")["ptp_kept_rate"] is None


def test_api_wrapup_requires_version_and_preserves_closed_case(service):
    with TestClient(app) as client:
        body = {"guardrail_token": "demo", "outcome": "BUSY_NO_ANSWER", "command_id": "W1", "expected_version": 0}
        assert client.post("/api/cases/C1/call-wrapup", json={"guardrail_token": ""}).status_code == 422
        first = client.post("/api/cases/C1/call-wrapup", json=body)
        assert first.status_code == 200, first.text
        assert client.post("/api/cases/C1/call-wrapup", json=body).json()["replayed"]
        balance(service, 0)
        assert client.post("/api/cases/C1/call-wrapup", json={**body, "command_id": "late"}).status_code == 409
        assert client.post("/api/cases/C1/call-intent", json={"target_party_id": "D1"}).status_code == 409
        assert client.get("/api/cases/C1/financial-state").json()["case"]["lifecycle"] == "CLOSED"


def test_api_balance_partial_then_cure_and_restart(service):
    with TestClient(app) as client:
        import main
        main.core_banking_adapter.client.simulate_incoming_payment("L1", "D1", 400)
        body = {"command_id": "probe1", "expected_version": 0}
        response = client.post("/api/cases/C1/balance-check", json=body)
        assert response.status_code == 200, response.text
        assert response.json()["lifecycle"] == "OPEN"
        assert not response.json()["can_proceed"]
        assert db.get_case_by_id("C1")["overdue_amount"] == 600
        assert client.post("/api/cases/C1/balance-check", json=body).json()["replayed"]
        main.core_banking_adapter.client.simulate_incoming_payment("L1", "D1", 600)
        response = client.post("/api/cases/C1/balance-check", json={"command_id": "probe2", "expected_version": 1})
        assert response.json()["resolution"] == "CURED"
    with TestClient(app) as client:
        response = client.post("/api/cases/C1/balance-check", json={"command_id": "probe3", "expected_version": 2})
        assert response.status_code == 200, response.text
        assert response.json()["resolution"] == "CURED"
        assert db.get_case_by_id("C1")["total_balance"] == 9000


def test_reconcile_rejects_balance_older_than_payment(service):
    balance(service)
    service.clock = lambda: NOW + timedelta(minutes=1)
    payment(service, at=NOW + timedelta(minutes=1))
    with pytest.raises(CaseConflict):
        command(service, "reconcile", {"reason": "old snapshot is insufficient"})
    with pytest.raises(CaseConflict):
        balance(service, 0, 2)


def test_partial_multi_loan_snapshot_is_transactional(service):
    command(service, "link_exposure", {"loan_id": "L2", "debtor_cif": "D1"})
    with pytest.raises(ValueError):
        command(service, "balance", {"snapshots": [snapshot(0), {**snapshot(0, loan="L2"), "debtor_cif": "D2"}]})
    assert all(not e["balance_verified"] for e in rows("case_exposures"))
    assert db.get_case_by_id("C1")["case_version"] == 1


def test_schema_failure_rolls_back_ddl_and_preserves_data(service, monkeypatch):
    import case_schema
    before = rows("cases")
    def fail(conn):
        conn.execute("ALTER TABLE cases ADD COLUMN rollback_probe TEXT")
        conn.execute("UPDATE cases SET full_name='must roll back'")
        raise ValueError("migration failed")
    monkeypatch.setattr(case_schema, "migrate", fail)
    with pytest.raises(ValueError, match="migration failed"):
        db.init_db()
    assert rows("cases") == before


@pytest.mark.parametrize("amount,due", [(0, "2026-09-07"), (1.5, "2026-09-07"), (1000, "2026-09-01"), (1000, "2026-09-07T12:00:00")])
def test_invalid_ptp_never_creates_interaction(service, amount, due):
    with pytest.raises(ValueError):
        command(service, "wrapup", {"outcome": "PTP_AGREED", "ptp_amount": amount, "ptp_date": due})
    assert rows("ptps") == rows("case_interactions") == []


def test_date_only_ptp_uses_vietnam_end_of_day(service):
    command(service, "wrapup", {"outcome": "PTP_AGREED", "ptp_amount": 1000, "ptp_date": "2026-09-07"})
    assert rows("ptps")[0]["due_at"] == "2026-09-07T16:59:59+00:00"
