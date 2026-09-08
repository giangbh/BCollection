"""Explicit persisted Customer 360 fixture expansion; never reads Collection DB."""
from contextlib import closing
from datetime import datetime, timedelta, timezone
import json
import sqlite3


def seed_customer360(path):
    from legacy_mock import initialize
    initialize(path)
    with closing(sqlite3.connect(path)) as conn, conn:
        conn.execute('BEGIN IMMEDIATE')
        if conn.execute("SELECT 1 FROM mock_metadata WHERE key='customer360'").fetchone():
            return
        loans = [json.loads(r[0]) for r in conn.execute('SELECT payload FROM mock_loans ORDER BY loan_id')]
        if not loans:
            raise ValueError('Seed Core before seed-360')
        # One explicit current loan outside the overdue portfolio/case for scope testing.
        first = loans[0]
        extra = {**first, 'loan_id': first['loan_id'] + '-CURRENT', 'dpd': 0,
                 'overdue_amount': 0, 'outstanding_principal': 100000000, 'outstanding_interest': 0}
        extra['source_record_id'] = extra['loan_id']
        conn.execute('INSERT INTO mock_loans VALUES (?,?)', (extra['loan_id'], json.dumps(extra)))
        loans.append(extra)
        grouped = {}
        for row in loans:
            grouped.setdefault(row['debtor_cif'], []).append(row)
        for index, (cif, customer_loans) in enumerate(grouped.items()):
            at = max(datetime.fromisoformat(row['as_of']) for row in customer_loans)
            org = index % 5 == 0
            profile = {'debtor_cif': cif, 'party_type': 'ORGANIZATION' if org else 'INDIVIDUAL',
                       'legal_name': 'CÔNG TY DEMO ' + cif if org else customer_loans[0]['full_name'],
                       'tax_id': 'DEMO-TAX-' + cif if org else None,
                       'industry': 'Xây dựng (mô phỏng)' if org else 'Nhân viên (mô phỏng)',
                       'region': 'Hà Nội (mô phỏng)', 'rm_user_id': 'DEMO-RM-01'}
            history, items, collateral = [], [], []
            for row in customer_loans:
                items.append({**row, 'repayment_schedule': [
                    {'due_at': (at + timedelta(days=15)).isoformat(), 'amount_vnd': 5000000},
                    {'due_at': (at + timedelta(days=45)).isoformat(), 'amount_vnd': 5000000}]})
                month_index = at.year * 12 + at.month - 1
                for offset in range(12):
                    month = month_index - offset
                    observed = datetime(month // 12, month % 12 + 1, 1, tzinfo=timezone.utc)
                    history.append({'debtor_cif': cif, 'loan_id': row['loan_id'],
                                    'observed_at': observed.isoformat(), 'dpd': max(0, row['dpd'] - offset * 3)})
                if row['product_code'] in {'MORTGAGE', 'AUTO_LOAN'}:
                    collateral.append({'debtor_cif': cif, 'collateral_id': 'COL-' + row['loan_id'],
                                       'loan_ids': [row['loan_id']], 'description': 'Tài sản mô phỏng ' + row['loan_id'],
                                       'valuation_vnd': 600000000, 'valued_at': at.isoformat(), 'legal_status': 'PLEDGED'})
            for kind, source, data in [('profile', 'MOCK_CRM', [profile]), ('loans', 'MOCK_CORE', items),
                                       ('history', 'MOCK_DWH', history), ('collateral', 'MOCK_LOS', collateral),
                                       ('directory', 'MOCK_DIRECTORY', [{'user_id': 'DEMO-RM-01', 'display_name': 'RM mô phỏng', 'org_unit': 'Chi nhánh demo'}])]:
                envelope = {'contract_version': '1.0', 'debtor_cif': cif, 'source_system': source,
                            'source_version': 1, 'as_of': at.isoformat(), 'data_origin': 'SYNTHETIC',
                            'coverage': 'COMPLETE', 'items': data}
                conn.execute('INSERT INTO mock_resources VALUES (?,?,?)', (cif, kind, json.dumps(envelope)))
        conn.execute("INSERT INTO mock_metadata VALUES ('customer360','1')")
