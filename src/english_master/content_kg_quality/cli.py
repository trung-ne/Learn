"""CLI for the deterministic Content/KG quality system."""
from __future__ import annotations

import argparse
from pathlib import Path

from .service import LEVEL_ORDER, build_request, run_quality, verify_report


def _source_arguments(parser: argparse.ArgumentParser) -> None:
    for level in LEVEL_ORDER:
        prefix = level.lower()
        parser.add_argument(f"--{prefix}-run-dir", required=True)
        parser.add_argument(f"--{prefix}-population", required=True)
        parser.add_argument(f"--{prefix}-blueprint", required=True)
        parser.add_argument(f"--{prefix}-allocation", required=True)
        parser.add_argument(f"--{prefix}-content-manifest", required=True)


def _levels(arguments: argparse.Namespace) -> list[dict[str, str]]:
    return [{
        "level": level,
        "run_dir": getattr(arguments, f"{level.lower()}_run_dir"),
        "population_path": getattr(arguments, f"{level.lower()}_population"),
        "blueprint_path": getattr(arguments, f"{level.lower()}_blueprint"),
        "allocation_path": getattr(arguments, f"{level.lower()}_allocation"),
        "content_manifest_path": getattr(arguments, f"{level.lower()}_content_manifest"),
    } for level in LEVEL_ORDER]


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run deterministic Content/KG consistency checks without providers or network access.")
    commands = parser.add_subparsers(dest="command", required=True)
    create = commands.add_parser("create-request", help="write a no-overwrite hash-bound quality request")
    create.add_argument("--output", required=True, type=Path)
    create.add_argument("--web-lane", action="append", choices=("vocabulary", "dictionary"), default=[])
    _source_arguments(create)
    run = commands.add_parser("run", help="revalidate sources and write a quality report")
    run.add_argument("--request", required=True, type=Path)
    run.add_argument("--output", required=True, type=Path)
    verify = commands.add_parser("verify", help="rebuild source evidence and verify a report")
    verify.add_argument("--request", required=True, type=Path)
    verify.add_argument("--report", required=True, type=Path)
    arguments = parser.parse_args(argv)
    if arguments.command == "create-request":
        request = build_request(_levels(arguments), web_validation_scope=arguments.web_lane, output_path=arguments.output)
        print(f"Content/KG quality request: {request['request_sha256']}")
    elif arguments.command == "run":
        report = run_quality(request_path=arguments.request, output_path=arguments.output)
        print(f"Content/KG quality: {report['result']}")
    else:
        report = verify_report(request_path=arguments.request, report_path=arguments.report)
        print(f"Content/KG quality verification: {report['result']}")
    return 0
