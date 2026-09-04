"""Run or independently verify the M8 QA Engine development gate."""
from __future__ import annotations

import argparse
from pathlib import Path
from typing import Any, Mapping

from english_master.curriculum_review.loading import load_strict_document
from english_master.lesson_generation.canonical import canonical_json

from .authority import VerifiedM7QaAuthority
from .backend import ReplayModelBackend
from .orchestrator import QaEngine
from .storage import publish_run
from .verification import verify_run


def _common(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--structure", type=Path, default=Path("curriculum/structure.json"))
    parser.add_argument(
        "--snapshot-dir",
        type=Path,
        default=Path("data/reviews/m5/development-20260903-062008"),
    )
    parser.add_argument("--source-registry", type=Path, default=Path("sources/registry.yaml"))
    parser.add_argument(
        "--m6-batch",
        type=Path,
        default=Path(
            "data/generated/m6/development-batches/20260903-v6/development-batch.json"
        ),
    )
    parser.add_argument(
        "--m6-root",
        type=Path,
        default=Path("data/generated/m6/development-candidates/20260903-v6-selected"),
    )
    parser.add_argument("--exercise-root", type=Path, default=Path("curriculum/exercises"))
    parser.add_argument(
        "--m7-batch",
        type=Path,
        default=Path(
            "curriculum/exercises/development-batches/20260903-v3/development-batch.json"
        ),
    )


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)

    run = commands.add_parser("run", help="run ordered M8 QA and publish one terminal bundle")
    _common(run)
    run.add_argument("--lesson-id", required=True)
    run.add_argument("--created-at", required=True)
    run.add_argument("--maximum-attempts", type=int, default=3)
    run.add_argument(
        "--regeneration-captures",
        "--candidate-captures",
        dest="regeneration_captures",
        type=Path,
        help="retained regeneration responses; replay evidence cannot promote a retry",
    )
    run.add_argument(
        "--review-captures",
        type=Path,
        help="retained semantic-review responses; replay evidence cannot promote a run",
    )
    run.add_argument("--output-dir", type=Path, required=True)

    verify = commands.add_parser(
        "verify", help="independently verify an approved, rejected, or operational run"
    )
    _common(verify)
    verify.add_argument("--run-dir", type=Path, required=True)
    return parser


def _authority(args: argparse.Namespace) -> VerifiedM7QaAuthority:
    return VerifiedM7QaAuthority.from_files(
        structure_path=args.structure,
        snapshot_directory=args.snapshot_dir,
        source_registry_path=args.source_registry,
        m6_batch_path=args.m6_batch,
        m6_root=args.m6_root,
        exercise_root=args.exercise_root,
        m7_batch_path=args.m7_batch,
    )


def _captures(path: Path | None) -> list[Mapping[str, Any]] | None:
    if path is None:
        return None
    document = load_strict_document(path)
    captures = document.get("captures") if isinstance(document, Mapping) else None
    if not isinstance(captures, list) or any(
        not isinstance(item, Mapping) for item in captures
    ):
        raise ValueError("capture file must contain an object with a captures array of objects")
    return captures


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    try:
        authority = _authority(args)
        if args.command == "verify":
            result = verify_run(args.run_dir, authority)
            print(canonical_json(result))
            return 0

        regeneration_captures = _captures(args.regeneration_captures)
        review_captures = _captures(args.review_captures)
        request = authority.request(
            args.lesson_id,
            created_at=args.created_at,
            maximum_attempts=args.maximum_attempts,
        )
        result = QaEngine(
            authority,
            request,
            (
                ReplayModelBackend(regeneration_captures)
                if regeneration_captures is not None
                else None
            ),
            ReplayModelBackend(review_captures) if review_captures is not None else None,
        ).run()
        publish_run(
            args.output_dir,
            authority=authority,
            request=request,
            attempts=result.attempts,
            receipts=result.receipts,
            rejections=result.rejections,
            decision=result.decision,
            invocations=result.invocations,
            ai_reviews=result.ai_reviews,
            operational_failures=result.operational_failures,
        )
        terminal_state = (
            "DEVELOPMENT_APPROVED"
            if result.approved
            else "OPERATIONAL_FAILURE"
            if result.operational_failures
            else "REJECTED"
        )
        print(
            canonical_json(
                {
                    "engine_run_id": request["engine_run_id"],
                    "terminal_state": terminal_state,
                    "content_lifecycle_status": "UNREVIEWED",
                    "output": str(args.output_dir),
                }
            )
        )
        return 0 if result.approved else 2 if result.operational_failures else 1
    except (KeyError, OSError, TypeError, ValueError) as error:
        print(f"{type(error).__name__}: {error}")
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
