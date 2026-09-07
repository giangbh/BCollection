"""Customer-first UI contracts, isolated synthetic data only."""
from datetime import timedelta
import pytest
from fastapi.testclient import TestClient
import database as db
from main import app
from case_service import CaseConflict, CaseService
from workspace import read_workspace
from customer360 import dpd_history, search_customers
from test_case_correctness import service, command, rows, balance, payment, snapshot, NOW
from test_workspace import clone_case


def feedback(service, decision='ACCEPT'):
    return command(service, 'decision_feedback', {'recommendation_id': 'WORKSPACE_RULES_V1', 'recommendation_kind': 'BALANCE_CHECK', 'decision': decision, 'reason': 'Review source'})['record_id']


def test_missing_sources_are_not_fabricated_and_cases_share_customer(service):
    clone_case('C2', 'L2')
    w = read_workspace('C1')
    assert w['customer_profile'] is None
    assert {c['case_id'] for c in w['customer_cases']} == {'C1', 'C2'}
    assert w['capabilities']['risk_model'] == 'NOT_CONNECTED'
    assert w['policy_handoffs'] == []
    assert w['outcome_feedback']['causal_attribution'] is False
    assert len(w['dpd_history']['case']['points']) == 12
    assert all(p['max_dpd'] is None for p in w['dpd_history']['case']['points'])


def test_profile_contract_and_accent_insensitive_search(service):
    with db.get_connection() as conn:
        conn.execute("INSERT INTO customer_profiles VALUES('D1','ORGANIZATION','Công ty Minh Phát','0101234567','Xây dựng','Hà Nội','RM nguồn','CRM',?,'SYNTHETIC')", (NOW.isoformat(),))
    p = read_workspace('C1')['customer_profile']
    assert p['party_type'] == 'ORGANIZATION' and p['source'] == 'CRM'
    for query in ('minh phat', '010123', 'C1', 'D1', 'L1'):
        assert search_customers(query)['items'][0]['case_id'] == 'C1'
    assert search_customers('%')['items'] == []  # Literal, not SQL wildcard.
    assert search_customers("' OR 1=1 --")['items'] == []


def test_search_secondary_exposure_and_validation(service):
    command(service, 'link_exposure', {'loan_id': 'SECONDARY-LOAN', 'debtor_cif': 'D1'})
    with TestClient(app) as client:
        assert client.get('/api/customer-search', params={'q': 'secondary'}).json()['items'][0]['case_id'] == 'C1'
        for q in ('', ' ', 'a', '  ', 'x' * 101):
            assert client.get('/api/customer-search', params={'q': q}).status_code == 422
        assert client.get('/api/customer-search', params={'q': 'absent'}).json()['items'] == []


def test_note_is_durable_scoped_and_does_not_accept_spoofed_author(service):
    clone_case('C2', 'L2')
    before = db.get_case_by_id('C1')
    payload = {'reason': '  Liên hệ sau khi khách hàng xác nhận.  ', 'author': 'Bank CEO'}
    command(service, 'add_note', payload, 'N1', 0)
    assert command(service, 'add_note', payload, 'N1', 0)['replayed']
    db.init_db()
    w = read_workspace('C1')
    assert len(w['case_notes']) == 1
    assert w['case_notes'][0]['author'] == 'Demo collector (unauthenticated)'
    assert w['case_notes'][0]['body'] == payload['reason'].strip()
    assert w['case_notes'][0]['debtor_cif'] == 'D1'
    assert read_workspace('C2')['case_notes'] == []
    for field in ('lifecycle', 'resolution', 'status', 'overdue_amount', 'total_balance', 'ptp_amount'):
        assert w['case'][field] == before[field]
    with pytest.raises(CaseConflict):
        command(service, 'add_note', {'reason': 'Stale'}, version=0)
    assert len(rows('case_notes')) == 1


@pytest.mark.parametrize('reason', ['', '   ', 'x' * 2001, None, 123])
def test_invalid_note_rolls_back(service, reason):
    with pytest.raises(ValueError):
        command(service, 'add_note', {'reason': reason})
    assert rows('case_notes') == []
    assert db.get_case_by_id('C1')['case_version'] == 0


def history(customer=False, loans=('L1',)):
    with db.get_connection() as conn:
        return dpd_history(conn, db.get_case_by_id('C1'), set(loans), customer, NOW)


def test_history_only_records_validated_snapshots_and_idempotent_commands(service):
    balance(service)
    command(service, 'balance', {'snapshots': [snapshot()]})
    assert len(rows('exposure_observations')) == 1
    points = history()['points']
    assert len(points) == 12 and points[-1]['max_dpd'] == 10
    assert points[-1]['average_dpd'] == 10
    assert all(p['max_dpd'] is None for p in points[:-1])
    with pytest.raises(CaseConflict):
        balance(service, amount=2000)
    assert len(rows('exposure_observations')) == 1


def test_history_preserves_zero_and_requires_complete_current_scope(service):
    command(service, 'link_exposure', {'loan_id': 'L2', 'debtor_cif': 'D1'})
    balance(service, 0)
    partial = history(loans=('L1', 'L2'))['points'][-1]
    assert partial['observed_loans'] == 1 and partial['max_dpd'] is None
    balance(service, 0, loan='L2')
    complete = history(loans=('L1', 'L2'))['points'][-1]
    assert complete['max_dpd'] == 0 and complete['average_dpd'] == 0


def test_history_deduplicates_cross_case_and_rejects_conflicting_evidence(service):
    clone_case('C2', 'L1')
    balance(service)
    service.execute('C2', 'B2', 0, 'balance', {'snapshots': [snapshot()]})
    assert history(customer=True)['points'][-1]['observed_loans'] == 1
    with db.get_connection() as conn:
        conn.execute("UPDATE exposure_observations SET snapshot_hash='conflict',dpd=90 WHERE case_id='C2'")
    assert history(customer=True)['points'][-1]['max_dpd'] is None


def test_history_month_boundary_uses_vietnam_time(service):
    # First local day of the oldest visible month is still the previous UTC month.
    first = NOW.replace(year=2025, month=9, day=30, hour=18)
    service.clock = lambda: first
    command(service, 'balance', {'snapshots': [snapshot(at=first)]})
    points = history()['points']
    assert points[0]['month'] == '2025-10' and points[0]['max_dpd'] == 10
    assert points[0]['oldest_as_of'] == first.isoformat()


def test_failed_multiloan_command_does_not_leave_history(service):
    with pytest.raises(ValueError):
        command(service, 'balance', {'snapshots': [snapshot(), snapshot(loan='NOT-LINKED')]})
    assert rows('exposure_observations') == []


def test_ews_handoff_is_scoped_and_not_implicitly_created(service):
    clone_case('C2', 'L2')
    with db.get_connection() as conn:
        conn.execute("INSERT INTO workspace_ews_signals VALUES('E1','D1','Dòng tiền giảm','HIGH','VERIFIED','EWS',?,'SYNTHETIC')", (NOW.isoformat(),))
        conn.execute("INSERT INTO workspace_ews_signals VALUES('E2','OTHER','Other party','LOW','UNVERIFIED','EWS',?,'SYNTHETIC')", (NOW.isoformat(),))
        conn.execute("INSERT INTO workspace_policy_handoffs VALUES('H1','C1','E1','POLICY-v1','REVIEW','Cần rà soát',?,'SYNTHETIC')", (NOW.isoformat(),))
        conn.execute("INSERT INTO workspace_policy_handoffs VALUES('H2','C1','E2','POLICY-v1','REVIEW','Invalid identity',?,'SYNTHETIC')", (NOW.isoformat(),))
    w = read_workspace('C1')
    assert len(w['ews']['signals']) == 1
    assert [h['handoff_id'] for h in w['policy_handoffs']] == ['H1']
    assert read_workspace('C2')['policy_handoffs'] == []
    assert w['next_action']['basis'] == 'CASE_STATE_RULES_NOT_AI'


def test_explicit_outcome_trace_preserves_ptp_payments_and_reversals(service):
    fid = feedback(service)
    payload = {'outcome': 'PTP_AGREED', 'ptp_amount': 1000, 'ptp_date': (NOW + timedelta(hours=1)).isoformat(), 'decision_feedback_id': fid}
    command(service, 'wrapup', payload, 'W1')
    command(service, 'wrapup', payload, 'W1', version=0)
    ptp = rows('ptps')[0]['ptp_id']
    payment(service, amount=400, ptp=ptp)
    w = read_workspace('C1')
    trace = w['outcome_feedback']['links'][0]
    assert trace['paid_vnd'] == 400 and trace['ptp_status'] == 'PARTIALLY_KEPT'
    assert len(rows('decision_action_links')) == 1
    command(service, 'payment', {'event_id': 'R1', 'loan_id': 'L1', 'debtor_cif': 'D1', 'kind': 'REVERSED', 'amount_vnd': 400, 'occurred_at': NOW.isoformat(), 'reverses_event_id': 'P1'})
    trace = read_workspace('C1')['outcome_feedback']['links'][0]
    assert trace['paid_vnd'] == 0
    assert {p['event_id'] for p in trace['payments']} == {'P1', 'R1'}
    assert db.get_case_by_id('C1')['resolution'] is None


@pytest.mark.parametrize('decision', ['DECLINE', 'missing', 'other_case'])
def test_outcome_rejects_invalid_feedback_without_side_effects(service, decision):
    fid = feedback(service, 'DECLINE' if decision == 'DECLINE' else 'ACCEPT')
    if decision == 'missing':
        fid = 'missing'
    if decision == 'other_case':
        clone_case('C2', 'L2')
        with db.get_connection() as conn:
            conn.execute("UPDATE decision_feedback SET case_id='C2' WHERE feedback_id=?", (fid,))
    with pytest.raises(ValueError):
        command(service, 'wrapup', {'outcome': 'REFUSED', 'decision_feedback_id': fid})
    assert rows('case_interactions') == rows('decision_action_links') == []


def test_no_implicit_outcome_and_api_contract_persists_link(service):
    fid = feedback(service)
    command(service, 'wrapup', {'outcome': 'REFUSED'})
    assert read_workspace('C1')['outcome_feedback']['links'] == []
    with TestClient(app) as client:
        response = client.post('/api/cases/C1/call-wrapup', json={'command_id': 'API-WRAP', 'expected_version': 2, 'guardrail_token': 'simulation', 'outcome': 'BUSY_NO_ANSWER', 'decision_feedback_id': fid})
        assert response.status_code == 200, response.text
        assert client.get('/api/cases/C1/workspace').json()['outcome_feedback']['links'][0]['feedback_id'] == fid


def test_pre_360_wrapup_receipt_remains_replayable_after_schema_upgrade(service):
    legacy = {'guardrail_token': 'demo', 'outcome': 'REFUSED', 'ptp_amount': None,
              'ptp_date': None, 'notes': None, 'loan_id': None}
    command(service, 'wrapup', legacy, 'OLD-WRAPUP', 0)
    with TestClient(app) as client:
        response = client.post('/api/cases/C1/call-wrapup', json={**legacy,
            'command_id': 'OLD-WRAPUP', 'expected_version': 0})
        assert response.status_code == 200, response.text
        assert response.json()['replayed'] is True
    assert len(rows('case_interactions')) == 1
    assert rows('decision_action_links') == []


def test_integration_cannot_write_notes(monkeypatch):
    from test_runtime_foundation import integration_env
    integration_env(monkeypatch)
    with TestClient(app) as client:
        assert client.post('/api/cases/C1/commands/add_note', json={}).status_code == 503
