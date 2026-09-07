"""CLI for the explicitly authorized, offline post-M3 Tatoeba pilot."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from english_master.ingest import _timestamp
from english_master.schema_validation import repository_root

from .service import PilotError, prepare, run, verify


def _path(value: str) -> Path:
    path = Path(value)
    if "://" in value:
        raise argparse.ArgumentTypeError("URLs are not accepted; acquisition is outside this CLI")
    return path


def _common(parser: argparse.ArgumentParser, *, require_output: bool = False) -> None:
    root = repository_root()
    parser.add_argument("--authorization", required=True, type=_path)
    parser.add_argument("--receipt", required=True, type=_path)
    parser.add_argument("--registry", type=_path, default=root / "sources" / "registry.yaml")
    parser.add_argument("--data-root", type=_path, default=root / "data")
    if require_output:
        parser.add_argument("--output-directory", required=True, type=_path)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Offline, authorized Tatoeba real-record pilot; never crawls or requests URLs.")
    commands = parser.add_subparsers(dest="command", required=True)
    prepare_parser = commands.add_parser("prepare")
    _common(prepare_parser, require_output=True)
    prepare_parser.add_argument("--payload", required=True, type=_path)
    run_parser = commands.add_parser("run")
    _common(run_parser)
    run_parser.add_argument("--preparation-report", required=True, type=_path)
    run_parser.add_argument("--prepared-tsv", required=True, type=_path)
    run_parser.add_argument("--retrieved-at", required=True, type=_timestamp)
    run_parser.add_argument("--processed-at", required=True, type=_timestamp)
    verify_parser = commands.add_parser("verify")
    _common(verify_parser)
    verify_parser.add_argument("--preparation-report", required=True, type=_path)
    verify_parser.add_argument("--prepared-tsv", required=True, type=_path)
    return parser


def main(argv: list[str] | None = None) -> int:
    arguments = build_parser().parse_args(argv)
    try:
        if arguments.command == "prepare":
            result = prepare(authorization_path=arguments.authorization, receipt_path=arguments.receipt, payload_path=arguments.payload, registry_path=arguments.registry, output_directory=arguments.output_directory, data_root=arguments.data_root)
        elif arguments.command == "run":
            result = run(authorization_path=arguments.authorization, receipt_path=arguments.receipt, preparation_report_path=arguments.preparation_report, prepared_tsv_path=arguments.prepared_tsv, registry_path=arguments.registry, data_root=arguments.data_root, retrieved_at=arguments.retrieved_at, processed_at=arguments.processed_at)
        else:
            result = verify(authorization_path=arguments.authorization, receipt_path=arguments.receipt, preparation_report_path=arguments.preparation_report, prepared_tsv_path=arguments.prepared_tsv, registry_path=arguments.registry)
    except (OSError, PilotError, ValueError) as error:
        print(f"PILOT FAILED: {error}", file=sys.stderr)
        return 1
    print(json.dumps(result, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
