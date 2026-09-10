"""M10 revision-cycle command-line interface."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Sequence

from .cli import main as intake_main
from .escalation_storage import verify_escalated_run
from .run_storage import verify_governance_run


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="M10 revision-cycle commands.")
    commands = parser.add_subparsers(dest="command", required=True)
    verify = commands.add_parser("verify-run", help="verify a closed M10 governance run directory")
    verify.add_argument("directory", type=Path)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    arguments = list(argv) if argv is not None else None
    if arguments is not None and arguments and arguments[0] in {"import-findings", "plan-findings", "execute-successor"}:
        return intake_main(arguments)
    if arguments is None:
        import sys

        if len(sys.argv) > 1 and sys.argv[1] in {"import-findings", "plan-findings", "execute-successor"}:
            return intake_main()
    args = _parser().parse_args(arguments)
    if args.command == "verify-run":
        verifier = verify_escalated_run if (args.directory / "escalation.json").is_file() else verify_governance_run
        print(json.dumps(verifier(args.directory), sort_keys=True, ensure_ascii=False))
        return 0
    raise AssertionError("unreachable")


if __name__ == "__main__":
    raise SystemExit(main())
