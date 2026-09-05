"""Build or independently verify the M8.2 AI-practice pilot."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import yaml

from .authority import VerifiedM6PracticeAuthority
from .generation import build_pilot
from .verification import verify_pilot


def _common(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--structure", type=Path, default=Path("curriculum/structure.json"))
    parser.add_argument("--snapshot-dir", type=Path, default=Path("data/reviews/m5/development-20260903-062008"))
    parser.add_argument("--source-registry", type=Path, default=Path("sources/registry.yaml"))
    parser.add_argument("--m6-batch", type=Path, default=Path("data/generated/m6/development-batches/20260903-v6/development-batch.json"))
    parser.add_argument("--m6-root", type=Path, default=Path("data/generated/m6/development-candidates/20260903-v6-selected"))


def _emit(value: object) -> None:
    """Emit ASCII-only CLI JSON after an irreversible immutable publication."""
    print(json.dumps(value, ensure_ascii=True, sort_keys=True, separators=(",", ":"), allow_nan=False))


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    build = commands.add_parser("build-pilot", help="build the complete immutable 10-by-4 pilot")
    _common(build)
    build.add_argument("--output-dir", type=Path, required=True)
    build.add_argument("--created-at", help="actual RFC 3339 build time; defaults to the current UTC time")
    build.add_argument("--prompt-version", default="M8_2_AI_PRACTICE_v9")
    verify = commands.add_parser("verify-pilot", help="independently verify an immutable pilot")
    _common(verify)
    verify.add_argument("--pilot-dir", type=Path, required=True)
    return parser


def _authority(args: argparse.Namespace) -> VerifiedM6PracticeAuthority:
    return VerifiedM6PracticeAuthority.from_files(
        structure_path=args.structure, snapshot_directory=args.snapshot_dir,
        source_registry_path=args.source_registry, m6_batch_path=args.m6_batch, m6_root=args.m6_root,
    )


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    try:
        authority = _authority(args)
        if args.command == "build-pilot":
            path = build_pilot(authority, args.output_dir, created_at=args.created_at, prompt_version=args.prompt_version)
            _emit({"output": str(path), **verify_pilot(path, authority)})
            return 0
        _emit(verify_pilot(args.pilot_dir, authority))
        return 0
    except (KeyError, OSError, TypeError, ValueError, yaml.YAMLError) as error:
        print(f"{type(error).__name__}: {error}".encode("ascii", "backslashreplace").decode("ascii"))
        return 2
