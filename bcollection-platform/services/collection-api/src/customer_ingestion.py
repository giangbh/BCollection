"""Versioned Customer 360 source projections. Never mutates case/financial/PTP state."""
from contextlib import closing
from datetime import datetime, timezone
import hashlib
import json
import os
from uuid import uuid4

from customer_sources import (CustomerMasterAdapter, CoreCustomerAdapter, CollateralAdapter,
                              DirectoryAdapter, validate_resource)
from rest_transport import AdapterError


def migrate(conn):
    conn.execute('''CREATE TABLE IF NOT EXISTS customer_source_snapshots (
        debtor_cif TEXT NOT NULL, resource TEXT NOT NULL, source_version INTEGER NOT NULL,
        source_as_of TEXT NOT NULL, payload_hash TEXT NOT NULL, payload TEXT NOT NULL,
        received_at TEXT NOT NULL, PRIMARY KEY(debtor_cif,resource))''')
    conn.execute('''CREATE TABLE IF NOT EXISTS customer_source_attempts (
        attempt_id TEXT PRIMARY KEY, debtor_cif TEXT NOT NULL, resource TEXT NOT NULL,
        status TEXT NOT NULL, attempted_at TEXT NOT NULL)''')
    conn.execute('CREATE INDEX IF NOT EXISTS source_attempts_customer ON customer_source_attempts(debtor_cif,attempted_at)')


def synchronize(cif):
    from database import get_connection
    if os.getenv('BCOLLECTION_MODE') != 'demo-http':
        raise ValueError('ADP-02 ingestion enabled only in demo-http')
    core = CoreCustomerAdapter()
    fetchers = {'profile': lambda: CustomerMasterAdapter().fetch(cif),
                'loans': lambda: core.fetch(cif, 'loans'), 'history': lambda: core.fetch(cif, 'history'),
                'collateral': lambda: CollateralAdapter().fetch(cif),
                'directory': lambda: DirectoryAdapter().fetch(cif)}
    statuses = {}
    for kind, fetch in fetchers.items():
        now = datetime.now(timezone.utc)
        try:
            raw = validate_resource(fetch(), kind, cif, now, 'SYNTHETIC')
            payload = json.dumps(raw, sort_keys=True, separators=(',', ':'))
            digest = hashlib.sha256(payload.encode()).hexdigest()
            status = 'RECORDED' if raw['items'] else 'EMPTY'
            with closing(get_connection()) as conn, conn:
                conn.execute('BEGIN IMMEDIATE')
                previous = conn.execute('SELECT * FROM customer_source_snapshots WHERE debtor_cif=? AND resource=?', (cif, kind)).fetchone()
                if previous and json.loads(previous['payload'])['source_system'] != raw['source_system']:
                    status = 'SOURCE_CONFLICT'
                elif previous and (raw['source_version'] < previous['source_version'] or
                                 datetime.fromisoformat(raw['as_of']) < datetime.fromisoformat(previous['source_as_of'])):
                    status = 'OUT_OF_ORDER'
                elif previous and raw['source_version'] == previous['source_version']:
                    status = 'UNCHANGED' if digest == previous['payload_hash'] else 'VERSION_CONFLICT'
                else:
                    conn.execute('INSERT OR REPLACE INTO customer_source_snapshots VALUES (?,?,?,?,?,?,?)',
                                 (cif, kind, raw['source_version'], raw['as_of'], digest, payload, now.isoformat()))
                    if kind == 'profile':
                        p = raw['items'][0]
                        conn.execute('INSERT OR REPLACE INTO customer_profiles VALUES (?,?,?,?,?,?,?,?,?,?)',
                                     (cif, p['party_type'], p['legal_name'], p['tax_id'], p['industry'], p['region'],
                                      None, raw['source_system'], raw['as_of'], raw['data_origin']))
                conn.execute('INSERT INTO customer_source_attempts VALUES (?,?,?,?,?)',
                             (str(uuid4()), cif, kind, status, now.isoformat()))
        except (AdapterError, KeyError, ValueError) as exc:
            status = exc.code if isinstance(exc, AdapterError) else 'NOT_CONFIGURED'
            with closing(get_connection()) as conn, conn:
                conn.execute('INSERT INTO customer_source_attempts VALUES (?,?,?,?,?)',
                             (str(uuid4()), cif, kind, status, now.isoformat()))
        statuses[kind] = status
    return {'debtor_cif': cif, 'resources': statuses, 'financial_state_changed': False}


def read_sources(conn, cif, now):
    result = {}
    for kind in ('profile', 'loans', 'history', 'collateral', 'directory'):
        row = conn.execute('SELECT * FROM customer_source_snapshots WHERE debtor_cif=? AND resource=?', (cif, kind)).fetchone()
        attempt = conn.execute('SELECT status,attempted_at FROM customer_source_attempts WHERE debtor_cif=? AND resource=? ORDER BY attempted_at DESC,rowid DESC LIMIT 1', (cif, kind)).fetchone()
        payload = json.loads(row['payload']) if row else None
        age = (now - datetime.fromisoformat(row['source_as_of'])).total_seconds() if row else None
        status = attempt['status'] if attempt else 'NOT_CONNECTED'
        if status in {'RECORDED', 'UNCHANGED', 'EMPTY'} and age is not None and age > 86400:
            status = 'STALE'
        result[kind] = {'status': status, 'last_attempt_at': attempt['attempted_at'] if attempt else None,
                        'received_at': row['received_at'] if row else None, 'snapshot': payload}
    return result


def enrich_context(context, sources):
    """Source profile is read-only; directory does not grant collector identity."""
    profile = sources['profile']['snapshot']
    if profile:
        p = profile['items'][0]
        directory = sources['directory']['snapshot']
        staff = next((s for s in directory['items'] if s['user_id'] == p['rm_user_id']), None) if directory else None
        context['customer_profile'] = {**p, 'rm_name': staff['display_name'] if staff else None,
                                      'source': profile['source_system'], 'source_as_of': profile['as_of'],
                                      'data_origin': profile['data_origin']}
    context['source_data'] = sources
    for capability, resource in (('profile', 'profile'), ('loan_terms', 'loans'), ('collateral', 'collateral')):
        if sources[resource]['snapshot'] or sources[resource]['status'] != 'NOT_CONNECTED':
            context['capabilities'][capability] = sources[resource]['status']
    return context


def imported_history(source, loans, now):
    from zoneinfo import ZoneInfo
    local = now.astimezone(ZoneInfo('Asia/Ho_Chi_Minh'))
    index = local.year * 12 + local.month - 1
    points = []
    rows = source['snapshot']['items']
    for month in [f'{i // 12:04d}-{i % 12 + 1:02d}' for i in range(index - 11, index + 1)]:
        by_loan = {}
        for item in rows:
            at = datetime.fromisoformat(item['observed_at'])
            if item['loan_id'] in loans and at <= now and at.astimezone(local.tzinfo).strftime('%Y-%m') == month:
                previous = by_loan.get(item['loan_id'])
                if previous is None or at > datetime.fromisoformat(previous['observed_at']):
                    by_loan[item['loan_id']] = item
        complete = bool(loans) and len(by_loan) == len(loans)
        values = [p['dpd'] for p in by_loan.values()]
        dates = [p['observed_at'] for p in by_loan.values()]
        points.append({'month': month, 'max_dpd': max(values) if complete else None,
                       'average_dpd': round(sum(values) / len(values), 1) if complete else None,
                       'observed_loans': len(values), 'scope_loans': len(loans),
                       'oldest_as_of': min(dates) if dates else None, 'newest_as_of': max(dates) if dates else None})
    return {'status': source['status'], 'definition': 'SOURCE_LATEST_OBSERVATION_PER_LOAN_MONTH_CURRENT_SCOPE', 'points': points}
