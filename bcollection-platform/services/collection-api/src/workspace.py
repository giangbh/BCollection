"""Consistent read models and metadata commands for the collector workspace.

No Core portfolio completeness, EWS integration or collector identity is invented.
All writes run inside CaseService's versioned transaction.
"""
import json
from datetime import datetime, timezone, timedelta
from uuid import uuid4

from bc_domain.case_rules import instant, obligation_status
from database import get_connection


def migrate_workspace(conn):
    conn.execute("""CREATE TABLE IF NOT EXISTS contact_schedules (
        schedule_id TEXT PRIMARY KEY, case_id TEXT NOT NULL REFERENCES cases(case_id),
        scheduled_at TEXT NOT NULL, channel TEXT NOT NULL CHECK(channel='VOICE'),
        reason TEXT NOT NULL, status TEXT NOT NULL CHECK(status IN ('PLANNED','SUPERSEDED','CANCELLED')),
        created_at TEXT NOT NULL, data_origin TEXT NOT NULL)""")
    conn.execute("CREATE UNIQUE INDEX IF NOT EXISTS one_planned_schedule ON contact_schedules(case_id) WHERE status='PLANNED'")
    conn.execute("""CREATE TABLE IF NOT EXISTS decision_feedback (
        feedback_id TEXT PRIMARY KEY, case_id TEXT NOT NULL REFERENCES cases(case_id),
        recommendation_id TEXT NOT NULL, recommendation_json TEXT NOT NULL,
        decision TEXT NOT NULL CHECK(decision IN ('ACCEPT','ADJUST','DECLINE')),
        reason TEXT NOT NULL, case_version INTEGER NOT NULL, created_at TEXT NOT NULL,
        data_origin TEXT NOT NULL)""")


def exposures(conn, cif=None, case_id=None):
    if case_id:
        rows = conn.execute("SELECT * FROM case_exposures WHERE case_id=? ORDER BY loan_id", (case_id,)).fetchall()
    else:
        rows = conn.execute("SELECT e.* FROM case_exposures e JOIN cases c ON c.case_id=e.case_id WHERE c.debtor_cif=? ORDER BY e.loan_id,e.case_id", (cif,)).fetchall()
    groups = {}
    for row in rows:
        groups.setdefault(row['loan_id'], []).append(dict(row))
    result = []
    for loan, copies in groups.items():
        latest = max(e['source_version'] for e in copies)
        candidates = [e for e in copies if e['source_version'] == latest]
        keys = ('debtor_cif', 'overdue_vnd', 'principal_vnd', 'interest_vnd', 'dpd', 'source_as_of', 'balance_verified')
        conflict = len({tuple(e[k] for k in keys) for e in candidates}) > 1
        e = dict(candidates[0])
        e['case_ids'] = sorted({c['case_id'] for c in copies})
        e['conflict'] = conflict
        e['obligation_status'] = 'CONFLICT' if conflict else obligation_status(e)
        # A newly linked exposure has placeholder zeros, not evidence of zero debt.
        missing = not e['balance_verified'] and not any(e[k] for k in ('overdue_vnd', 'principal_vnd', 'interest_vnd'))
        if conflict or missing:
            for key in ('overdue_vnd', 'principal_vnd', 'interest_vnd', 'dpd'):
                e[key] = None
        result.append(e)
    return result


def scope_summary(items):
    known = bool(items) and all(e['overdue_vnd'] is not None for e in items)
    dates = [e['source_as_of'] for e in items if e['source_as_of']]
    return {
        'exposures': items,
        'overdue_vnd': sum(e['overdue_vnd'] for e in items) if known else None,
        'total_vnd': sum(e['principal_vnd'] + e['interest_vnd'] for e in items) if known else None,
        'max_dpd': max(e['dpd'] for e in items) if known else None,
        'verified_count': sum(bool(e['balance_verified']) and not e['conflict'] for e in items),
        'conflict_count': sum(e['conflict'] for e in items),
        'oldest_as_of': min(dates) if dates else None,
        'newest_as_of': max(dates) if dates else None,
        'coverage': 'RECORDED_IN_BCOLLECTION_ONLY',
        'complete_core_portfolio': False,
    }


def next_action(conn, case, now):
    schedule = conn.execute("SELECT * FROM contact_schedules WHERE case_id=? AND status='PLANNED'", (case['case_id'],)).fetchone()
    es = conn.execute("SELECT * FROM case_exposures WHERE case_id=?", (case['case_id'],)).fetchall()
    if case['lifecycle'] == 'CLOSED':
        kind = 'VIEW_RESOLUTION'
    elif case['contact_hold_reason'] or case['lifecycle'] != 'OPEN':
        kind = 'RECONCILE'
    elif not es or any(not e['balance_verified'] or not e['source_as_of'] or not -30 <= (now - instant(e['source_as_of'])).total_seconds() <= 900 for e in es):
        kind = 'BALANCE_CHECK'
    elif schedule and instant(schedule['scheduled_at']) > now:
        kind = 'WAIT_SCHEDULE'
    else:
        kind = 'CHECK_CONTACT'
    return {'recommendation_id': 'WORKSPACE_RULES_V1', 'kind': kind,
            'basis': 'CASE_STATE_RULES_NOT_AI', 'case_version': case['case_version'],
            'schedule_at': schedule['scheduled_at'] if schedule else None,
            'contact_hold_reason': case['contact_hold_reason']}


def apply_command(conn, case, kind, payload, now):
    from case_service import CaseConflict
    reason = payload.get('reason')
    if not isinstance(reason, str) or not reason.strip() or len(reason) > 2000:
        raise ValueError('Reason is required (1–2000 characters)')
    record_id = str(uuid4())
    if kind == 'schedule_contact':
        if case['lifecycle'] != 'OPEN' or case['contact_hold_reason']:
            raise CaseConflict('Closed or held cases cannot schedule contact')
        at = instant(payload['scheduled_at'])
        if at <= now or at > now + timedelta(days=365):
            raise ValueError('Schedule must be in the future and within one year')
        if payload.get('channel') != 'VOICE':
            raise ValueError('Only a VOICE plan is supported; no channel is executed')
        conn.execute("UPDATE contact_schedules SET status='SUPERSEDED' WHERE case_id=? AND status='PLANNED'", (case['case_id'],))
        conn.execute("INSERT INTO contact_schedules VALUES(?,?,?,?,?,'PLANNED',?,?)", (record_id, case['case_id'], at.isoformat(), 'VOICE', reason.strip(), now.isoformat(), case['data_origin']))
    elif kind == 'cancel_schedule':
        schedule_id = payload.get('schedule_id')
        changed = conn.execute("UPDATE contact_schedules SET status='CANCELLED' WHERE case_id=? AND schedule_id=? AND status='PLANNED'", (case['case_id'], schedule_id)).rowcount
        if not changed:
            raise CaseConflict('Active schedule no longer exists')
        # Preserve cancellation reason separately from the original plan.
        record_id = schedule_id
    else:
        recommendation = next_action(conn, case, now)
        if payload.get('recommendation_id') != recommendation['recommendation_id'] or payload.get('recommendation_kind') != recommendation['kind']:
            raise CaseConflict('Recommendation changed; reload evidence before deciding')
        decision = payload.get('decision')
        if decision not in {'ACCEPT', 'ADJUST', 'DECLINE'}:
            raise ValueError('Decision must be ACCEPT, ADJUST or DECLINE')
        conn.execute("INSERT INTO decision_feedback VALUES(?,?,?,?,?,?,?,?,?)", (record_id, case['case_id'], recommendation['recommendation_id'], json.dumps(recommendation), decision, reason.strip(), case['case_version'], now.isoformat(), case['data_origin']))
    return record_id


def read_workspace(case_id):
    from case_service import CaseNotFound
    conn = get_connection()
    try:
        conn.execute('BEGIN')  # Every panel is read from the same SQLite snapshot.
        row = conn.execute('SELECT * FROM cases WHERE case_id=?', (case_id,)).fetchone()
        if not row:
            raise CaseNotFound(case_id)
        case = dict(row)
        now = datetime.now(timezone.utc)
        result = {'case': case, 'read_at': now.isoformat(), 'assigned_collector': None,
                  'case_scope': scope_summary(exposures(conn, case_id=case_id)),
                  'customer_scope': scope_summary(exposures(conn, cif=case['debtor_cif'])),
                  'next_action': next_action(conn, case, now), 'ews': {'status': 'NOT_CONNECTED', 'signals': []}}
        for table in ('ptps', 'payment_ledger', 'case_transition_log', 'contact_schedules', 'decision_feedback', 'case_interactions'):
            result[table] = [dict(r) for r in conn.execute(f'SELECT * FROM {table} WHERE case_id=?', (case_id,))]
        return result
    finally:
        conn.close()


def read_customer(cif):
    from case_service import CaseNotFound
    conn = get_connection()
    try:
        conn.execute('BEGIN')
        if not conn.execute('SELECT 1 FROM cases WHERE debtor_cif=?', (cif,)).fetchone():
            raise CaseNotFound(cif)
        return {'debtor_cif': cif, 'read_at': datetime.now(timezone.utc).isoformat(),
                **scope_summary(exposures(conn, cif=cif))}
    finally:
        conn.close()
