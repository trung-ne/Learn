"""Command-line interface for authority-first M11 export packaging."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Sequence

from .authority import ExportEligibilityError, assess_authorization
from .storage import build_export
from .verification import ExportVerificationError, verify_export


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Build and independently verify English Master M11 export packages offline.")
    commands = parser.add_subparsers(dest="command", required=True)
    inspect = commands.add_parser("inspect-authority", help="check release authority without creating output")
    inspect.add_argument("--authorization", required=True, type=Path)
    inspect.add_argument("--repository-root", required=True, type=Path)
    build = commands.add_parser("build", help="build all required formats from eligible release authority")
    build.add_argument("--authorization", required=True, type=Path)
    build.add_argument("--repository-root", required=True, type=Path)
    build.add_argument("--output-root", required=True, type=Path)
    build.add_argument("--exported-at", required=True, help="explicit ISO-8601 export timestamp")
    verify = commands.add_parser("verify", help="read-only verification of an immutable export directory")
    verify.add_argument("directory", type=Path)
    verify.add_argument("--repository-root", required=True, type=Path)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    try:
        if args.command == "inspect-authority":
            eligible = assess_authorization(args.authorization, args.repository_root)
            result = {"eligible": True, "authorization_id": eligible.authorization["authorization_id"], "artifact_count": len(eligible.artifacts), "release_approved": True}
        elif args.command == "build":
            directory = build_export(args.authorization, args.repository_root, args.output_root, exported_at=args.exported_at)
            result = {"result": "BUILT", "directory": str(directory), "export_id": directory.name}
        elif args.command == "verify":
            receipt = verify_export(args.directory, args.repository_root)
            result = {"result": "VERIFIED", "export_id": receipt["export_id"], "verification_id": receipt["verification_id"]}
        else:  # pragma: no cover
            raise AssertionError("unreachable")
    except (ExportEligibilityError, ExportVerificationError, OSError, ValueError, KeyError) as error:
        print(json.dumps({"result": "INELIGIBLE" if args.command != "verify" else "INVALID", "error": str(error)}, ensure_ascii=False, sort_keys=True), file=sys.stderr)
        return 2
    print(json.dumps(result, ensure_ascii=False, sort_keys=True))
    return 0
