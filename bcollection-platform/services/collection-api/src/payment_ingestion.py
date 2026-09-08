"""Inbox -> CaseService -> ledger/PTP/outbox, atomically per event."""
from contextlib import closing
from datetime import datetime, timezone
import json
from uuid import uuid5, NAMESPACE_URL

from integration_events import demo_only, receive
from case_service import CaseService, CaseConflict
from bc_domain.case_rules import instant
from database import get_connection


def command_id(prefix, value):
    return prefix + ':' + str(uuid5(NAMESPACE_URL, value))


def drain_payments(loan_id, case_id):
    for _ in range(2):  # Posted events may follow their reversal in delivery order.
        with closing(get_connection()) as conn:
            events = [r['event_id'] for r in conn.execute("SELECT event_id FROM integration_inbox WHERE kind='payment' AND stream_id=? AND state!='APPLIED' ORDER BY sequence", (loan_id,))]
        for event_id in events:
            try:
                with closing(get_connection()) as conn, conn:
                    conn.execute('BEGIN IMMEDIATE')
                    row = conn.execute("SELECT * FROM integration_inbox WHERE kind='payment' AND event_id=?", (event_id,)).fetchone()
                    if row['state'] == 'APPLIED':
                        continue
                    event = json.loads(row['payload'])
                    cases = conn.execute('SELECT c.* FROM cases c JOIN case_exposures e ON c.case_id=e.case_id WHERE e.loan_id=? AND e.debtor_cif=? AND c.debtor_cif=?',
                                         (loan_id, event['debtor_cif'], event['debtor_cif'])).fetchall()
                    if len(cases) != 1 or cases[0]['case_id'] != case_id:
                        raise CaseConflict('AMBIGUOUS_OR_MISSING_CASE')
                    c = cases[0]
                    if c['data_origin'] != 'SYNTHETIC':
                        raise CaseConflict('NON_SYNTHETIC_CASE')
                    payload = {k: event[k] for k in ('event_id', 'loan_id', 'debtor_cif', 'amount_vnd', 'kind', 'occurred_at', 'reverses_event_id')}
                    payload['ptp_id'] = None
                    allocation = 'UNALLOCATED'
                    if event['kind'] == 'POSTED':
                        candidates = [p for p in conn.execute("SELECT * FROM ptps WHERE case_id=? AND loan_id=? AND status NOT IN ('UNVERIFIED','CANCELLED')", (c['case_id'], loan_id))
                                      if instant(p['created_at']) <= instant(event['occurred_at']) <= instant(p['due_at']) and p['paid_vnd'] < p['amount_vnd']]
                        if len(candidates) == 1:
                            payload['ptp_id'] = candidates[0]['ptp_id']
                            allocation = 'PTP_UNIQUE_WINDOW_V1'
                    CaseService().execute(c['case_id'], command_id('core-event', event_id), c['case_version'], 'payment', payload, connection=conn)
                    conn.execute("UPDATE integration_inbox SET state='APPLIED',error=? WHERE kind='payment' AND event_id=?", (allocation if event['kind'] == 'POSTED' else None, event_id))
            except (ValueError, KeyError):
                with closing(get_connection()) as conn, conn:
                    conn.execute("UPDATE integration_inbox SET state='PENDING_REVIEW',error='IDENTITY_ALLOCATION_OR_REVERSAL_DEPENDENCY' WHERE kind='payment' AND event_id=? AND state!='APPLIED'", (event_id,))


def observe_complete(loan_id, case_id):
    with closing(get_connection()) as conn, conn:
        conn.execute('BEGIN IMMEDIATE')
        stream = conn.execute("SELECT * FROM integration_streams WHERE kind='payment' AND stream_id=?", (loan_id,)).fetchone()
        if not stream or stream['last_error'] or not stream['complete_through']:
            return
        if conn.execute("SELECT 1 FROM integration_inbox WHERE kind='payment' AND stream_id=? AND state!='APPLIED'", (loan_id,)).fetchone():
            return
        through = stream['complete_through']
        for p in conn.execute("SELECT * FROM ptps WHERE loan_id=? AND case_id=? AND status NOT IN ('UNVERIFIED','CANCELLED')", (loan_id, case_id)).fetchall():
            unallocated = conn.execute("""SELECT x.occurred_at FROM payment_ledger x WHERE x.loan_id=?
                AND x.kind='POSTED' AND x.ptp_id IS NULL AND NOT EXISTS
                (SELECT 1 FROM payment_ledger r WHERE r.reverses_event_id=x.event_id)""", (loan_id,)).fetchall()
            if any(instant(p['created_at']) <= instant(r['occurred_at']) <= instant(p['due_at']) for r in unallocated):
                continue  # Ambiguous allocation is not evidence that the promise was broken.
            if p['observed_through'] and instant(p['observed_through']) >= instant(through):
                continue
            version = conn.execute('SELECT case_version FROM cases WHERE case_id=?', (p['case_id'],)).fetchone()[0]
            CaseService().execute(p['case_id'], command_id('core-complete', p['ptp_id'] + through), version,
                                  'observe_ptp', {'ptp_id': p['ptp_id'], 'payments_complete_through': through}, connection=conn)
        conn.execute("UPDATE integration_streams SET applied_through=? WHERE kind='payment' AND stream_id=?", (through, loan_id))


def sync_payments(case_id):
    from core_banking.adapter import CoreBankingAdapter
    demo_only()
    with closing(get_connection()) as conn:
        case = conn.execute('SELECT * FROM cases WHERE case_id=?', (case_id,)).fetchone()
        if not case or case['data_origin'] != 'SYNTHETIC':
            raise ValueError('Synthetic case required')
        loans = [r[0] for r in conn.execute('SELECT loan_id FROM case_exposures WHERE case_id=?', (case_id,))]
    results = {}
    for loan in loans:
        results[loan] = receive('payment', loan)
        with closing(get_connection()) as conn, conn:
            stream = conn.execute("SELECT * FROM integration_streams WHERE kind='payment' AND stream_id=?", (loan,)).fetchone()
            if stream and stream['debtor_cif'] and stream['debtor_cif'] != case['debtor_cif']:
                results[loan] = {'status': 'STREAM_IDENTITY_MISMATCH'}
                conn.execute("UPDATE integration_streams SET last_error='STREAM_IDENTITY_MISMATCH' WHERE kind='payment' AND stream_id=?", (loan,))
        if results[loan]['status'] != 'STREAM_IDENTITY_MISMATCH':
            drain_payments(loan, case_id)
        with closing(get_connection()) as conn:
            pending_loan = conn.execute("SELECT 1 FROM integration_inbox WHERE kind='payment' AND stream_id=? AND state!='APPLIED'", (loan,)).fetchone()
        if results[loan]['status'] == 'RECEIVED':
            observe_complete(loan, case_id)
        if results[loan]['status'] not in {'RECEIVED', 'MORE_PAGES'} or pending_loan:
            with closing(get_connection()) as conn, conn:
                conn.execute('BEGIN IMMEDIATE')
                c = conn.execute('SELECT * FROM cases WHERE case_id=?', (case_id,)).fetchone()
                invalidate = results[loan]['status'] in {'SEALED_HISTORY_CHANGED', 'WATERMARK_REGRESSION', 'INVALID_EVENT_CONTRACT', 'EVENT_ID_CONFLICT', 'STREAM_IDENTITY_CHANGED', 'STREAM_IDENTITY_MISMATCH'}
                observed = conn.execute('SELECT 1 FROM ptps WHERE case_id=? AND loan_id=? AND observed_through IS NOT NULL', (case_id, loan)).fetchone()
                if c['contact_hold_reason'] != 'PAYMENT_SOURCE_REVIEW' or (invalidate and observed):
                    CaseService().execute(case_id, command_id('source-hold', loan + str(c['case_version'])), c['case_version'],
                                          'payment_source_hold', {'loan_id': loan, 'invalidate_completeness': invalidate}, connection=conn)
    # Financial reconciliation is separate from event receipt. Failure does not lose inbox/ledger.
    balance = 'NOT_REFRESHED'
    try:
        adapter = CoreBankingAdapter()
        snapshots = [adapter.client.fetch_loan_balance(loan)['data'] for loan in loans]
        with closing(get_connection()) as conn:
            version = conn.execute('SELECT case_version FROM cases WHERE case_id=?', (case_id,)).fetchone()[0]
        from integration_events import fingerprint
        CaseService().execute(case_id, command_id('core-balance', fingerprint(snapshots)), version, 'balance', {'snapshots': snapshots})
        balance = 'REFRESHED'
    except (ValueError, ConnectionError, KeyError):
        balance = 'SOURCE_UNAVAILABLE_OR_CONFLICT'
    with closing(get_connection()) as conn:
        pending = conn.execute("SELECT COUNT(*) FROM integration_inbox WHERE kind='payment' AND stream_id IN (SELECT loan_id FROM case_exposures WHERE case_id=?) AND state!='APPLIED'", (case_id,)).fetchone()[0]
    return {'streams': results, 'pending_review': pending, 'balance': balance,
            'contact_hold_requires_explicit_reconciliation': True}
