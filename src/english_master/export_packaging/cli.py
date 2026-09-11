"""Command-line interface for authority-first M11 export packaging."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Sequence

from .authority import ExportEligibilityError, assess_authorization
from .batch import BatchEligibilityError, build_batch_export, verify_batch_export
from .storage import build_export
from .verification import ExportVerificationError, verify_export


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Build and independently verify English Master M11 export packages offline.")
    commands = parser.add_subparsers(dest="command", required=True)
    inspect = commands.add_parser("inspect-authority", help="check AI development authority without creating output")
    inspect.add_argument("--authorization", required=True, type=Path)
    inspect.add_argument("--repository-root", required=True, type=Path)
    build = commands.add_parser("build", help="build all required formats from eligible AI development authority")
    build.add_argument("--authorization", required=True, type=Path)
    build.add_argument("--repository-root", required=True, type=Path)
    build.add_argument("--output-root", required=True, type=Path)
    build.add_argument("--exported-at", required=True, help="explicit ISO-8601 export timestamp")
    verify = commands.add_parser("verify", help="read-only verification of an immutable export directory")
    verify.add_argument("directory", type=Path)
    verify.add_argument("--repository-root", required=True, type=Path)
    batch = commands.add_parser("build-batch", help="build a direct local batch; JSON, CSV, web, and mobile are always included")
    batch.add_argument("--batch-input", required=True, type=Path)
    batch.add_argument("--repository-root", required=True, type=Path)
    batch.add_argument("--output-root", required=True, type=Path)
    batch.add_argument("--exported-at", required=True, help="explicit ISO-8601 export timestamp")
    batch.add_argument("--include-print", action="store_true", help="also emit learner and instructor print HTML")
    batch.add_argument("--include-ims", action="store_true", help="also emit an IMS Common Cartridge archive")
    verify_batch = commands.add_parser("verify-batch", help="read-only verification of an immutable direct local-batch export")
    verify_batch.add_argument("directory", type=Path)
    verify_batch.add_argument("--repository-root", required=True, type=Path)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    try:
        if args.command == "inspect-authority":
            eligible = assess_authorization(args.authorization, args.repository_root)
            result = {"eligible": True, "authorization_id": eligible.authorization["authorization_id"], "artifact_count": len(eligible.artifacts), "approval_tier": "DEVELOPMENT_APPROVED"}
        elif args.command == "build":
            directory = build_export(args.authorization, args.repository_root, args.output_root, exported_at=args.exported_at)
            result = {"result": "BUILT", "directory": str(directory), "export_id": directory.name}
        elif args.command == "verify":
            receipt = verify_export(args.directory, args.repository_root)
            result = {"result": "VERIFIED", "export_id": receipt["export_id"], "verification_id": receipt["verification_id"]}
        elif args.command == "build-batch":
            directory = build_batch_export(
                args.batch_input,
                args.repository_root,
                args.output_root,
                exported_at=args.exported_at,
                include_print=args.include_print,
                include_ims=args.include_ims,
            )
            result = {"result": "BUILT", "directory": str(directory), "export_id": directory.name, "mode": "LOCAL_BATCH"}
        elif args.command == "verify-batch":
            receipt = verify_batch_export(args.directory, args.repository_root)
            result = {"result": "VERIFIED", "export_id": receipt["export_id"], "verification_id": receipt["verification_id"], "mode": "LOCAL_BATCH"}
        else:  # pragma: no cover
            raise AssertionError("unreachable")
    except (BatchEligibilityError, ExportEligibilityError, ExportVerificationError, OSError, ValueError, KeyError) as error:
        verifying = args.command in {"verify", "verify-batch"}
        print(json.dumps({"result": "INVALID" if verifying else "INELIGIBLE", "error": str(error)}, ensure_ascii=False, sort_keys=True), file=sys.stderr)
        return 2
    print(json.dumps(result, ensure_ascii=False, sort_keys=True))
    return 0
