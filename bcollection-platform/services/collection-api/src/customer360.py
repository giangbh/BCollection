"""Customer 360 read projection. No external source is assumed connected.

Source tables are adapter contracts, not collector-editable financial inputs.
DPD observations start with validated Core commands; missing history stays missing.
"""
from datetime import datetime, timezone
from zoneinfo import ZoneInfo
import unicodedata


def search_customers(query):
    from database import get_connection
    def fold(value):
        return ''.join(c for c in unicodedata.normalize('NFD', value or '') if not unicodedata.combining(c)).lower().replace('đ', 'd')
    conn = get_connection()
    try:
        conn.create_function('search_fold', 1, fold, deterministic=True)
        rows = [dict(r) for r in conn.execute('''SELECT c.case_id,c.debtor_cif,
            COALESCE(p.legal_name,c.full_name) AS full_name,c.lifecycle,c.data_origin
            FROM cases c LEFT JOIN customer_profiles p ON p.debtor_cif=c.debtor_cif
            WHERE instr(search_fold(c.full_name || ' ' || c.case_id || ' ' || c.debtor_cif || ' ' || c.phone_e164 || ' ' || COALESCE(p.legal_name,'') || ' ' || COALESCE(p.tax_id,'')),?)>0
            OR EXISTS(SELECT 1 FROM case_exposures e WHERE e.case_id=c.case_id AND instr(search_fold(e.loan_id),?)>0)
            ORDER BY c.updated_at DESC,c.case_id LIMIT 26''', (fold(query.strip()), fold(query.strip())))]
        return {'items': rows[:25], 'has_more': len(rows) > 25, 'coverage': 'RECORDED_IN_BCOLLECTION_ONLY'}
    finally:
        conn.close()


def migrate(conn):
    conn.execute("""CREATE TABLE IF NOT EXISTS customer_profiles (
        debtor_cif TEXT PRIMARY KEY, party_type TEXT NOT NULL CHECK(party_type IN ('INDIVIDUAL','ORGANIZATION')),
        legal_name TEXT NOT NULL, tax_id TEXT, industry TEXT, region TEXT, rm_name TEXT,
        source TEXT NOT NULL, source_as_of TEXT NOT NULL, data_origin TEXT NOT NULL)""")
    conn.execute("""CREATE TABLE IF NOT EXISTS case_notes (
        note_id TEXT PRIMARY KEY, case_id TEXT NOT NULL REFERENCES cases(case_id),
        debtor_cif TEXT NOT NULL, body TEXT NOT NULL CHECK(length(body) BETWEEN 1 AND 2000),
        author TEXT NOT NULL, created_at TEXT NOT NULL, data_origin TEXT NOT NULL)""")
    conn.execute("""CREATE TABLE IF NOT EXISTS exposure_observations (
        case_id TEXT NOT NULL REFERENCES cases(case_id), loan_id TEXT NOT NULL,
        debtor_cif TEXT NOT NULL, source_version INTEGER NOT NULL, source_as_of TEXT NOT NULL,
        dpd INTEGER NOT NULL, snapshot_hash TEXT NOT NULL, data_origin TEXT NOT NULL,
        PRIMARY KEY(case_id,loan_id,source_version))""")
    conn.execute("CREATE INDEX IF NOT EXISTS observations_customer_time ON exposure_observations(debtor_cif,source_as_of)")
    conn.execute("""CREATE TABLE IF NOT EXISTS workspace_ews_signals (
        signal_id TEXT PRIMARY KEY, debtor_cif TEXT NOT NULL, title TEXT NOT NULL,
        severity TEXT NOT NULL CHECK(severity IN ('HIGH','MEDIUM','LOW')),
        verification TEXT NOT NULL CHECK(verification IN ('VERIFIED','UNVERIFIED','DISMISSED')),
        source TEXT NOT NULL, occurred_at TEXT NOT NULL, data_origin TEXT NOT NULL)""")
    conn.execute("""CREATE TABLE IF NOT EXISTS workspace_policy_handoffs (
        handoff_id TEXT PRIMARY KEY, case_id TEXT NOT NULL REFERENCES cases(case_id),
        signal_id TEXT NOT NULL REFERENCES workspace_ews_signals(signal_id),
        policy_version TEXT NOT NULL, decision TEXT NOT NULL, reason TEXT NOT NULL,
        occurred_at TEXT NOT NULL, data_origin TEXT NOT NULL)""")
    conn.execute("""CREATE TABLE IF NOT EXISTS decision_action_links (
        interaction_id TEXT PRIMARY KEY REFERENCES case_interactions(interaction_id),
        feedback_id TEXT NOT NULL REFERENCES decision_feedback(feedback_id),
        ptp_id TEXT REFERENCES ptps(ptp_id), case_id TEXT NOT NULL REFERENCES cases(case_id))""")
    conn.execute('CREATE INDEX IF NOT EXISTS notes_case_time ON case_notes(case_id,created_at)')
    conn.execute('CREATE INDEX IF NOT EXISTS observations_case_time ON exposure_observations(case_id,source_as_of)')
    conn.execute('CREATE INDEX IF NOT EXISTS ews_customer_time ON workspace_ews_signals(debtor_cif,occurred_at)')
    conn.execute('CREATE INDEX IF NOT EXISTS handoffs_case_time ON workspace_policy_handoffs(case_id,occurred_at)')
    conn.execute('CREATE INDEX IF NOT EXISTS action_links_case ON decision_action_links(case_id)')


def dpd_history(conn, case, loans, customer, now):
    """Monthly observations, not month-end claims or imputed zeroes.

Take latest observed snapshot per loan/month; equal-version disagreement is
unknown. Aggregate only if every loan in the CURRENT selected scope is present.
"""
    local = now.astimezone(ZoneInfo('Asia/Ho_Chi_Minh'))
    index = local.year * 12 + local.month - 1
    months = [f'{i // 12:04d}-{i % 12 + 1:02d}' for i in range(index - 11, index + 1)]
    params = (case['debtor_cif'],) if customer else (case['case_id'],)
    where = 'debtor_cif=?' if customer else 'case_id=?'
    boundary = datetime.fromisoformat(months[0] + '-01').replace(tzinfo=local.tzinfo).astimezone(timezone.utc).isoformat()
    rows = conn.execute(f'SELECT * FROM exposure_observations WHERE {where} AND source_as_of>=? ORDER BY source_version', (*params, boundary)).fetchall()
    groups = {}
    for r in rows:
        at = datetime.fromisoformat(r['source_as_of']).astimezone(ZoneInfo('Asia/Ho_Chi_Minh'))
        month = at.strftime('%Y-%m')
        if month not in months or r['loan_id'] not in loans or at > now:
            continue
        groups.setdefault((month, r['loan_id']), []).append(r)
    points = []
    for month in months:
        values, dates = [], []
        for loan in loans:
            copies = groups.get((month, loan), [])
            if not copies:
                continue
            version = max(r['source_version'] for r in copies)
            latest = [r for r in copies if r['source_version'] == version]
            if len({r['snapshot_hash'] for r in latest}) != 1:
                continue
            values.append(latest[0]['dpd'])
            dates.append(latest[0]['source_as_of'])
        complete = bool(loans) and len(values) == len(loans)
        points.append({'month': month, 'max_dpd': max(values) if complete else None,
                       'average_dpd': round(sum(values) / len(values), 1) if complete else None,
                       'observed_loans': len(values), 'scope_loans': len(loans),
                       'oldest_as_of': min(dates) if dates else None, 'newest_as_of': max(dates) if dates else None})
    return {'status': 'OBSERVED' if any(p['observed_loans'] for p in points) else 'NO_HISTORY',
            'definition': 'LATEST_OBSERVATION_PER_LOAN_MONTH_UNWEIGHTED_CURRENT_SCOPE',
            'points': points}


def read_context(conn, case, case_scope, customer_scope, now):
    profile = conn.execute('SELECT * FROM customer_profiles WHERE debtor_cif=?', (case['debtor_cif'],)).fetchone()
    cases = [dict(r) for r in conn.execute('SELECT case_id,lifecycle,stage,resolution,created_at,case_version FROM cases WHERE debtor_cif=? ORDER BY created_at DESC,case_id', (case['debtor_cif'],))]
    signals = [dict(r) for r in conn.execute('SELECT * FROM workspace_ews_signals WHERE debtor_cif=? ORDER BY occurred_at DESC,signal_id', (case['debtor_cif'],))]
    handoffs = [dict(r) for r in conn.execute('''SELECT h.* FROM workspace_policy_handoffs h
        JOIN workspace_ews_signals s ON s.signal_id=h.signal_id
        WHERE h.case_id=? AND s.debtor_cif=? ORDER BY h.occurred_at DESC''', (case['case_id'], case['debtor_cif']))]
    # Explicit links only. A later payment is not automatically attributed to AI.
    links = [dict(r) for r in conn.execute('''SELECT l.*, i.outcome, i.created_at,
        p.status AS ptp_status,p.amount_vnd,p.paid_vnd,p.on_time_vnd,p.observed_through
        FROM decision_action_links l JOIN case_interactions i ON i.interaction_id=l.interaction_id AND i.case_id=l.case_id
        JOIN decision_feedback f ON f.feedback_id=l.feedback_id AND f.case_id=l.case_id
        LEFT JOIN ptps p ON p.ptp_id=l.ptp_id AND p.case_id=l.case_id WHERE l.case_id=? ORDER BY i.created_at DESC''', (case['case_id'],))]
    for link in links:
        link['payments'] = [dict(r) for r in conn.execute('''SELECT event_id,kind,amount_vnd,reverses_event_id,occurred_at
            FROM payment_ledger WHERE case_id=? AND (ptp_id=? OR reverses_event_id IN
            (SELECT event_id FROM payment_ledger WHERE case_id=? AND ptp_id=?)) ORDER BY occurred_at,event_id''',
            (case['case_id'], link['ptp_id'], case['case_id'], link['ptp_id']))]
    return {
        'customer_profile': dict(profile) if profile else None,
        'customer_cases': cases,
        'case_notes': [dict(r) for r in conn.execute('SELECT * FROM case_notes WHERE case_id=? ORDER BY created_at DESC,note_id', (case['case_id'],))],
        'dpd_history': {name: dpd_history(conn, case, {e['loan_id'] for e in scope['exposures']}, name == 'customer', now)
                        for name, scope in (('case', case_scope), ('customer', customer_scope))},
        'ews': {'status': 'RECORDED_EVIDENCE' if signals else 'NOT_CONNECTED', 'signals': signals},
        'policy_handoffs': handoffs,
        'outcome_feedback': {'status': 'LOCAL_TRACE_ONLY', 'causal_attribution': False, 'links': links},
        'capabilities': {'profile': 'RECORDED' if profile else 'NOT_CONNECTED',
                         'assignment': 'NOT_CONNECTED', 'loan_terms': 'NOT_CONNECTED',
                         'risk_model': 'NOT_CONNECTED', 'collateral': 'NOT_CONNECTED',
                         'documents': 'NOT_CONNECTED', 'mentions': 'NOT_CONNECTED',
                         'ews_ingress': 'NOT_CONNECTED', 'outcome_publisher': 'NOT_CONNECTED'},
    }
