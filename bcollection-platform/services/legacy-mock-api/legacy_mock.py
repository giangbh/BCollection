"""Independent synthetic Core REST service. Never opens B.Collection's database."""
from contextlib import closing
from datetime import datetime, timedelta, timezone
import json
from pathlib import Path
import sqlite3

from fastapi import FastAPI, HTTPException, Query


def initialize(path):
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    with closing(sqlite3.connect(path)) as conn, conn:
        tables = {r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")}
        if tables - {"mock_metadata", "mock_loans", "mock_payments", "mock_resources", 'mock_event_streams', 'mock_events', 'mock_outcomes', 'mock_outcome_latest'}:
            raise ValueError("Refusing non-mock database; use a separate empty path")
        conn.execute("CREATE TABLE IF NOT EXISTS mock_metadata(key TEXT PRIMARY KEY, value TEXT NOT NULL)")
        conn.execute("CREATE TABLE IF NOT EXISTS mock_loans(loan_id TEXT PRIMARY KEY, payload TEXT NOT NULL)")
        conn.execute("CREATE TABLE IF NOT EXISTS mock_payments(event_id TEXT PRIMARY KEY, loan_id TEXT NOT NULL, payload TEXT NOT NULL)")
        conn.execute('CREATE TABLE IF NOT EXISTS mock_resources(debtor_cif TEXT NOT NULL,resource TEXT NOT NULL,payload TEXT NOT NULL,PRIMARY KEY(debtor_cif,resource))')
        from event_mock import migrate
        migrate(conn)


def seed(path, loans, manifest, as_of):
    """Explicit immutable seed; repeated same seed does not reset scenario state."""
    initialize(path)
    with closing(sqlite3.connect(path)) as conn, conn:
        conn.execute("BEGIN IMMEDIATE")
        previous = conn.execute("SELECT value FROM mock_metadata WHERE key='manifest'").fetchone()
        encoded = json.dumps(manifest, sort_keys=True)
        if previous:
            if previous[0] != encoded:
                raise ValueError("Existing seed differs; choose a new mock database")
            return
        if conn.execute("SELECT 1 FROM mock_loans").fetchone():
            raise ValueError("Refusing partially seeded database")
        for loan in loans:
            if loan.get("data_origin") != "SYNTHETIC":
                raise ValueError("Synthetic fixtures required")
            row = {**loan, "source_version": 1, "as_of": as_of,
                   "source_system": "MOCK_CORE", "source_record_id": loan["loan_id"]}
            for key in ("overdue_amount", "outstanding_principal", "outstanding_interest"):
                row[key] = int(row[key])
            conn.execute("INSERT INTO mock_loans VALUES (?,?)", (row["loan_id"], json.dumps(row)))
        conn.execute("INSERT INTO mock_metadata VALUES ('manifest',?)", (encoded,))


def advance_snapshot(path, as_of):
    """Explicit source observation. GET never mutates source version/as_of."""
    initialize(path)
    with closing(sqlite3.connect(path)) as conn, conn:
        conn.execute("BEGIN IMMEDIATE")
        for loan_id, payload in conn.execute("SELECT * FROM mock_loans").fetchall():
            row = json.loads(payload)
            if datetime.fromisoformat(as_of) <= datetime.fromisoformat(row["as_of"]):
                raise ValueError("Observation time must advance")
            row.update(as_of=as_of, source_version=row["source_version"] + 1)
            conn.execute("UPDATE mock_loans SET payload=? WHERE loan_id=?", (json.dumps(row), loan_id))
        for cif, resource, payload in conn.execute('SELECT * FROM mock_resources').fetchall():
            row = json.loads(payload)
            if datetime.fromisoformat(as_of) <= datetime.fromisoformat(row['as_of']):
                raise ValueError('Observation time must advance')
            row.update(as_of=as_of, source_version=row['source_version'] + 1)
            if resource == 'loans':
                for item in row['items']:
                    current = json.loads(conn.execute('SELECT payload FROM mock_loans WHERE loan_id=?', (item['loan_id'],)).fetchone()[0])
                    item.update(current)
            conn.execute('UPDATE mock_resources SET payload=? WHERE debtor_cif=? AND resource=?', (json.dumps(row), cif, resource))


def create_app(database_path):
    path = str(database_path)
    initialize(path)
    app = FastAPI(title="B.Collection synthetic legacy REST", version="1.0.0")
    from event_mock import register
    register(app, path)

    @app.middleware("http")
    async def synthetic_header(request, call_next):
        response = await call_next(request)
        response.headers["X-Data-Origin"] = "SYNTHETIC"
        return response

    def loan(loan_id):
        with closing(sqlite3.connect(path)) as conn:
            record = conn.execute("SELECT payload FROM mock_loans WHERE loan_id=?", (loan_id,)).fetchone()
        if not record:
            raise HTTPException(404, "Synthetic loan not found")
        return json.loads(record[0])

    @app.get("/health")
    def health():
        return {"status": "HEALTHY", "data_origin": "SYNTHETIC"}

    @app.get("/{source}/v1/readiness")
    def readiness(source: str):
        if source not in {"core", "los", "cic", "crm", "directory", 'ews'}:
            raise HTTPException(404)
        with closing(sqlite3.connect(path)) as conn:
            seeded = conn.execute("SELECT 1 FROM mock_metadata WHERE key='manifest'").fetchone()
            expanded = conn.execute("SELECT 1 FROM mock_metadata WHERE key='customer360'").fetchone()
        return {"status": ("READY" if seeded else "NO_DATA") if source in {'core', 'ews'} else ('READY' if expanded and source != 'cic' else 'NOT_IMPLEMENTED'),
                "data_origin": "SYNTHETIC", "contract_version": "1.0"}

    @app.get("/core/v1/loans/{loan_id}/balance")
    def balance(loan_id: str):
        row = loan(loan_id)
        row["is_fully_paid"] = not any(row[k] for k in ("overdue_amount", "outstanding_principal", "outstanding_interest"))
        return {"status": "SUCCESS", "data": row, "data_origin": "SYNTHETIC", "contract_version": "1.0"}

    @app.get("/core/v1/loans/{loan_id}/payments")
    def payments(loan_id: str, lookback_minutes: int = Query(default=15, ge=1, le=1440)):
        loan(loan_id)
        cutoff = datetime.now(timezone.utc) - timedelta(minutes=lookback_minutes)
        with closing(sqlite3.connect(path)) as conn:
            rows = [json.loads(r[0]) for r in conn.execute("SELECT payload FROM mock_payments WHERE loan_id=?", (loan_id,))]
        return {"payments": [r for r in rows if datetime.fromisoformat(r["paid_at"]) >= cutoff],
                "data_origin": "SYNTHETIC", "coverage": "RECENT_WINDOW_ONLY", "contract_version": "1.0"}

    @app.get("/core/v1/portfolio/delinquent")
    def portfolio(max_dpd: int = Query(default=30, ge=1, le=9999)):
        with closing(sqlite3.connect(path)) as conn:
            rows = [json.loads(r[0]) for r in conn.execute("SELECT payload FROM mock_loans ORDER BY loan_id")]
        return {"loans": [r for r in rows if 0 < r["dpd"] <= max_dpd], "data_origin": "SYNTHETIC",
                "coverage": "SEEDED_SCENARIO_ONLY", "contract_version": "1.0"}

    @app.get("/core/v1/customers/{cif}/cashflows")
    @app.get("/los/v1/loans/{cif}/parties")
    @app.get("/los/v1/loans/{cif}/collaterals")
    def not_implemented(cif: str):
        raise HTTPException(501, "ADP-01: source dataset not implemented; no inferred defaults")

    @app.get("/cic/v1/reports")
    def reports():
        raise HTTPException(501, "ADP-01: CIC dataset not implemented")

    @app.get('/{source}/v1/customers/{cif}/{resource}')
    def customer_resource(source: str, cif: str, resource: str):
        kind = {('crm', 'profile'): 'profile', ('core', 'loans'): 'loans',
                ('core', 'history'): 'history', ('los', 'collaterals'): 'collateral',
                ('directory', 'staff'): 'directory'}.get((source, resource))
        if not kind:
            raise HTTPException(404)
        with closing(sqlite3.connect(path)) as conn:
            if not conn.execute("SELECT 1 FROM mock_metadata WHERE key='customer360'").fetchone():
                raise HTTPException(501, 'Run seed-360 explicitly')
            row = conn.execute('SELECT payload FROM mock_resources WHERE debtor_cif=? AND resource=?', (cif, kind)).fetchone()
        if not row:
            raise HTTPException(404, 'Customer not in synthetic scenario')
        return json.loads(row[0])

    return app
