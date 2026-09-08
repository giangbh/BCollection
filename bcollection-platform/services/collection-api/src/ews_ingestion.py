"""Demo EWS policy handoff with explicit scopes and versioned decisions."""
from contextlib import closing
from datetime import datetime, timezone
import json
from uuid import uuid5, NAMESPACE_URL

from database import get_connection
from case_service import CaseService, CaseConflict
from integration_events import demo_only, receive, fingerprint
from bc_domain.case_rules import instant

POLICY = 'DEMO_HANDOFF_V1'


def stable(value):
    return str(uuid5(NAMESPACE_URL, 'bcollection:ews:' + value))


def apply_handoff(conn, case, payload, now):
    if case['lifecycle'] != 'OPEN' or case['data_origin'] != 'SYNTHETIC':
        raise CaseConflict('Open synthetic case required for demo handoff')
    version = conn.execute('SELECT * FROM ews_signal_versions WHERE signal_id=?', (payload['signal_id'],)).fetchone()
    if not version or version['signal_version'] != payload['signal_version']:
        raise CaseConflict('Signal revision changed')
    signal = json.loads(version['payload'])
    loans = {r[0] for r in conn.execute('SELECT loan_id FROM case_exposures WHERE case_id=?', (case['case_id'],))}
    if signal['debtor_cif'] != case['debtor_cif'] or not set(signal['loan_ids']) <= loans or signal['verification'] != 'VERIFIED':
        raise CaseConflict('Handoff identity/scope/verification mismatch')
    handoff_id = stable(f"{signal['signal_id']}:{signal['signal_version']}:{POLICY}:{case['case_id']}")
    conn.execute('INSERT INTO workspace_policy_handoffs VALUES (?,?,?,?,?,?,?,?)',
                 (handoff_id, case['case_id'], signal['signal_id'], POLICY, 'REVIEW_COLLECTION', payload['reason'], now.isoformat(), 'SYNTHETIC'))
    return handoff_id


def ingest_signals(cif):
    with closing(get_connection()) as conn, conn:
        conn.execute('BEGIN IMMEDIATE')
        for row in conn.execute("SELECT * FROM integration_inbox WHERE kind='ews' AND stream_id=? AND state!='APPLIED' ORDER BY sequence", (cif,)).fetchall():
            event = json.loads(row['payload'])
            prior = conn.execute('SELECT * FROM ews_signal_versions WHERE signal_id=?', (event['signal_id'],)).fetchone()
            if prior:
                old = json.loads(prior['payload'])
                if old['debtor_cif'] != cif or event['signal_version'] <= prior['signal_version'] or instant(event['occurred_at']) < instant(old['occurred_at']):
                    conn.execute("UPDATE integration_inbox SET state='PENDING_REVIEW',error='SIGNAL_VERSION_CONFLICT' WHERE kind='ews' AND event_id=?", (row['event_id'],))
                    continue
            conn.execute('''INSERT INTO workspace_ews_signals VALUES (?,?,?,?,?,?,?,?) ON CONFLICT(signal_id) DO UPDATE SET
                title=excluded.title,severity=excluded.severity,verification=excluded.verification,occurred_at=excluded.occurred_at''',
                (event['signal_id'], cif, event['title'], event['severity'], event['verification'], 'MOCK_EWS', event['occurred_at'], 'SYNTHETIC'))
            conn.execute('INSERT OR REPLACE INTO ews_signal_versions VALUES (?,?,?,?,?)',
                         (event['signal_id'], event['signal_version'], fingerprint(event), json.dumps(event, sort_keys=True), event['event_id']))
            conn.execute("UPDATE integration_inbox SET state='APPLIED',error=NULL WHERE kind='ews' AND event_id=?", (row['event_id'],))


def evaluate(signal):
    """Network evidence prepared outside locks, checked again in the apply transaction."""
    now = datetime.now(timezone.utc)
    prepared, profile = None, None
    eligible = signal['verification'] == 'VERIFIED' and signal['severity'] in {'HIGH','MEDIUM'}
    if eligible:
        try:
            from core_banking.adapter import CoreBankingAdapter
            from customer_sources import CustomerMasterAdapter, validate_resource
            prepared = [CoreBankingAdapter().client.fetch_loan_balance(loan)['data'] for loan in signal['loan_ids']]
            if any(s['debtor_cif'] != signal['debtor_cif'] or not -30 <= (now-instant(s['as_of'])).total_seconds() <= 900 for s in prepared):
                raise ValueError('Untrusted Core evidence')
            profile = validate_resource(CustomerMasterAdapter().fetch(signal['debtor_cif']), 'profile', signal['debtor_cif'], now, 'SYNTHETIC')['items'][0]
        except (ValueError, ConnectionError, KeyError):
            prepared = None
    with closing(get_connection()) as conn, conn:
        conn.execute('BEGIN IMMEDIATE')
        current = conn.execute('SELECT * FROM ews_signal_versions WHERE signal_id=?', (signal['signal_id'],)).fetchone()
        if not current or current['signal_version'] != signal['signal_version']:
            return 'REVISION_CHANGED'
        previous = conn.execute('SELECT decision FROM ews_policy_decisions WHERE signal_id=? AND signal_version=? AND policy_version=?',
                                (signal['signal_id'], signal['signal_version'], POLICY)).fetchone()
        if previous and previous['decision'] == 'APPLIED':
            return 'APPLIED'
        case_id = None
        if signal['verification'] == 'DISMISSED':
            decision, reason = 'NO_ACTION', 'Signal dismissed; previous handoffs remain audit history'
        elif signal['verification'] != 'VERIFIED':
            decision, reason = 'DEFER_VERIFICATION', 'Unverified signal cannot create a collection case'
        elif signal['severity'] == 'LOW':
            decision, reason = 'MONITOR', 'Low severity remains monitoring'
        elif prepared is None:
            decision, reason = 'DEFER_SOURCE', 'Fresh Core and CRM identity evidence required'
        elif not any(s['overdue_amount'] > 0 and s['dpd'] > 0 for s in prepared):
            decision, reason = 'MONITOR', 'No overdue obligation in the explicit signal scope'
        else:
            linked = [dict(r) for r in conn.execute('SELECT c.* , e.loan_id AS linked_loan FROM cases c JOIN case_exposures e ON c.case_id=e.case_id WHERE e.loan_id IN (' + ','.join('?' for _ in signal['loan_ids']) + ')', signal['loan_ids'])]
            ids = {r['case_id'] for r in linked}
            if linked and (len(ids) != 1 or {r['linked_loan'] for r in linked} != set(signal['loan_ids']) or any(r['debtor_cif'] != signal['debtor_cif'] for r in linked)):
                decision, reason = 'DEFER_SCOPE', 'Ambiguous or partially linked loans; no automatic merge'
            elif linked and any(r['lifecycle'] != 'OPEN' or r['contact_hold_reason'] for r in linked):
                decision, reason = 'DEFER_CASE_STATE', 'Existing closed/held case requires review; never auto-reopen'
                case_id = linked[0]['case_id']
            else:
                if linked:
                    case_id = linked[0]['case_id']
                else:
                    case_id = 'EWS-' + stable(signal['signal_id'])
                    # Explicit synthetic policy creation; no assumed phone, collector, experiment or PTP.
                    conn.execute('''INSERT INTO cases(case_id,loan_id,debtor_cif,full_name,phone_e164,product_code,dpd,
                        overdue_amount,total_balance,status,experiment_arm,created_at,updated_at,data_origin)
                        VALUES (?,?,?,?,'','UNKNOWN',0,0,0,'IN_TREATMENT','UNASSIGNED',?,?,'SYNTHETIC')''',
                        (case_id, signal['loan_ids'][0], signal['debtor_cif'], profile['legal_name'], now.isoformat(), now.isoformat()))
                    for s in prepared:
                        conn.execute('''INSERT INTO case_exposures(case_id,loan_id,debtor_cif,overdue_vnd,principal_vnd,interest_vnd,dpd)
                            VALUES (?,?,?,0,0,0,0)''', (case_id, s['loan_id'], signal['debtor_cif']))
                    CaseService().execute(case_id, 'ews-initial-balance', 0, 'balance', {'snapshots': prepared}, connection=conn)
                c = conn.execute('SELECT * FROM cases WHERE case_id=?', (case_id,)).fetchone()
                decision = 'APPLIED'
                reason = f"{POLICY}: verified {signal['severity']} signal v{signal['signal_version']}; explicit loan scope; review treatment, no contact executed"
                CaseService().execute(case_id, 'handoff:' + stable(signal['event_id']), c['case_version'], 'policy_handoff',
                                      {'signal_id': signal['signal_id'], 'signal_version': signal['signal_version'], 'reason': reason}, connection=conn)
        conn.execute('INSERT OR REPLACE INTO ews_policy_decisions VALUES (?,?,?,?,?,?,?)',
                     (signal['signal_id'], signal['signal_version'], POLICY, decision, reason, case_id, now.isoformat()))
    return decision


def sync_ews(cif):
    demo_only()
    received = receive('ews', cif)
    ingest_signals(cif)
    with closing(get_connection()) as conn:
        signals = [json.loads(r['payload']) for r in conn.execute("SELECT v.payload FROM ews_signal_versions v JOIN workspace_ews_signals s ON s.signal_id=v.signal_id WHERE s.debtor_cif=?", (cif,))]
        pending = conn.execute("SELECT 1 FROM integration_inbox WHERE kind='ews' AND stream_id=? AND state!='APPLIED'", (cif,)).fetchone()
    decisions = {}
    if pending:
        return {'received': received, 'decisions': {}, 'status': 'QUARANTINED', 'policy_version': POLICY}
    if received['status'] == 'RECEIVED':
        for signal in signals:
            try:
                decisions[signal['signal_id']] = evaluate(signal)
            except (ValueError, KeyError):
                decisions[signal['signal_id']] = 'RETRY_REQUIRED'
                with closing(get_connection()) as conn, conn:
                    conn.execute('INSERT OR REPLACE INTO ews_policy_decisions VALUES (?,?,?,?,?,NULL,?)',
                                 (signal['signal_id'], signal['signal_version'], POLICY, 'RETRY_REQUIRED', 'Transaction rejected; retry after reviewing current evidence', datetime.now(timezone.utc).isoformat()))
    with closing(get_connection()) as conn:
        targets = [dict(r) for r in conn.execute('''SELECT d.signal_id,d.signal_version,d.case_id,d.decision FROM ews_policy_decisions d
            JOIN workspace_ews_signals s ON s.signal_id=d.signal_id WHERE s.debtor_cif=? ORDER BY d.evaluated_at DESC''', (cif,))]
    return {'received': received, 'decisions': decisions, 'policy_version': POLICY, 'targets': targets}
