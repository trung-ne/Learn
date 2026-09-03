"""Offline validator for hash-bound M6 human reviews and batch QA reports."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from english_master.curriculum_review.loading import load_strict_document
from english_master.lesson_generation.authority import VerifiedM5Authority
from english_master.lesson_generation.review import validate_batch_report, validate_lesson_review


def _root() -> Path:
    return Path(__file__).resolve().parents[2]


def _common(parser: argparse.ArgumentParser) -> None:
    root = _root()
    parser.add_argument("--snapshot-dir", type=Path, required=True)
    parser.add_argument("--reviewer-registry", type=Path, required=True)
    parser.add_argument("--structure", type=Path, default=root / "curriculum" / "structure.json")
    parser.add_argument("--source-registry", type=Path, default=root / "sources" / "registry.yaml")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Validate independent M6 lesson-review evidence")
    subcommands = parser.add_subparsers(dest="command", required=True)
    review = subcommands.add_parser("review", help="validate one independent review against lesson and audit")
    _common(review)
    review.add_argument("--review", type=Path, required=True)
    review.add_argument("--lesson", type=Path, required=True)
    review.add_argument("--audit", type=Path, required=True)
    batch = subcommands.add_parser("batch", help="validate a ten-lesson batch QA report")
    _common(batch)
    batch.add_argument("--report", type=Path, required=True)
    batch.add_argument("--bundle-root", type=Path, required=True)
    return parser


def _load_m5(args: argparse.Namespace) -> VerifiedM5Authority:
    return VerifiedM5Authority.from_files(args.structure, args.snapshot_dir, args.source_registry, args.reviewer_registry)


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        m5 = _load_m5(args)
        if args.command == "review":
            issues = validate_lesson_review(load_strict_document(args.review), load_strict_document(args.lesson), load_strict_document(args.audit), m5)
        else:
            issues = validate_batch_report(load_strict_document(args.report), m5, args.bundle_root)
    except Exception as error:
        print(f"M6 review validation setup failed: {type(error).__name__}: {error}", file=sys.stderr)
        return 2
    if issues:
        for issue in issues:
            print(f"{issue.code} {issue.path}: {issue.message}", file=sys.stderr)
        return 1
    print("M6 review evidence validation passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
