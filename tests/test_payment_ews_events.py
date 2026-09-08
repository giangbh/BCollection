"""ADP-03/04 real loopback REST integration with isolated synthetic state."""
from datetime import datetime, timedelta, timezone
import json
import sqlite3

import pytest
from fastapi.testclient import TestClient

import database as db
from main import app
from case_service import CaseService
from legacy_mock import create_app, seed
from customer_fixtures import seed_customer360
from event_mock import payment, signal, seal
from portfolio_import import import_demo_portfolio
from payment_ingestion import sync_payments
from ews_ingestion import sync_ews
from integration_events import publish_outcomes
from rest_transport import AdapterError
from synthetic.generator import generate_synthetic_delinquent_cases
from test_demo_http_adapters import serve, configure


@pytest.fixture
def running(monkeypatch, tmp_path):
    path = tmp_path / 'events.sqlite3'
    now = datetime.now(timezone.utc)
    seed(path, generate_synthetic_delinquent_cases(3, 42, now.replace(tzinfo=None)), {'seed': 42}, now.isoformat())
    seed_customer360(path)
    with serve(create_app(path)) as url:
        configure(monkeypatch, url)
        monkeypatch.setenv('CRM_API_URL', url + '/crm/v1')
        monkeypatch.setenv('EWS_API_URL', url + '/ews/v1')
        with TestClient(app) as client:
            yield path, client, url


def bootstrap(client):
    import_demo_portfolio()
    return client.get('/api/cases').json()[0]


def case_row(case):
    return db.get_case_by_id(case['case_id'])


def promise(case, *, historical=False, amount=1000):
    now = datetime.now(timezone.utc)
    clock = now - timedelta(days=2) if historical else now
    due = now - timedelta(days=1) if historical else now + timedelta(days=1)
    CaseService(lambda: clock).execute(case['case_id'], 'promise', case_row(case)['case_version'], 'record_ptp',
                                      {'loan_id': case['loan_id'], 'ptp_amount': amount, 'ptp_date': due.isoformat()})
    return ptp(case)


def ptp(case):
    with db.get_connection() as conn:
        return dict(conn.execute('SELECT * FROM ptps WHERE case_id=?', (case['case_id'],)).fetchone())


def count(table):
    with db.get_connection() as conn:
        return conn.execute(f'SELECT COUNT(*) FROM {table}').fetchone()[0]


def test_partial_full_and_reversal_feedback(running):
    path, client, url = running
    case = bootstrap(client)
    promise(case)
    payment(path, case['loan_id'], 'P1', 400)
    sync_payments(case['case_id'])
    assert ptp(case)['paid_vnd'] == 400 and ptp(case)['status'] == 'PARTIALLY_KEPT'
    payment(path, case['loan_id'], 'P2', 600)
    sync_payments(case['case_id'])
    assert ptp(case)['status'] == 'KEPT'
    before = count('payment_ledger'), count('outcome_outbox'), case_row(case)['case_version']
    sync_payments(case['case_id'])
    assert before == (count('payment_ledger'), count('outcome_outbox'), case_row(case)['case_version'])
    payment(path, case['loan_id'], 'R1', reverses='P2')
    sync_payments(case['case_id'])
    assert ptp(case)['paid_vnd'] == 400 and ptp(case)['status'] == 'PARTIALLY_KEPT'
    assert publish_outcomes(case['case_id'])['failed'] == 0
    from rest_transport import RestTransport
    result = RestTransport(url + '/ews/v1').get('collection-outcomes/' + case['case_id'])
    assert result['ptps'][0]['paid_vnd'] == 400
    assert result['causal_attribution'] is False


def test_watermark_required_for_broken_and_late_arrival_before_seal(running):
    path, client, _ = running
    case = bootstrap(client)
    promise(case, historical=True)
    sync_payments(case['case_id'])
    assert ptp(case)['status'] == 'SCHEDULED' and ptp(case)['observed_through'] is None
    # Arrives now, but was paid before the due date. A recent-15-minute query would miss it.
    payment(path, case['loan_id'], 'LATE', 400, occurred_at=(datetime.now(timezone.utc)-timedelta(hours=36)).isoformat())
    sync_payments(case['case_id'])
    assert ptp(case)['on_time_vnd'] == 400
    seal(path, case['loan_id'])
    sync_payments(case['case_id'])
    assert ptp(case)['status'] == 'BROKEN'
    with pytest.raises(ValueError, match='sealed'):
        payment(path, case['loan_id'], 'ILLEGAL-LATE', 600, occurred_at=(datetime.now(timezone.utc)-timedelta(hours=30)).isoformat())


def test_reversal_delivered_before_original_and_restart(running):
    path, client, _ = running
    case = bootstrap(client)
    promise(case)
    payment(path, case['loan_id'], 'P1', 400)
    payment(path, case['loan_id'], 'R1', reverses='P1')
    with sqlite3.connect(path) as conn:
        rows = conn.execute("SELECT * FROM mock_events WHERE kind='payment' ORDER BY sequence DESC").fetchall()
        conn.execute("DELETE FROM mock_events WHERE kind='payment'")
        for index, row in enumerate(rows, 1):
            payload = json.loads(row[4]); payload['sequence'] = index
            conn.execute('INSERT INTO mock_events VALUES (?,?,?,?,?,?)', (*row[:3], index, json.dumps(payload), row[5]))
    result = sync_payments(case['case_id'])
    assert result['pending_review'] == 0 and count('payment_ledger') == 2
    assert ptp(case)['paid_vnd'] == 0
    with TestClient(app):
        sync_payments(case['case_id'])
    assert count('payment_ledger') == 2


def test_inbox_survives_crash_and_ledger_outbox_are_atomic(running, monkeypatch):
    path, client, _ = running
    case = bootstrap(client)
    payment(path, case['loan_id'], 'P1', 100)
    import integration_events
    original = integration_events.enqueue_outcome
    def crash(*a, **kw):
        raise RuntimeError('Simulated process failure before commit')
    monkeypatch.setattr(integration_events, 'enqueue_outcome', crash)
    with pytest.raises(RuntimeError):
        sync_payments(case['case_id'])
    assert count('integration_inbox') == 1 and count('payment_ledger') == 0 and count('outcome_outbox') == 0
    monkeypatch.setattr(integration_events, 'enqueue_outcome', original)
    sync_payments(case['case_id'])
    assert count('payment_ledger') == 1 and count('outcome_outbox') >= 1


def test_pagination_cursor_receives_all_events(running):
    path, client, _ = running
    case = bootstrap(client)
    for i in range(101):
        payment(path, case['loan_id'], 'P' + str(i), 1)
    seal(path, case['loan_id'])
    assert sync_payments(case['case_id'])['streams'][case['loan_id']]['cursor'] == 101
    assert count('payment_ledger') == 101


def test_unknown_ptp_stays_unallocated_and_explicit_allocation(running):
    path, client, _ = running
    case = bootstrap(client)
    p = promise(case, historical=True)
    payment(path, case['loan_id'], 'LATE', 400)  # Outside any PTP due window.
    sync_payments(case['case_id'])
    assert ptp(case)['paid_vnd'] == 0
    CaseService().execute(case['case_id'], 'allocation', case_row(case)['case_version'], 'allocate_payment',
                          {'event_id': 'LATE', 'ptp_id': p['ptp_id'], 'reason': 'Reviewed late payment allocation'})
    assert ptp(case)['paid_vnd'] == 400 and ptp(case)['on_time_vnd'] == 0


def test_ews_creates_scoped_case_and_replays_without_duplicate(running):
    path, client, _ = running
    with sqlite3.connect(path) as conn:
        loan = json.loads(conn.execute("SELECT payload FROM mock_loans WHERE json_extract(payload,'$.dpd')>0 LIMIT 1").fetchone()[0])
    signal(path, loan['debtor_cif'], [loan['loan_id']], 'S1', 'E1')
    result = sync_ews(loan['debtor_cif'])
    assert result['decisions']['S1'] == 'APPLIED'
    assert count('cases') == count('workspace_policy_handoffs') == 1
    sync_ews(loan['debtor_cif'])
    assert count('cases') == count('workspace_policy_handoffs') == 1
    case = client.get('/api/cases').json()[0]
    assert case['phone_e164'] == '' and case['case_version'] == 2
    assert client.post(f"/api/cases/{case['case_id']}/call-intent", json={}).status_code == 503
    assert publish_outcomes()['delivered'] == 2


def test_ews_unverified_then_verified_revision_and_closed_case(running):
    path, client, _ = running
    case = bootstrap(client)
    signal(path, case['debtor_cif'], [case['loan_id']], 'S1', 'E1', verification='UNVERIFIED')
    assert sync_ews(case['debtor_cif'])['decisions']['S1'] == 'DEFER_VERIFICATION'
    assert count('workspace_policy_handoffs') == 0
    signal(path, case['debtor_cif'], [case['loan_id']], 'S1', 'E2', version=2)
    assert sync_ews(case['debtor_cif'])['decisions']['S1'] == 'APPLIED'
    with db.get_connection() as conn:
        conn.execute("UPDATE cases SET lifecycle='CLOSED',resolution='CURED' WHERE case_id=?", (case['case_id'],))
    signal(path, case['debtor_cif'], [case['loan_id']], 'S2', 'E3')
    assert sync_ews(case['debtor_cif'])['decisions']['S2'] == 'DEFER_CASE_STATE'
    assert case_row(case)['lifecycle'] == 'CLOSED'


def test_ews_low_or_dismissed_never_creates_case(running):
    path, _, _ = running
    with sqlite3.connect(path) as conn:
        loan = json.loads(conn.execute('SELECT payload FROM mock_loans LIMIT 1').fetchone()[0])
    signal(path, loan['debtor_cif'], [loan['loan_id']], 'LOW', 'E1', severity='LOW')
    signal(path, loan['debtor_cif'], [loan['loan_id']], 'DISMISSED', 'E2', verification='DISMISSED')
    result = sync_ews(loan['debtor_cif'])
    assert set(result['decisions'].values()) == {'MONITOR', 'NO_ACTION'}
    assert count('cases') == 0


def test_outcome_lost_ack_and_expired_lease_are_idempotent(running, monkeypatch):
    path, client, _ = running
    case = bootstrap(client)
    promise(case)
    from event_sources import OutcomePublisherAdapter
    original = OutcomePublisherAdapter.send
    def lost_ack(self, event):
        original(self, event)
        raise AdapterError('SOURCE_UNAVAILABLE')
    monkeypatch.setattr(OutcomePublisherAdapter, 'send', lost_ack)
    assert publish_outcomes(case['case_id'])['failed'] == 1
    monkeypatch.setattr(OutcomePublisherAdapter, 'send', original)
    assert publish_outcomes(case['case_id'], clock=lambda: datetime.now(timezone.utc)+timedelta(minutes=2))['delivered'] == 1
    with sqlite3.connect(path) as conn:
        assert conn.execute('SELECT COUNT(*) FROM mock_outcomes').fetchone()[0] == 1
    with db.get_connection() as conn:
        conn.execute("UPDATE outcome_outbox SET state='INFLIGHT',lease_until='2000-01-01T00:00:00+00:00'")
    assert publish_outcomes(case['case_id'])['delivered'] == 1
    with sqlite3.connect(path) as conn:
        assert conn.execute('SELECT COUNT(*) FROM mock_outcomes').fetchone()[0] == 1


def test_event_actions_are_demo_only():
    with TestClient(app) as client:
        for action in ('sync-payments','sync-ews','publish-outcomes'):
            assert client.post('/api/cases/unknown/' + action).status_code == 503


def test_wrong_cif_stream_cannot_observe_ptp_or_change_other_case(running):
    path, client, _ = running
    case = bootstrap(client)
    promise(case, historical=True)
    seal(path, case['loan_id'])
    with sqlite3.connect(path) as conn:
        loan = json.loads(conn.execute('SELECT payload FROM mock_loans WHERE loan_id=?', (case['loan_id'],)).fetchone()[0])
        loan['debtor_cif'] = 'WRONG'
        conn.execute('UPDATE mock_loans SET payload=? WHERE loan_id=?', (json.dumps(loan), case['loan_id']))
    result = sync_payments(case['case_id'])
    assert result['streams'][case['loan_id']]['status'] == 'STREAM_IDENTITY_MISMATCH'
    assert ptp(case)['status'] == 'SCHEDULED' and ptp(case)['observed_through'] is None
    assert case_row(case)['contact_hold_reason'] == 'PAYMENT_SOURCE_REVIEW'


def test_ambiguous_allocation_prevents_broken_until_review(running):
    path, client, _ = running
    case = bootstrap(client)
    p = promise(case, historical=True)
    with db.get_connection() as conn:
        conn.execute("""INSERT INTO ptps SELECT 'SECOND',case_id,loan_id,amount_vnd,created_at,due_at,status,
            paid_vnd,on_time_vnd,observed_through,data_origin FROM ptps WHERE ptp_id=?""", (p['ptp_id'],))
    payment(path, case['loan_id'], 'P1', 400, occurred_at=(datetime.now(timezone.utc)-timedelta(hours=36)).isoformat())
    seal(path, case['loan_id'])
    sync_payments(case['case_id'])
    with db.get_connection() as conn:
        assert {r[0] for r in conn.execute('SELECT status FROM ptps')} == {'SCHEDULED'}
        assert conn.execute('SELECT ptp_id FROM payment_ledger').fetchone()[0] is None


def test_pending_reversal_holds_case_and_completeness(running):
    path, client, _ = running
    case = bootstrap(client)
    promise(case, historical=True)
    # Malformed but structurally valid source dependency is quarantined, not silently discarded.
    from event_mock import append
    with sqlite3.connect(path) as conn:
        append(conn, 'payment', case['loan_id'], {'event_id': 'R', 'loan_id': case['loan_id'], 'debtor_cif': case['debtor_cif'],
            'kind': 'REVERSED', 'amount_vnd': 400, 'occurred_at': datetime.now(timezone.utc).isoformat(), 'reverses_event_id': 'MISSING'})
    seal(path, case['loan_id'])
    result = sync_payments(case['case_id'])
    assert result['pending_review'] == 1 and ptp(case)['observed_through'] is None
    assert case_row(case)['contact_hold_reason'] == 'PAYMENT_SOURCE_REVIEW'
    with pytest.raises(ValueError, match='pending events'):
        CaseService().execute(case['case_id'], 'cannot-clear', case_row(case)['case_version'], 'reconcile', {'reason': 'Must not bypass pending events'})


def test_ews_conflicting_revision_quarantines_without_handoff(running):
    path, client, _ = running
    case = bootstrap(client)
    signal(path, case['debtor_cif'], [case['loan_id']], 'S1', 'E1', verification='UNVERIFIED')
    sync_ews(case['debtor_cif'])
    signal(path, case['debtor_cif'], [case['loan_id']], 'S1', 'E2', version=2)
    with sqlite3.connect(path) as conn:
        event = json.loads(conn.execute("SELECT payload FROM mock_events WHERE event_id='E2'").fetchone()[0])
        event['signal_version'] = 1
        conn.execute("UPDATE mock_events SET payload=? WHERE event_id='E2'", (json.dumps(event),))
    assert sync_ews(case['debtor_cif'])['status'] == 'QUARANTINED'
    assert count('workspace_policy_handoffs') == 0


def test_outcome_receiver_rejects_conflict_and_old_revision_does_not_regress(running):
    path, client, url = running
    case = bootstrap(client)
    promise(case)
    payment(path, case['loan_id'], 'P', 100)
    sync_payments(case['case_id'])
    from rest_transport import RestTransport
    receiver = RestTransport(url + '/ews/v1')
    with db.get_connection() as conn:
        events = [json.loads(r[0]) for r in conn.execute('SELECT payload FROM outcome_outbox WHERE case_id=? ORDER BY case_version DESC', (case['case_id'],))]
    for e in events:
        receiver.post('collection-outcomes', e, e['event_id'])
    assert receiver.get('collection-outcomes/' + case['case_id'])['case_version'] == events[0]['case_version']
    with pytest.raises(AdapterError) as error:
        receiver.post('collection-outcomes', {**events[0], 'trigger': 'tampered'}, events[0]['event_id'])
    assert error.value.status == 409


def test_cli_and_api_demo_workflow(running):
    import subprocess
    import sys
    from pathlib import Path
    path, client, _ = running
    case = bootstrap(client)
    root = Path(__file__).resolve().parents[1]
    def cli(script, args):
        result = subprocess.run([sys.executable, str(root / 'scripts' / script), *args], capture_output=True, text=True, timeout=20)
        assert result.returncode == 0, result.stderr
        return json.loads(result.stdout)
    collection = ['--mode', 'demo-http', '--database', db.DB_FILE_PATH]
    source = ['--database', str(path)]
    cli('legacy_mock.py', [*source, 'emit-ews', '--cif', case['debtor_cif'], '--loan', case['loan_id'], '--signal-id', 'CLI-S', '--event-id', 'CLI-E'])
    assert cli('bcollection.py', [*collection, 'sync-ews', '--cif', case['debtor_cif']])['decisions']['CLI-S'] == 'APPLIED'
    cli('bcollection.py', [*collection, 'create-demo-ptp', '--case', case['case_id'], '--loan', case['loan_id'], '--command-id', 'CLI-PTP', '--amount', '1000', '--due', (datetime.now(timezone.utc)+timedelta(days=1)).isoformat()])
    cli('legacy_mock.py', [*source, 'post-payment', '--loan', case['loan_id'], '--event-id', 'CLI-P', '--amount', '1000'])
    assert client.post(f"/api/cases/{case['case_id']}/sync-payments").status_code == 200
    assert ptp(case)['status'] == 'KEPT'
    cli('legacy_mock.py', [*source, 'reverse-payment', '--loan', case['loan_id'], '--event-id', 'CLI-R', '--reverses', 'CLI-P'])
    cli('legacy_mock.py', [*source, 'seal-payments', '--loan', case['loan_id']])
    cli('bcollection.py', [*collection, 'sync-payments', '--case', case['case_id']])
    result = client.post(f"/api/cases/{case['case_id']}/publish-outcomes").json()
    assert result['delivered'] > 0 and result['failed'] == 0
    state = client.get(f"/api/cases/{case['case_id']}/workspace").json()['integration_state']
    assert state['delivery']['delivered'] > 0 and state['ews_decisions'][0]['decision'] == 'APPLIED'
