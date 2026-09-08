"""Explicit POC lifecycle commands. Run from any working directory."""
import argparse
from datetime import datetime
import json
import os
from pathlib import Path
import sys
from contextlib import closing

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / p) for p in (
    "bcollection-platform/libs", "bcollection-platform/services/collection-api/src",
    "bcollection-platform/services/integration-adapters/src", "bcollection-data", "bcollection-guardrail",
)]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--mode", choices=["demo", "test", "integration", "demo-http"], default=os.getenv("BCOLLECTION_MODE", "demo"))
    parser.add_argument("--database", help="Separate SQLite path for this profile")
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser("init-db", help="Create empty schema only")
    commands.add_parser('import-demo-portfolio', help='Explicit synthetic case bootstrap from Core REST, not policy handoff')
    sync = commands.add_parser('sync-customer', help='Import Customer 360 read projections over REST')
    sync.add_argument('--cif', required=True)
    payments = commands.add_parser('sync-payments')
    payments.add_argument('--case', required=True)
    ews = commands.add_parser('sync-ews')
    ews.add_argument('--cif', required=True)
    publish = commands.add_parser('publish-outcomes')
    publish.add_argument('--case')
    promise = commands.add_parser('create-demo-ptp', help='Explicit manual synthetic promise; does not simulate a call')
    promise.add_argument('--case', required=True)
    promise.add_argument('--loan', required=True)
    promise.add_argument('--command-id', required=True)
    promise.add_argument('--amount', type=int, required=True)
    promise.add_argument('--due', required=True)
    allocate = commands.add_parser('allocate-payment')
    allocate.add_argument('--case', required=True)
    allocate.add_argument('--event-id', required=True)
    allocate.add_argument('--ptp-id', required=True)
    allocate.add_argument('--command-id', required=True)
    allocate.add_argument('--reason', required=True)
    seed = commands.add_parser("seed-demo", help="Explicit synthetic fixtures; never integration")
    seed.add_argument("--seed", type=int, default=42)
    seed.add_argument("--as-of", default="2026-09-01T09:00:00")
    serve = commands.add_parser("serve", help="Start API without seeding")
    serve.add_argument("--port", type=int, default=8088)
    args = parser.parse_args()
    os.environ["BCOLLECTION_MODE"] = args.mode
    if args.database:
        os.environ["BCOLLECTION_DB_PATH"] = args.database
    from bc_runtime.settings import RuntimeSettings
    settings = RuntimeSettings.from_env()
    if args.command in {'import-demo-portfolio', 'sync-customer', 'sync-payments', 'sync-ews', 'publish-outcomes', 'create-demo-ptp', 'allocate-payment'} and settings.mode != 'demo-http':
        parser.error('ADP-02 import commands require demo-http')
    if args.command == "seed-demo" and settings.mode == "integration":
        parser.error("seed-demo is forbidden in integration")
    settings.validate_adapters()
    if args.command == "serve":
        import uvicorn
        uvicorn.run("main:app", host="127.0.0.1", port=args.port)
        return

    import database as db
    db.init_db()
    db.claim_runtime_database(settings.mode)
    if args.command in {'sync-payments', 'sync-ews', 'publish-outcomes', 'create-demo-ptp', 'allocate-payment'}:
        if args.command == 'sync-payments':
            from payment_ingestion import sync_payments
            result = sync_payments(args.case)
        elif args.command == 'sync-ews':
            from ews_ingestion import sync_ews
            result = sync_ews(args.cif)
        elif args.command == 'publish-outcomes':
            from integration_events import publish_outcomes
            result = publish_outcomes(args.case)
        else:
            from case_service import CaseService
            c = db.get_case_by_id(args.case)
            if not c or c['data_origin'] != 'SYNTHETIC':
                parser.error('Known synthetic case required')
            kind = 'record_ptp' if args.command == 'create-demo-ptp' else 'allocate_payment'
            payload = {'loan_id': args.loan, 'ptp_amount': args.amount, 'ptp_date': args.due} if kind == 'record_ptp' else {
                'event_id': args.event_id, 'ptp_id': args.ptp_id, 'reason': args.reason}
            result = CaseService().execute(args.case, args.command_id, c['case_version'], kind, payload)
        print(json.dumps(result))
        return
    if args.command == 'import-demo-portfolio':
        from portfolio_import import import_demo_portfolio
        print(json.dumps(import_demo_portfolio()))
        return
    if args.command == 'sync-customer':
        from customer_ingestion import synchronize
        print(json.dumps(synchronize(args.cif)))
        return
    if args.command == "seed-demo":
        as_of = datetime.fromisoformat(args.as_of)
        if as_of.tzinfo is not None:
            parser.error("Demo fixtures use a naive local --as-of timestamp")
        manifest = json.dumps({"version": 1, "seed": args.seed, "as_of": as_of.isoformat()}, sort_keys=True)
        with closing(db.get_connection()) as conn, conn:
            previous = conn.execute("SELECT value FROM runtime_metadata WHERE key='seed_manifest'").fetchone()
            if previous:
                if previous[0] != manifest:
                    parser.error("Existing seed differs; use a new database path (no overwrite)")
                print("Synthetic dataset already seeded; no data changed.")
                return
            if any(conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0] for table in ("cases", "case_interactions", "cbr_reference_cases")):
                parser.error("Refusing to seed a non-empty or partially seeded database; use a new path")
        from synthetic.generator import generate_synthetic_delinquent_cases
        from ml.experiments.holdout_assignment import HoldoutManager
        from src.guardrail.repositories.obligation_repo import InMemoryObligationRepository
        db.seed_cases_to_db(
            generate_synthetic_delinquent_cases(500, args.seed, as_of),
            HoldoutManager(), InMemoryObligationRepository(), as_of, args.seed,
        )
        with closing(db.get_connection()) as conn, conn:
            conn.execute("INSERT INTO runtime_metadata VALUES ('seed_manifest', ?)", (manifest,))
        print("SYNTHETIC ONLY: seeded 500 cases and 1000 reference cases.")
    else:
        print(f"Empty schema initialized for {settings.mode}; no seed data inserted.")


if __name__ == "__main__":
    main()
