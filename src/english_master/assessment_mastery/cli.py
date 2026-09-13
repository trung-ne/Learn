"""Offline CLI for assessment assembly, verification, and objective scoring."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from .learner_state import score_submission
from .service import LEVEL_ORDER, build_request, build_run, verify_run


def _request_arguments(parser: argparse.ArgumentParser) -> None:
    for level in LEVEL_ORDER:
        prefix = level.lower()
        parser.add_argument(f"--{prefix}-run-dir", required=True)
        parser.add_argument(f"--{prefix}-population", required=True)
        parser.add_argument(f"--{prefix}-blueprint", required=True)
        parser.add_argument(f"--{prefix}-allocation", required=True)
        parser.add_argument(f"--{prefix}-content-manifest", required=True)


def _levels(args: argparse.Namespace) -> list[dict[str, str]]:
    return [{
        "level": level,
        "run_dir": getattr(args, f"{level.lower()}_run_dir"),
        "population_path": getattr(args, f"{level.lower()}_population"),
        "blueprint_path": getattr(args, f"{level.lower()}_blueprint"),
        "allocation_path": getattr(args, f"{level.lower()}_allocation"),
        "content_manifest_path": getattr(args, f"{level.lower()}_content_manifest"),
    } for level in LEVEL_ORDER]


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Build and score deterministic local A1-C2 assessments without provider calls.")
    commands = parser.add_subparsers(dest="command", required=True)
    create = commands.add_parser("create-request", help="write a hash-bound six-run build request")
    create.add_argument("--output", required=True, type=Path)
    _request_arguments(create)
    build = commands.add_parser("build", help="verify sources and atomically publish an immutable run")
    build.add_argument("--request", required=True, type=Path)
    build.add_argument("--output-root", required=True, type=Path)
    verify = commands.add_parser("verify", help="reverify sources and reconstruct every package")
    verify.add_argument("--request", required=True, type=Path)
    verify.add_argument("--run-dir", required=True, type=Path)
    score = commands.add_parser("score", help="score a complete submission and atomically update local state")
    score.add_argument("--package", required=True, type=Path)
    score.add_argument("--submission", required=True, type=Path)
    score.add_argument("--state", required=True, type=Path)
    args = parser.parse_args(argv)
    if args.command == "create-request":
        result = build_request(_levels(args), args.output)
        print(f"Assessment build request: {result['request_sha256']}")
    elif args.command == "build":
        result = build_run(request_path=args.request, output_root=args.output_root)
        print(f"Assessment run: {result['run_id']} ({result['counts']['packages']} packages)")
    elif args.command == "verify":
        result = verify_run(request_path=args.request, run_dir=args.run_dir)
        print(f"Assessment verification: {result['result']} ({result['package_count']} packages)")
    else:
        result = score_submission(package_path=args.package, submission_path=args.submission, state_path=args.state)
        print(json.dumps(result, ensure_ascii=False, sort_keys=True, separators=(",", ":")))
    return 0
