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
    parser.add_argument("--mode", choices=["demo", "test", "integration"], default=os.getenv("BCOLLECTION_MODE", "demo"))
    parser.add_argument("--database", help="Separate SQLite path for this profile")
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser("init-db", help="Create empty schema only")
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
