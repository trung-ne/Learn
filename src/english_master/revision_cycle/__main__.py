"""Read-only M10 verification command-line interface."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Sequence

from .escalation_storage import verify_escalated_run
from .run_storage import verify_governance_run


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Verify immutable English Master M10 governance evidence offline.")
    commands = parser.add_subparsers(dest="command", required=True)
    verify = commands.add_parser("verify-run", help="verify a closed M10 governance run directory")
    verify.add_argument("directory", type=Path)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    if args.command == "verify-run":
        verifier = verify_escalated_run if (args.directory / "escalation.json").is_file() else verify_governance_run
        print(json.dumps(verifier(args.directory), sort_keys=True, ensure_ascii=False))
        return 0
    raise AssertionError("unreachable")


if __name__ == "__main__":
    raise SystemExit(main())
