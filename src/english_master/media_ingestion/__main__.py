"""CLI for the offline fixture-only M12 media framework."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from .service import MediaIngestionError, prepare, run, verify


def _local_path(value: str) -> Path:
    if "://" in value:
        raise argparse.ArgumentTypeError("URLs are prohibited; provide a local path")
    return Path(value)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Offline fixture-only controlled media ingestion")
    subparsers = parser.add_subparsers(dest="command", required=True)
    prepared = subparsers.add_parser("prepare", help="validate a local fixture and create an acquisition receipt")
    prepared.add_argument("--authorization", required=True, type=_local_path)
    prepared.add_argument("--payload", required=True, type=_local_path)
    prepared.add_argument("--registry", required=True, type=_local_path)
    prepared.add_argument("--receipt", required=True, type=_local_path)
    prepared.add_argument("--acquired-at", required=True)
    execute = subparsers.add_parser("run", help="atomically import a prepared fixture")
    execute.add_argument("--authorization", required=True, type=_local_path)
    execute.add_argument("--receipt", required=True, type=_local_path)
    execute.add_argument("--payload", required=True, type=_local_path)
    execute.add_argument("--registry", required=True, type=_local_path)
    execute.add_argument("--data-root", required=True, type=_local_path)
    execute.add_argument("--completed-at", required=True)
    checked = subparsers.add_parser("verify", help="read-only verify an immutable media run")
    checked.add_argument("--run-directory", required=True, type=_local_path)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        if args.command == "prepare":
            result = prepare(authorization_path=args.authorization, payload_path=args.payload, registry_path=args.registry, receipt_path=args.receipt, acquired_at=args.acquired_at)
        elif args.command == "run":
            result = {"run_directory": str(run(authorization_path=args.authorization, receipt_path=args.receipt, payload_path=args.payload, registry_path=args.registry, data_root=args.data_root, completed_at=args.completed_at))}
        else:
            result = verify(run_directory=args.run_directory)
    except (MediaIngestionError, OSError, ValueError) as error:
        print(f"media ingestion failed: {error}")
        return 1
    print(json.dumps(result, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
