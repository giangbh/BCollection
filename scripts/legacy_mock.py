"""Local-only synthetic legacy service; admin operations are CLI-only."""
import argparse
from datetime import datetime, timezone
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / "bcollection-platform/services/legacy-mock-api"), str(ROOT / "bcollection-data")]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--database", required=True)
    commands = parser.add_subparsers(dest="command", required=True)
    seed_parser = commands.add_parser("seed")
    seed_parser.add_argument("--seed", type=int, default=42)
    seed_parser.add_argument("--as-of", default="2026-09-01T09:00:00")
    commands.add_parser("observe", help="Explicitly refresh source observations without changing money")
    commands.add_parser('seed-360', help='Explicit CRM/Core history/LOS/directory scenario expansion')
    pay = commands.add_parser('post-payment')
    pay.add_argument('--loan', required=True)
    pay.add_argument('--event-id', required=True)
    pay.add_argument('--amount', type=int, required=True)
    pay.add_argument('--at')
    reverse = commands.add_parser('reverse-payment')
    reverse.add_argument('--loan', required=True)
    reverse.add_argument('--event-id', required=True)
    reverse.add_argument('--reverses', required=True)
    reverse.add_argument('--at')
    seal = commands.add_parser('seal-payments', help='Certify completeness; later inserts before this watermark are forbidden')
    seal.add_argument('--loan', required=True)
    seal.add_argument('--through')
    ews = commands.add_parser('emit-ews')
    ews.add_argument('--cif', required=True)
    ews.add_argument('--loan', action='append', required=True)
    ews.add_argument('--signal-id', required=True)
    ews.add_argument('--event-id', required=True)
    ews.add_argument('--title', default='Tín hiệu EWS mô phỏng')
    ews.add_argument('--version', type=int, default=1)
    ews.add_argument('--severity', choices=['HIGH','MEDIUM','LOW'], default='HIGH')
    ews.add_argument('--verification', choices=['VERIFIED','UNVERIFIED','DISMISSED'], default='VERIFIED')
    serve = commands.add_parser("serve")
    serve.add_argument("--port", type=int, default=8099)
    args = parser.parse_args()
    from legacy_mock import create_app, seed, advance_snapshot
    if args.command in {'post-payment', 'reverse-payment', 'seal-payments', 'emit-ews'}:
        import json
        from event_mock import payment, seal, signal
        if args.command == 'post-payment':
            result = payment(args.database, args.loan, args.event_id, args.amount, occurred_at=args.at)
        elif args.command == 'reverse-payment':
            result = payment(args.database, args.loan, args.event_id, reverses=args.reverses, occurred_at=args.at)
        elif args.command == 'seal-payments':
            result = seal(args.database, args.loan, args.through)
        else:
            result = signal(args.database, args.cif, args.loan, args.signal_id, args.event_id,
                            args.version, args.severity, args.verification, title=args.title)
        print(json.dumps(result))
    elif args.command == "seed":
        from synthetic.generator import generate_synthetic_delinquent_cases
        fixture_time = datetime.fromisoformat(args.as_of)
        if fixture_time.tzinfo is not None:
            parser.error("Fixture --as-of must match bcollection seed-demo's naive timestamp")
        seed(args.database, generate_synthetic_delinquent_cases(500, args.seed, fixture_time),
             {"version": 1, "seed": args.seed, "as_of": args.as_of, "count": 500}, datetime.now(timezone.utc).isoformat())
        print("Synthetic Core scenario seeded (or unchanged); no B.Collection database accessed.")
    elif args.command == 'seed-360':
        from customer_fixtures import seed_customer360
        seed_customer360(args.database)
        print('Synthetic Customer 360 sources seeded; no Collection DB accessed.')
    elif args.command == "observe":
        advance_snapshot(args.database, datetime.now(timezone.utc).isoformat())
        print("Synthetic source observations advanced explicitly.")
    else:
        import uvicorn
        uvicorn.run(create_app(args.database), host="127.0.0.1", port=args.port)


if __name__ == "__main__":
    main()
