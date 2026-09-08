"""Explicit synthetic bootstrap from REST. Not EWS policy handoff or live onboarding."""
from contextlib import closing
from datetime import datetime, timezone
import os
from uuid import uuid5, NAMESPACE_URL, uuid4
from pydantic import Field
from core_banking.contracts import CoreSnapshot
from core_banking.adapter import CoreBankingAdapter


class PortfolioLoan(CoreSnapshot):
    full_name: str = Field(min_length=1)
    phone_e164: str = Field(min_length=1)
    product_code: str = Field(min_length=1)
    data_origin: str


def import_demo_portfolio():
    from database import get_connection
    if os.getenv('BCOLLECTION_MODE') != 'demo-http':
        raise ValueError('Portfolio bootstrap only in demo-http')
    rows = [PortfolioLoan.model_validate(r) for r in CoreBankingAdapter().get_overdue_portfolio()]
    now = datetime.now(timezone.utc)
    if len({r.loan_id for r in rows}) != len(rows):
        raise ValueError('Duplicate loan IDs')
    for row in rows:
        if row.data_origin != 'SYNTHETIC' or not 0 < row.dpd <= 30 or not -30 <= (now-row.as_of).total_seconds() <= 900:
            raise ValueError('Untrusted synthetic overdue portfolio')
    created = []
    with closing(get_connection()) as conn, conn:
        conn.execute('BEGIN IMMEDIATE')
        for row in rows:
            existing = conn.execute('SELECT debtor_cif FROM case_exposures WHERE loan_id=?', (row.loan_id,)).fetchall()
            if existing:
                if any(e['debtor_cif'] != row.debtor_cif for e in existing):
                    raise ValueError('Loan identity conflict')
                continue  # Never reopen, duplicate, or overwrite an existing case.
            case_id = 'DEMO-' + str(uuid5(NAMESPACE_URL, 'bcollection:core:' + row.loan_id))
            conn.execute('''INSERT INTO cases(case_id,loan_id,debtor_cif,full_name,phone_e164,product_code,dpd,
                overdue_amount,total_balance,status,experiment_arm,created_at,updated_at,data_origin)
                VALUES (?,?,?,?,?,?,?,?,?,'IN_TREATMENT','UNASSIGNED',?,?,'SYNTHETIC')''',
                (case_id, row.loan_id, row.debtor_cif, row.full_name, row.phone_e164, row.product_code, row.dpd,
                 row.overdue_amount, row.outstanding_principal + row.outstanding_interest, now.isoformat(), now.isoformat()))
            conn.execute('''INSERT INTO case_exposures(case_id,loan_id,debtor_cif,overdue_vnd,principal_vnd,interest_vnd,dpd)
                VALUES (?,?,?,?,?,?,?)''', (case_id, row.loan_id, row.debtor_cif, row.overdue_amount,
                                          row.outstanding_principal, row.outstanding_interest, row.dpd))
            conn.execute('''INSERT INTO case_transition_log VALUES (?,?,?,'OPEN','OPEN',NULL,NULL,'DEMO_REST_PORTFOLIO_IMPORT',0,?)''',
                         (str(uuid4()), case_id, 'DEMO_BOOTSTRAP', now.isoformat()))
            created.append(case_id)
    return {'created': created, 'skipped': len(rows)-len(created), 'scope': 'OVERDUE_DPD_1_30_ONLY',
            'data_origin': 'SYNTHETIC', 'balances_verified': False}
