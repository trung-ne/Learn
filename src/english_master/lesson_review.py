"""Offline validation for M6 human and development AI review evidence."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from english_master.curriculum_review.loading import load_strict_document
from english_master.lesson_generation.authority import VerifiedM5Authority, VerifiedM5DevelopmentAuthority
from english_master.lesson_generation.review import (
    m7_eligibility_issues,
    validate_ai_lesson_review,
    validate_batch_report,
    validate_development_batch,
    validate_lesson_review,
)


def _root() -> Path:
    return Path(__file__).resolve().parents[2]


def _common(parser: argparse.ArgumentParser, *, development: bool = False) -> None:
    root = _root()
    parser.add_argument("--snapshot-dir", type=Path, required=True)
    if not development:
        parser.add_argument("--reviewer-registry", type=Path, required=True)
    parser.add_argument("--structure", type=Path, default=root / "curriculum" / "structure.json")
    parser.add_argument("--source-registry", type=Path, default=root / "sources" / "registry.yaml")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Validate M6 human or development AI review evidence")
    subcommands = parser.add_subparsers(dest="command", required=True)
    review = subcommands.add_parser("review", help="validate one human independent review")
    _common(review)
    review.add_argument("--review", type=Path, required=True)
    review.add_argument("--lesson", type=Path, required=True)
    review.add_argument("--audit", type=Path, required=True)
    batch = subcommands.add_parser("batch", help="validate a human-evidence batch QA report")
    _common(batch)
    batch.add_argument("--report", type=Path, required=True)
    batch.add_argument("--bundle-root", type=Path, required=True)
    ai_review = subcommands.add_parser("ai-review", help="validate one development AI review")
    _common(ai_review, development=True)
    ai_review.add_argument("--review", type=Path, required=True)
    ai_review.add_argument("--lesson", type=Path, required=True)
    ai_review.add_argument("--audit", type=Path, required=True)
    development_batch = subcommands.add_parser("development-batch", help="validate a development-approved M6 batch")
    _common(development_batch, development=True)
    development_batch.add_argument("--report", type=Path, required=True)
    development_batch.add_argument("--bundle-root", type=Path, required=True)
    m7_gate = subcommands.add_parser("m7-eligibility", help="read-only M7 eligibility check; does not start M7")
    _common(m7_gate, development=True)
    m7_gate.add_argument("--report", type=Path, required=True)
    m7_gate.add_argument("--bundle-root", type=Path, required=True)
    return parser


def _load_m5(args: argparse.Namespace):
    if args.command in {"ai-review", "development-batch", "m7-eligibility"}:
        return VerifiedM5DevelopmentAuthority.from_files(args.structure, args.snapshot_dir, args.source_registry)
    return VerifiedM5Authority.from_files(args.structure, args.snapshot_dir, args.source_registry, args.reviewer_registry)


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        m5 = _load_m5(args)
        if args.command == "review":
            issues = validate_lesson_review(load_strict_document(args.review), load_strict_document(args.lesson), load_strict_document(args.audit), m5)
        elif args.command == "batch":
            issues = validate_batch_report(load_strict_document(args.report), m5, args.bundle_root)
        elif args.command == "ai-review":
            issues = validate_ai_lesson_review(load_strict_document(args.review), load_strict_document(args.lesson), load_strict_document(args.audit), m5)
        elif args.command == "development-batch":
            issues = validate_development_batch(load_strict_document(args.report), m5, args.bundle_root)
        else:
            issues = m7_eligibility_issues(load_strict_document(args.report), m5, args.bundle_root)
    except Exception as error:
        print(f"M6 review validation setup failed: {type(error).__name__}: {error}", file=sys.stderr)
        return 2
    if issues:
        for issue in issues:
            print(f"{issue.code} {issue.path}: {issue.message}", file=sys.stderr)
        return 1
    print("M7 development eligibility passed" if args.command == "m7-eligibility" else "M6 development evidence validation passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
