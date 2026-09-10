"""CLI for deterministic offline fixture transcription."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from .models import TranscriptionError
from .service import run, verify


def _local_path(value: str) -> Path:
    if "://" in value:
        raise argparse.ArgumentTypeError("URLs are prohibited; provide a local path")
    return Path(value)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Offline deterministic fixture-only transcription")
    commands = parser.add_subparsers(dest="command", required=True)
    execute = commands.add_parser("run", help="create one immutable fixture transcript run")
    execute.add_argument("--authorization", required=True, type=_local_path)
    execute.add_argument("--request", required=True, type=_local_path)
    execute.add_argument("--media-run-directory", required=True, type=_local_path)
    execute.add_argument("--registry", required=True, type=_local_path)
    execute.add_argument("--data-root", required=True, type=_local_path)
    execute.add_argument("--started-at", required=True)
    execute.add_argument("--completed-at", required=True)
    checked = commands.add_parser("verify", help="read-only verify an immutable transcript run")
    checked.add_argument("--run-directory", required=True, type=_local_path)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        if args.command == "run":
            result = {"run_directory": str(run(authorization_path=args.authorization, request_path=args.request, media_run_directory=args.media_run_directory, registry_path=args.registry, data_root=args.data_root, started_at=args.started_at, completed_at=args.completed_at))}
        else:
            result = verify(run_directory=args.run_directory)
    except (TranscriptionError, OSError, ValueError) as error:
        print(f"transcription failed: {error}")
        return 1
    print(json.dumps(result, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
