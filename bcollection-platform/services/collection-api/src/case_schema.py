"""Additive PR-02 migration; old loan_id and status remain compatibility projections."""
from bc_domain.case_rules import vnd


def migrate(conn):
    columns = {r[1] for r in conn.execute("PRAGMA table_info(cases)")}
    new_lifecycle = "lifecycle" not in columns
    for name, ddl in (
        ("case_version", "INTEGER NOT NULL DEFAULT 0"),
        ("stage", "TEXT NOT NULL DEFAULT 'EARLY_COLLECTION'"),
        ("lifecycle", "TEXT NOT NULL DEFAULT 'OPEN'"),
        ("resolution", "TEXT"),
        ("contact_hold_reason", "TEXT"),
    ):
        if name not in columns:
            conn.execute(f"ALTER TABLE cases ADD COLUMN {name} {ddl}")
    if new_lifecycle:
        conn.execute("UPDATE cases SET lifecycle=status WHERE status IN ('SUSPENDED','PROBATION')")
        conn.execute("UPDATE cases SET lifecycle='CLOSED', resolution='CURED' WHERE status IN ('CURED','RESOLVED_CURED')")
        conn.execute("UPDATE cases SET lifecycle='CLOSED' WHERE status IN ('CLOSED','SETTLED_WRITEOFF')")
    conn.execute("""CREATE TABLE IF NOT EXISTS case_exposures (
        case_id TEXT NOT NULL REFERENCES cases(case_id), loan_id TEXT NOT NULL,
        debtor_cif TEXT NOT NULL, overdue_vnd INTEGER NOT NULL CHECK(overdue_vnd >= 0),
        principal_vnd INTEGER NOT NULL CHECK(principal_vnd >= 0), interest_vnd INTEGER NOT NULL CHECK(interest_vnd >= 0),
        dpd INTEGER NOT NULL CHECK(dpd >= 0), balance_verified INTEGER NOT NULL DEFAULT 0,
        source_version INTEGER NOT NULL DEFAULT -1, source_as_of TEXT, snapshot_hash TEXT,
        PRIMARY KEY(case_id, loan_id))""")
    conn.execute("""CREATE TABLE IF NOT EXISTS ptps (
        ptp_id TEXT PRIMARY KEY, case_id TEXT NOT NULL, loan_id TEXT NOT NULL,
        amount_vnd INTEGER NOT NULL CHECK(amount_vnd > 0), created_at TEXT NOT NULL,
        due_at TEXT NOT NULL, status TEXT NOT NULL, paid_vnd INTEGER NOT NULL DEFAULT 0,
        on_time_vnd INTEGER NOT NULL DEFAULT 0, observed_through TEXT,
        data_origin TEXT NOT NULL, FOREIGN KEY(case_id,loan_id) REFERENCES case_exposures(case_id,loan_id))""")
    conn.execute("""CREATE TABLE IF NOT EXISTS payment_ledger (
        event_id TEXT PRIMARY KEY, case_id TEXT NOT NULL, loan_id TEXT NOT NULL,
        debtor_cif TEXT NOT NULL, kind TEXT NOT NULL CHECK(kind IN ('POSTED','REVERSED')),
        amount_vnd INTEGER NOT NULL CHECK(amount_vnd > 0), occurred_at TEXT NOT NULL,
        reverses_event_id TEXT UNIQUE REFERENCES payment_ledger(event_id),
        ptp_id TEXT REFERENCES ptps(ptp_id), allocated_vnd INTEGER NOT NULL DEFAULT 0,
        data_origin TEXT NOT NULL, FOREIGN KEY(case_id,loan_id) REFERENCES case_exposures(case_id,loan_id))""")
    conn.execute("""CREATE TABLE IF NOT EXISTS case_commands (
        case_id TEXT NOT NULL, command_id TEXT NOT NULL, payload_hash TEXT NOT NULL,
        result_json TEXT NOT NULL, PRIMARY KEY(case_id,command_id))""")
    conn.execute("""CREATE TABLE IF NOT EXISTS case_transition_log (
        transition_id TEXT PRIMARY KEY, case_id TEXT NOT NULL, command_id TEXT NOT NULL,
        from_lifecycle TEXT NOT NULL, to_lifecycle TEXT NOT NULL,
        from_resolution TEXT, to_resolution TEXT, reason TEXT NOT NULL,
        case_version INTEGER NOT NULL, recorded_at TEXT NOT NULL)""")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_ptps_case ON ptps(case_id,loan_id,status)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_payments_case ON payment_ledger(case_id,loan_id,occurred_at)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_payments_ptp ON payment_ledger(ptp_id)")
    backfill(conn)


def backfill(conn):
    # One link per existing case; never merge customers/cases or infer verified balances.
    rows = conn.execute("SELECT * FROM cases c WHERE NOT EXISTS (SELECT 1 FROM case_exposures e WHERE e.case_id=c.case_id AND e.loan_id=c.loan_id)").fetchall()
    for c in rows:
        conn.execute("""INSERT INTO case_exposures
            (case_id,loan_id,debtor_cif,overdue_vnd,principal_vnd,interest_vnd,dpd)
            VALUES (?,?,?,?,?,0,?)""", (c["case_id"], c["loan_id"], c["debtor_cif"], vnd(c["overdue_amount"]), vnd(c["total_balance"]), c["dpd"]))
        if c["ptp_amount"] and c["ptp_date"]:
            # Preserve a legacy promise as evidence only, never mark it kept.
            conn.execute("""INSERT OR IGNORE INTO ptps
                (ptp_id,case_id,loan_id,amount_vnd,created_at,due_at,status,data_origin)
                VALUES (?,?,?,?,?,?,'UNVERIFIED',?)""", (
                "LEGACY-" + c["case_id"], c["case_id"], c["loan_id"], vnd(c["ptp_amount"]),
                c["created_at"], c["ptp_date"], c["data_origin"]))
