"""Synthetic event streams and idempotent outcome receiver; mutation via CLI only."""
from contextlib import closing
from datetime import datetime, timezone
import hashlib
import json
import sqlite3
from uuid import uuid4
from fastapi import HTTPException, Query, Header


def migrate(conn):
    conn.execute('''CREATE TABLE IF NOT EXISTS mock_event_streams (
        kind TEXT NOT NULL,stream_id TEXT NOT NULL,complete_through TEXT,PRIMARY KEY(kind,stream_id))''')
    conn.execute('''CREATE TABLE IF NOT EXISTS mock_events (
        kind TEXT NOT NULL,stream_id TEXT NOT NULL,event_id TEXT NOT NULL,sequence INTEGER NOT NULL,
        payload TEXT NOT NULL,effect TEXT,PRIMARY KEY(kind,event_id),UNIQUE(kind,stream_id,sequence))''')
    conn.execute('''CREATE TABLE IF NOT EXISTS mock_outcomes (
        event_id TEXT PRIMARY KEY,payload_hash TEXT NOT NULL,payload TEXT NOT NULL,receipt_id TEXT NOT NULL)''')
    conn.execute('''CREATE TABLE IF NOT EXISTS mock_outcome_latest (
        case_id TEXT PRIMARY KEY,case_version INTEGER NOT NULL,event_id TEXT NOT NULL)''')


def instant(value=None):
    at = datetime.fromisoformat(value) if value else datetime.now(timezone.utc)
    if at.tzinfo is None or at > datetime.now(timezone.utc):
        raise ValueError('Non-future timezone-aware timestamp required')
    return at


def append(conn, kind, stream, payload, effect=None):
    sequence = conn.execute('SELECT COALESCE(MAX(sequence),0)+1 FROM mock_events WHERE kind=? AND stream_id=?', (kind, stream)).fetchone()[0]
    payload = {**payload, 'sequence': sequence}
    conn.execute('INSERT INTO mock_events VALUES (?,?,?,?,?,?)', (kind, stream, payload['event_id'], sequence, json.dumps(payload), json.dumps(effect)))
    conn.execute('INSERT OR IGNORE INTO mock_event_streams VALUES (?,?,NULL)', (kind, stream))
    return payload


def payment(path, loan_id, event_id, amount=None, reverses=None, occurred_at=None):
    from legacy_mock import initialize
    initialize(path)
    with closing(sqlite3.connect(path)) as conn, conn:
        conn.execute('BEGIN IMMEDIATE')
        loan_row = conn.execute('SELECT payload FROM mock_loans WHERE loan_id=?', (loan_id,)).fetchone()
        if not loan_row:
            raise ValueError('Unknown synthetic loan')
        loan = json.loads(loan_row[0])
        previous = conn.execute("SELECT payload FROM mock_events WHERE kind='payment' AND event_id=?", (event_id,)).fetchone()
        old = json.loads(previous[0]) if previous else None
        at = instant(occurred_at or (old['occurred_at'] if old else None))
        original = None
        if reverses:
            original_row = conn.execute("SELECT payload,effect FROM mock_events WHERE kind='payment' AND event_id=?", (reverses,)).fetchone()
            if not original_row:
                raise ValueError('Original payment required')
            original, effect = json.loads(original_row[0]), json.loads(original_row[1])
            if original['kind'] != 'POSTED' or original['loan_id'] != loan_id or at < instant(original['occurred_at']):
                raise ValueError('Invalid reversal')
            amount = original['amount_vnd']
        if not isinstance(event_id, str) or not 1 <= len(event_id) <= 128 or type(amount) is not int or amount <= 0:
            raise ValueError('Positive integer VND and event ID required')
        event = {'event_id': event_id, 'loan_id': loan_id, 'debtor_cif': loan['debtor_cif'],
                 'amount_vnd': amount, 'occurred_at': at.isoformat(), 'kind': 'REVERSED' if reverses else 'POSTED',
                 'reverses_event_id': reverses}
        if old:
            if {k: v for k, v in old.items() if k != 'sequence'} != event:
                raise ValueError('Event ID conflict')
            return old
        watermark = conn.execute("SELECT complete_through FROM mock_event_streams WHERE kind='payment' AND stream_id=?", (loan_id,)).fetchone()
        if watermark and watermark[0] and at <= instant(watermark[0]):
            raise ValueError('Cannot insert into sealed history')
        if reverses:
            if conn.execute("SELECT 1 FROM mock_events WHERE kind='payment' AND json_extract(payload,'$.reverses_event_id')=?", (reverses,)).fetchone():
                raise ValueError('Already reversed')
            for key in ('outstanding_principal', 'outstanding_interest', 'overdue_amount'):
                loan[key] += effect[key]
            loan['dpd'] = max(loan['dpd'], effect['dpd'])
        else:
            if amount > loan['outstanding_principal'] + loan['outstanding_interest']:
                raise ValueError('Demo payment exceeds outstanding balance')
            interest = min(amount, loan['outstanding_interest'])
            effect = {'outstanding_interest': interest, 'outstanding_principal': amount-interest,
                      'overdue_amount': min(amount, loan['overdue_amount']), 'dpd': loan['dpd']}
            for key in ('outstanding_principal', 'outstanding_interest', 'overdue_amount'):
                loan[key] -= effect[key]
            if not loan['overdue_amount']:
                loan['dpd'] = 0
        loan.update(source_version=loan['source_version'] + 1, as_of=datetime.now(timezone.utc).isoformat())
        conn.execute('UPDATE mock_loans SET payload=? WHERE loan_id=?', (json.dumps(loan), loan_id))
        # Keep the legacy recent-payment safety check consistent with the event feed.
        recent = {'event_id': event_id, 'loan_id': loan_id, 'debtor_cif': loan['debtor_cif'], 'amount_paid': amount,
                  'paid_at': at.isoformat(), 'channel': 'DEMO_REVERSAL' if reverses else 'DEMO_PAYMENT'}
        conn.execute('INSERT INTO mock_payments VALUES (?,?,?)', (event_id, loan_id, json.dumps(recent)))
        return append(conn, 'payment', loan_id, event, effect if not reverses else None)


def seal(path, loan_id, through=None):
    from legacy_mock import initialize
    initialize(path)
    at = instant(through).isoformat()
    with closing(sqlite3.connect(path)) as conn, conn:
        conn.execute('BEGIN IMMEDIATE')
        if not conn.execute('SELECT 1 FROM mock_loans WHERE loan_id=?', (loan_id,)).fetchone():
            raise ValueError('Unknown loan')
        conn.execute("INSERT OR IGNORE INTO mock_event_streams VALUES ('payment',?,NULL)", (loan_id,))
        previous = conn.execute("SELECT complete_through FROM mock_event_streams WHERE kind='payment' AND stream_id=?", (loan_id,)).fetchone()[0]
        if previous and instant(at) < instant(previous):
            raise ValueError('Watermark regression')
        conn.execute("UPDATE mock_event_streams SET complete_through=? WHERE kind='payment' AND stream_id=?", (at, loan_id))
    return {'complete_through': at}


def signal(path, cif, loan_ids, signal_id, event_id, version=1, severity='HIGH', verification='VERIFIED', title='Tín hiệu EWS mô phỏng', occurred_at=None):
    from legacy_mock import initialize
    initialize(path)
    with closing(sqlite3.connect(path)) as conn, conn:
        conn.execute('BEGIN IMMEDIATE')
        for loan in loan_ids:
            row = conn.execute('SELECT payload FROM mock_loans WHERE loan_id=?', (loan,)).fetchone()
            if not row or json.loads(row[0])['debtor_cif'] != cif:
                raise ValueError('Loan/CIF mismatch')
        previous = conn.execute("SELECT payload FROM mock_events WHERE kind='ews' AND event_id=?", (event_id,)).fetchone()
        old = json.loads(previous[0]) if previous else None
        event = {'event_id': event_id, 'debtor_cif': cif, 'loan_ids': loan_ids, 'signal_id': signal_id,
                 'signal_version': version, 'severity': severity, 'verification': verification, 'title': title,
                 'occurred_at': instant(occurred_at or (old['occurred_at'] if old else None)).isoformat()}
        if not loan_ids or len(set(loan_ids)) != len(loan_ids) or severity not in {'HIGH','MEDIUM','LOW'} or verification not in {'VERIFIED','UNVERIFIED','DISMISSED'} or version < 1:
            raise ValueError('Invalid signal')
        if old:
            if {k: v for k, v in old.items() if k != 'sequence'} != event:
                raise ValueError('Event ID conflict')
            return old
        last = conn.execute("SELECT MAX(CAST(json_extract(payload,'$.signal_version') AS INTEGER)) FROM mock_events WHERE kind='ews' AND json_extract(payload,'$.signal_id')=?", (signal_id,)).fetchone()[0]
        if last and version <= last:
            raise ValueError('Signal version must advance')
        return append(conn, 'ews', cif, event)


def register(app, path):
    def page(kind, stream, cursor, limit):
        with closing(sqlite3.connect(path)) as conn:
            conn.execute('BEGIN')
            if kind == 'payment' and not conn.execute('SELECT 1 FROM mock_loans WHERE loan_id=?', (stream,)).fetchone():
                raise HTTPException(404)
            if kind == 'ews' and not conn.execute("SELECT 1 FROM mock_loans WHERE json_extract(payload,'$.debtor_cif')=?", (stream,)).fetchone():
                raise HTTPException(404)
            rows = conn.execute('SELECT payload FROM mock_events WHERE kind=? AND stream_id=? AND sequence>? ORDER BY sequence LIMIT ?', (kind, stream, cursor, limit+1)).fetchall()
            watermark = conn.execute('SELECT complete_through FROM mock_event_streams WHERE kind=? AND stream_id=?', (kind, stream)).fetchone()
            maximum = conn.execute('SELECT COALESCE(MAX(sequence),0) FROM mock_events WHERE kind=? AND stream_id=?', (kind, stream)).fetchone()[0]
            cif = json.loads(conn.execute('SELECT payload FROM mock_loans WHERE loan_id=?', (stream,)).fetchone()[0])['debtor_cif'] if kind == 'payment' else stream
            if cursor > maximum:
                raise HTTPException(409, 'Cursor exceeds source; do not silently reset')
        return {'contract_version': '1.0', 'data_origin': 'SYNTHETIC', 'source_system': 'MOCK_CORE' if kind == 'payment' else 'MOCK_EWS',
                'stream_id': stream, 'debtor_cif': cif, 'after_cursor': cursor, 'next_cursor': cursor + min(limit, len(rows)),
                'has_more': len(rows) > limit, 'complete_through': watermark[0] if watermark else None,
                'events': [json.loads(r[0]) for r in rows[:limit]]}

    @app.get('/core/v1/loans/{loan_id}/payment-events')
    def payment_events(loan_id: str, cursor: int = Query(0, ge=0), limit: int = Query(100, ge=1, le=100)):
        return page('payment', loan_id, cursor, limit)

    @app.get('/ews/v1/customers/{cif}/signals')
    def signals(cif: str, cursor: int = Query(0, ge=0), limit: int = Query(100, ge=1, le=100)):
        return page('ews', cif, cursor, limit)

    @app.post('/ews/v1/collection-outcomes')
    def receive_outcome(payload: dict, idempotency_key: str = Header()):
        if (not isinstance(payload.get('event_id'), str) or not 1 <= len(payload['event_id']) <= 128
                or payload.get('event_id') != idempotency_key or payload.get('data_origin') != 'SYNTHETIC'
                or payload.get('contract_version') != '1.0' or type(payload.get('case_version')) is not int
                or payload['case_version'] < 0 or not payload.get('case_id') or payload.get('causal_attribution') is not False):
            raise HTTPException(422, 'Invalid synthetic outcome')
        encoded = json.dumps(payload, sort_keys=True)
        digest = hashlib.sha256(encoded.encode()).hexdigest()
        with closing(sqlite3.connect(path)) as conn, conn:
            conn.execute('BEGIN IMMEDIATE')
            old = conn.execute('SELECT payload_hash,receipt_id FROM mock_outcomes WHERE event_id=?', (idempotency_key,)).fetchone()
            if old:
                if old[0] != digest:
                    raise HTTPException(409, 'Idempotency conflict')
                return {'event_id': idempotency_key, 'accepted': True, 'receipt_id': old[1], 'replayed': True}
            receipt = str(uuid4())
            conn.execute('INSERT INTO mock_outcomes VALUES (?,?,?,?)', (idempotency_key, digest, encoded, receipt))
            conn.execute('''INSERT INTO mock_outcome_latest VALUES (?,?,?) ON CONFLICT(case_id) DO UPDATE
                SET case_version=excluded.case_version,event_id=excluded.event_id WHERE excluded.case_version>mock_outcome_latest.case_version''',
                (payload['case_id'], payload['case_version'], idempotency_key))
        return {'event_id': idempotency_key, 'accepted': True, 'receipt_id': receipt, 'replayed': False}

    @app.get('/ews/v1/collection-outcomes/{case_id}')
    def latest(case_id: str):
        with closing(sqlite3.connect(path)) as conn:
            row = conn.execute('SELECT o.payload FROM mock_outcomes o JOIN mock_outcome_latest l ON l.event_id=o.event_id WHERE l.case_id=?', (case_id,)).fetchone()
        if not row:
            raise HTTPException(404)
        return json.loads(row[0])
