from datetime import datetime, timedelta, timezone
import json

from fastapi.testclient import TestClient
import pytest

import database as db
from case_schema import backfill
from case_service import CaseConflict
from main import app
from workspace import read_workspace
from test_case_correctness import service, command, rows, balance, payment, NOW


def schedule_payload():
    return {'scheduled_at': (NOW + timedelta(days=2)).isoformat(), 'channel': 'VOICE', 'reason': 'Kế hoạch cán bộ, chưa xác nhận khách hàng'}


def test_schedule_persists_idempotently_without_financial_changes(service):
    before = db.get_case_by_id('C1')
    first = command(service, 'schedule_contact', schedule_payload(), 'S1', 0)
    again = command(service, 'schedule_contact', schedule_payload(), 'S1', 0)
    assert first['record_id'] == again['record_id'] and again['replayed']
    assert len(rows('contact_schedules')) == 1
    db.init_db()
    w = read_workspace('C1')
    assert w['contact_schedules'][0]['reason'] == schedule_payload()['reason']
    for field in ('lifecycle', 'status', 'resolution', 'overdue_amount', 'total_balance', 'ptp_amount', 'ptp_date'):
        assert w['case'][field] == before[field]
    assert w['case']['case_version'] == 1
    assert len(w['case_transition_log']) == 1


def test_reschedule_preserves_history_and_cancel_reason(service):
    command(service, 'schedule_contact', schedule_payload())
    second = command(service, 'schedule_contact', {**schedule_payload(), 'scheduled_at': (NOW + timedelta(days=3)).isoformat()})
    assert [s['status'] for s in rows('contact_schedules')] == ['SUPERSEDED', 'PLANNED']
    command(service, 'cancel_schedule', {'schedule_id': second['record_id'], 'reason': 'Cần đối soát trước'})
    assert [s['status'] for s in rows('contact_schedules')] == ['SUPERSEDED', 'CANCELLED']
    assert 'Cần đối soát trước' in rows('case_transition_log')[-1]['reason']


@pytest.mark.parametrize('change', [{'reason': ''}, {'reason': ' '}, {'reason': 'x' * 2001}, {'channel': 'SMS'}, {'scheduled_at': NOW.isoformat()}, {'scheduled_at': '2026-09-09T18:00:00'}, {'scheduled_at': (NOW + timedelta(days=366)).isoformat()}])
def test_bad_schedule_rolls_back(service, change):
    with pytest.raises(ValueError):
        command(service, 'schedule_contact', {**schedule_payload(), **change})
    assert rows('contact_schedules') == []
    assert db.get_case_by_id('C1')['case_version'] == 0


@pytest.mark.parametrize('closed', [True, False])
def test_closed_or_held_case_cannot_plan(service, closed):
    if closed:
        balance(service, 0)
    else:
        payment(service)
    with pytest.raises(CaseConflict):
        command(service, 'schedule_contact', schedule_payload())
    assert rows('contact_schedules') == []


def test_stale_schedule_cannot_supersede_existing(service):
    command(service, 'schedule_contact', schedule_payload())
    with pytest.raises(CaseConflict):
        command(service, 'schedule_contact', {**schedule_payload(), 'reason': 'concurrent edit'}, version=0)
    assert len(rows('contact_schedules')) == 1


def test_feedback_snapshot_and_provenance_not_outcome(service):
    payload = {'recommendation_id': 'WORKSPACE_RULES_V1', 'recommendation_kind': 'BALANCE_CHECK', 'decision': 'ADJUST', 'reason': 'Cần kiểm tra thông tin trước'}
    command(service, 'decision_feedback', payload, 'F1', 0)
    command(service, 'decision_feedback', payload, 'F1', 0)
    feedback = rows('decision_feedback')
    assert len(feedback) == 1 and feedback[0]['data_origin'] == 'SYNTHETIC'
    assert json.loads(feedback[0]['recommendation_json'])['case_version'] == 0
    assert feedback[0]['decision'] == 'ADJUST'
    assert rows('payment_ledger') == rows('ptps') == []
    assert db.get_case_by_id('C1')['resolution'] is None


def test_feedback_rejects_invented_or_changed_recommendation(service):
    with pytest.raises(CaseConflict):
        command(service, 'decision_feedback', {'recommendation_id': 'fake-model', 'recommendation_kind': 'CHECK_CONTACT', 'decision': 'ACCEPT', 'reason': 'approve'})
    assert rows('decision_feedback') == []


def clone_case(case_id, loan_id):
    with db.get_connection() as conn:
        c = dict(conn.execute("SELECT * FROM cases WHERE case_id='C1'").fetchone())
        c.update(case_id=case_id, loan_id=loan_id)
        conn.execute(f"INSERT INTO cases({','.join(c)}) VALUES({','.join('?' for _ in c)})", tuple(c.values()))
        backfill(conn)


def test_customer_scope_deduplicates_and_discloses_coverage(service):
    clone_case('C2', 'L1')
    clone_case('C3', 'L2')
    w = read_workspace('C1')
    assert len(w['case_scope']['exposures']) == 1
    assert len(w['customer_scope']['exposures']) == 2
    assert w['customer_scope']['overdue_vnd'] == 2000
    assert w['customer_scope']['exposures'][0]['case_ids'] == ['C1', 'C2']
    assert not w['customer_scope']['complete_core_portfolio']
    assert w['ews'] == {'status': 'NOT_CONNECTED', 'signals': []}
    assert w['assigned_collector'] is None


def test_conflicting_same_version_is_not_summed(service):
    clone_case('C2', 'L1')
    with db.get_connection() as conn:
        conn.execute("UPDATE case_exposures SET overdue_vnd=2000 WHERE case_id='C2'")
    scope = read_workspace('C1')['customer_scope']
    assert scope['conflict_count'] == 1
    assert scope['overdue_vnd'] is None and scope['total_vnd'] is None and scope['max_dpd'] is None
    assert scope['exposures'][0]['obligation_status'] == 'CONFLICT'


def test_empty_new_link_is_missing_not_zero(service):
    command(service, 'link_exposure', {'loan_id': 'L2', 'debtor_cif': 'D1'})
    scope = read_workspace('C1')['case_scope']
    assert scope['total_vnd'] is None and scope['overdue_vnd'] is None


def test_workspace_api_persists_and_checks_future_schedule_before_call(service):
    with TestClient(app) as client:
        assert client.get('/api/cases/absent/workspace').status_code == 404
        payload = {**schedule_payload(), 'scheduled_at': (datetime.now(timezone.utc) + timedelta(days=1)).isoformat()}
        res = client.post('/api/cases/C1/commands/schedule_contact', json={'command_id': 'api-schedule', 'expected_version': 0, 'payload': payload})
        assert res.status_code == 200, res.text
        res = client.post('/api/cases/C1/call-intent', json={'target_party_id': 'D1', 'channel': 'VOICE', 'expected_version': 1})
        assert res.status_code == 200 and res.json()['blocking_reason'] == 'NOT_BEFORE_SCHEDULE'
    with TestClient(app) as client:
        data = client.get('/api/cases/C1/workspace').json()
        assert len(data['contact_schedules']) == 1
        assert data['case']['case_version'] == 1


def test_integration_blocks_workspace_mutations(monkeypatch):
    from test_runtime_foundation import integration_env
    integration_env(monkeypatch)
    with TestClient(app) as client:
        for kind in ('schedule_contact', 'decision_feedback', 'cancel_schedule'):
            assert client.post(f'/api/cases/C1/commands/{kind}', json={}).status_code == 503


def test_customer_endpoint_does_not_claim_complete_core_portfolio(service):
    with TestClient(app) as client:
        response = client.get('/api/customers/D1/exposures')
        assert response.status_code == 200
        assert response.json()['coverage'] == 'RECORDED_IN_BCOLLECTION_ONLY'
        assert response.json()['complete_core_portfolio'] is False
        assert client.get('/api/customers/absent/exposures').status_code == 404
