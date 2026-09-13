"""CLI for deterministic cross-level A1-C2 QA."""
from __future__ import annotations

import argparse
from pathlib import Path

from .service import LEVEL_ORDER, build_request, run_qa, sample_flagged_regions, verify_report


def _request_arguments(parser: argparse.ArgumentParser) -> None:
    for level in LEVEL_ORDER:
        prefix = level.lower()
        parser.add_argument(f"--{prefix}-run-dir", required=True)
        parser.add_argument(f"--{prefix}-population", required=True)
        parser.add_argument(f"--{prefix}-blueprint", required=True)
        parser.add_argument(f"--{prefix}-allocation", required=True)
        parser.add_argument(f"--{prefix}-content-manifest", required=True)


def _levels_from_args(args: argparse.Namespace) -> list[dict[str, str]]:
    return [{
        "level": level,
        "run_dir": getattr(args, f"{level.lower()}_run_dir"),
        "population_path": getattr(args, f"{level.lower()}_population"),
        "blueprint_path": getattr(args, f"{level.lower()}_blueprint"),
        "allocation_path": getattr(args, f"{level.lower()}_allocation"),
        "content_manifest_path": getattr(args, f"{level.lower()}_content_manifest"),
    } for level in LEVEL_ORDER]


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Verify and inspect the six full A1-C2 development corpora without provider calls.")
    commands = parser.add_subparsers(dest="command", required=True)
    create = commands.add_parser("create-request", help="write a hash-bound six-level request")
    create.add_argument("--output", required=True, type=Path)
    _request_arguments(create)
    run = commands.add_parser("run", help="verify all six levels and write a report")
    run.add_argument("--request", required=True, type=Path)
    run.add_argument("--output", required=True, type=Path)
    sample = commands.add_parser("sample", help="write a deterministic flagged-region manifest; no API is invoked")
    sample.add_argument("--report", required=True, type=Path)
    sample.add_argument("--seed", required=True)
    sample.add_argument("--size", default=20, type=int)
    sample.add_argument("--output", required=True, type=Path)
    verify = commands.add_parser("verify", help="re-run source verification and validate report bindings")
    verify.add_argument("--request", required=True, type=Path)
    verify.add_argument("--report", required=True, type=Path)
    args = parser.parse_args(argv)
    if args.command == "create-request":
        print(f"Cross-level QA request: {build_request(_levels_from_args(args), args.output)['request_sha256']}")
    elif args.command == "run":
        print(f"Cross-level QA: {run_qa(request_path=args.request, output_path=args.output)['result']}")
    elif args.command == "verify":
        print(f"Cross-level QA verification: {verify_report(request_path=args.request, report_path=args.report)['result']}")
    else:
        result = sample_flagged_regions(report_path=args.report, seed=args.seed, sample_size=args.size, output_path=args.output)
        print(f"Cross-level flagged-region sample contains {len(result['selected_region_ids'])} regions")
    return 0
