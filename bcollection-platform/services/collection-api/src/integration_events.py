"""Durable inbox/cursors and transactional outbox; no network in a DB transaction."""
from contextlib import closing
from datetime import datetime, timezone, timedelta
import hashlib
import json
import os
from uuid import uuid4, uuid5, NAMESPACE_URL


def fingerprint(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(',', ':')).encode()).hexdigest()


def demo_only():
    if os.getenv('BCOLLECTION_MODE') != 'demo-http':
        raise ValueError('Event integration is enabled only in demo-http')


def migrate(conn):
    conn.execute('''CREATE TABLE IF NOT EXISTS integration_streams (
        kind TEXT NOT NULL, stream_id TEXT NOT NULL, cursor INTEGER NOT NULL DEFAULT 0,
        complete_through TEXT, applied_through TEXT, last_error TEXT, updated_at TEXT,
        PRIMARY KEY(kind,stream_id))''')
    conn.execute('''CREATE TABLE IF NOT EXISTS integration_inbox (
        kind TEXT NOT NULL, stream_id TEXT NOT NULL, event_id TEXT NOT NULL, sequence INTEGER NOT NULL,
        payload TEXT NOT NULL, payload_hash TEXT NOT NULL, state TEXT NOT NULL, error TEXT,
        received_at TEXT NOT NULL, PRIMARY KEY(kind,event_id), UNIQUE(kind,stream_id,sequence))''')
    if 'debtor_cif' not in {r[1] for r in conn.execute('PRAGMA table_info(integration_streams)')}:
        conn.execute('ALTER TABLE integration_streams ADD COLUMN debtor_cif TEXT')
    conn.execute('''CREATE TABLE IF NOT EXISTS outcome_outbox (
        event_id TEXT PRIMARY KEY, case_id TEXT NOT NULL, case_version INTEGER NOT NULL,
        payload TEXT NOT NULL, state TEXT NOT NULL DEFAULT 'PENDING', attempts INTEGER NOT NULL DEFAULT 0,
        next_attempt_at TEXT NOT NULL, lease_until TEXT, lease_token TEXT, last_error TEXT, receipt_id TEXT,
        created_at TEXT NOT NULL, delivered_at TEXT)''')
    conn.execute('''CREATE TABLE IF NOT EXISTS ews_signal_versions (
        signal_id TEXT PRIMARY KEY, signal_version INTEGER NOT NULL, payload_hash TEXT NOT NULL,
        payload TEXT NOT NULL, event_id TEXT NOT NULL)''')
    conn.execute('''CREATE TABLE IF NOT EXISTS ews_policy_decisions (
        signal_id TEXT NOT NULL, signal_version INTEGER NOT NULL, policy_version TEXT NOT NULL,
        decision TEXT NOT NULL, reason TEXT NOT NULL, case_id TEXT, evaluated_at TEXT NOT NULL,
        PRIMARY KEY(signal_id,signal_version,policy_version))''')


def receive(kind, stream):
    from database import get_connection
    from event_sources import EventSourceAdapter
    from rest_transport import AdapterError
    demo_only()
    for _ in range(20):  # Bounded work per user action; resume cursor on next run.
        with closing(get_connection()) as conn:
            row = conn.execute('SELECT cursor FROM integration_streams WHERE kind=? AND stream_id=?', (kind, stream)).fetchone()
            cursor = row['cursor'] if row else 0
        try:
            page = EventSourceAdapter().fetch(kind, stream, cursor)
            now = datetime.now(timezone.utc).isoformat()
            with closing(get_connection()) as conn, conn:
                conn.execute('BEGIN IMMEDIATE')
                conn.execute('INSERT OR IGNORE INTO integration_streams(kind,stream_id) VALUES (?,?)', (kind, stream))
                current = conn.execute('SELECT * FROM integration_streams WHERE kind=? AND stream_id=?', (kind, stream)).fetchone()
                if current['cursor'] != cursor:
                    continue
                if current['debtor_cif'] and current['debtor_cif'] != page['debtor_cif']:
                    raise AdapterError('STREAM_IDENTITY_CHANGED')
                watermark = None if page['has_more'] else page['complete_through']
                if watermark and current['complete_through'] and datetime.fromisoformat(watermark) < datetime.fromisoformat(current['complete_through']):
                    raise AdapterError('WATERMARK_REGRESSION')
                for event in page['events']:
                    previous = conn.execute('SELECT payload_hash FROM integration_inbox WHERE kind=? AND event_id=?', (kind, event['event_id'])).fetchone()
                    digest = fingerprint(event)
                    if previous:
                        raise AdapterError('EVENT_ID_CONFLICT')
                    if kind == 'payment' and current['complete_through'] and datetime.fromisoformat(event['occurred_at']) <= datetime.fromisoformat(current['complete_through']):
                        raise AdapterError('SEALED_HISTORY_CHANGED')
                    conn.execute('INSERT INTO integration_inbox VALUES (?,?,?,?,?,?,\'RECEIVED\',NULL,?)',
                                 (kind, stream, event['event_id'], event['sequence'], json.dumps(event, sort_keys=True), digest, now))
                conn.execute('UPDATE integration_streams SET cursor=?,complete_through=COALESCE(?,complete_through),last_error=NULL,updated_at=?,debtor_cif=? WHERE kind=? AND stream_id=?',
                             (page['next_cursor'], watermark, now, page['debtor_cif'], kind, stream))
            if not page['has_more']:
                return {'status': 'RECEIVED', 'cursor': page['next_cursor']}
        except (AdapterError, ValueError, KeyError) as exc:
            code = exc.code if isinstance(exc, AdapterError) else 'NOT_CONFIGURED'
            with closing(get_connection()) as conn, conn:
                conn.execute('INSERT OR IGNORE INTO integration_streams(kind,stream_id) VALUES (?,?)', (kind, stream))
                conn.execute('UPDATE integration_streams SET last_error=?,updated_at=? WHERE kind=? AND stream_id=?',
                             (code, datetime.now(timezone.utc).isoformat(), kind, stream))
            return {'status': code}
    return {'status': 'MORE_PAGES'}


def enqueue_outcome(conn, case_id, command_id, kind, now, payment=None):
    if os.getenv('BCOLLECTION_MODE') != 'demo-http':
        return
    case = dict(conn.execute('SELECT * FROM cases WHERE case_id=?', (case_id,)).fetchone())
    event_id = str(uuid5(NAMESPACE_URL, f'bcollection:outcome:{case_id}:{command_id}'))
    payload = {'event_id': event_id, 'contract_version': '1.0', 'data_origin': case['data_origin'],
               'case_id': case_id, 'case_version': case['case_version'], 'debtor_cif': case['debtor_cif'],
               'trigger': kind, 'occurred_at': now.isoformat(), 'causal_attribution': False,
               'lifecycle': case['lifecycle'], 'resolution': case['resolution'], 'contact_hold_reason': case['contact_hold_reason'],
               'ptps': [dict(r) for r in conn.execute('SELECT ptp_id,status,amount_vnd,paid_vnd,on_time_vnd,observed_through FROM ptps WHERE case_id=? ORDER BY ptp_id', (case_id,))],
               'handoff_ids': [r[0] for r in conn.execute('SELECT handoff_id FROM workspace_policy_handoffs WHERE case_id=? ORDER BY handoff_id', (case_id,))],
               'payment_event': payment if kind == 'payment' else None}
    conn.execute('INSERT INTO outcome_outbox(event_id,case_id,case_version,payload,next_attempt_at,created_at) VALUES (?,?,?,?,?,?)',
                 (event_id, case_id, case['case_version'], json.dumps(payload, sort_keys=True), now.isoformat(), now.isoformat()))


def publish_outcomes(case_id=None, limit=50, clock=None):
    from database import get_connection
    from event_sources import OutcomePublisherAdapter
    from rest_transport import AdapterError
    demo_only()
    clock = clock or (lambda: datetime.now(timezone.utc))
    delivered, failed = 0, 0
    for _ in range(min(limit, 100)):
        now, token = clock(), str(uuid4())
        with closing(get_connection()) as conn, conn:
            conn.execute('BEGIN IMMEDIATE')
            row = conn.execute('''SELECT * FROM outcome_outbox WHERE (? IS NULL OR case_id=?) AND
                ((state='PENDING' AND next_attempt_at<=?) OR (state='INFLIGHT' AND lease_until<=?))
                ORDER BY created_at,event_id LIMIT 1''', (case_id, case_id, now.isoformat(), now.isoformat())).fetchone()
            if not row:
                break
            conn.execute("UPDATE outcome_outbox SET state='INFLIGHT',attempts=attempts+1,lease_until=?,lease_token=? WHERE event_id=?",
                         ((now + timedelta(seconds=30)).isoformat(), token, row['event_id']))
        try:
            payload = json.loads(row['payload'])
            if payload['data_origin'] != 'SYNTHETIC':
                raise AdapterError('NON_SYNTHETIC_OUTCOME')
            ack = OutcomePublisherAdapter().send(payload)
            with closing(get_connection()) as conn, conn:
                conn.execute("UPDATE outcome_outbox SET state='DELIVERED',receipt_id=?,delivered_at=?,last_error=NULL,lease_until=NULL WHERE event_id=? AND lease_token=?",
                             (ack['receipt_id'], clock().isoformat(), row['event_id'], token))
            delivered += 1
        except (AdapterError, ValueError, KeyError) as exc:
            code = exc.code if isinstance(exc, AdapterError) else 'NOT_CONFIGURED'
            with closing(get_connection()) as conn, conn:
                conn.execute("UPDATE outcome_outbox SET state='PENDING',last_error=?,next_attempt_at=?,lease_until=NULL WHERE event_id=? AND lease_token=?",
                             (code, (clock() + timedelta(seconds=min(60, 2 ** min(row['attempts'] + 1, 6)))).isoformat(), row['event_id'], token))
            failed += 1
    return {'delivered': delivered, 'failed': failed}


def read_state(conn, case):
    case_id = case['case_id']
    streams = [dict(r) for r in conn.execute("SELECT * FROM integration_streams WHERE (kind='payment' AND stream_id IN (SELECT loan_id FROM case_exposures WHERE case_id=?)) OR (kind='ews' AND stream_id=?) ORDER BY kind,stream_id", (case_id, case['debtor_cif']))]
    pending = [dict(r) for r in conn.execute("SELECT event_id,stream_id,state,error FROM integration_inbox WHERE kind='payment' AND state!='APPLIED' AND stream_id IN (SELECT loan_id FROM case_exposures WHERE case_id=?) ORDER BY sequence LIMIT 100", (case_id,))]
    pending_ews = [dict(r) for r in conn.execute("SELECT event_id,state,error FROM integration_inbox WHERE kind='ews' AND stream_id=? AND state!='APPLIED' ORDER BY sequence LIMIT 100", (case['debtor_cif'],))]
    decisions = [dict(r) for r in conn.execute('''SELECT d.* FROM ews_policy_decisions d JOIN workspace_ews_signals s ON d.signal_id=s.signal_id
        WHERE s.debtor_cif=? ORDER BY d.evaluated_at DESC LIMIT 100''', (case['debtor_cif'],))]
    counts = {r[0]: r[1] for r in conn.execute('SELECT state,COUNT(*) FROM outcome_outbox WHERE case_id=? GROUP BY state', (case_id,))}
    deliveries = [dict(r) for r in conn.execute('SELECT event_id,case_version,state,attempts,last_error,receipt_id,delivered_at FROM outcome_outbox WHERE case_id=? ORDER BY created_at DESC LIMIT 20', (case_id,))]
    return {'streams': streams, 'pending_payments': pending, 'pending_ews': pending_ews, 'ews_decisions': decisions,
            'delivery': {'pending': counts.get('PENDING',0)+counts.get('INFLIGHT',0), 'delivered': counts.get('DELIVERED',0), 'events': deliveries}}
