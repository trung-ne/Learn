"""Build and publish a verified M7 AI-reviewed development batch."""
from __future__ import annotations

import argparse
from pathlib import Path

from english_master.curriculum_review.loading import load_strict_document
from english_master.curriculum_review.storage import publish_bundle
from english_master.lesson_generation.canonical import canonical_json

from .exercise_generation.authority import VerifiedM6DevelopmentAuthority
from .exercise_generation.review import build_development_batch, validate_development_batch


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--exercise-root", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--created-at", required=True)
    parser.add_argument("--bundle-paths", type=Path, help="Strict JSON object mapping lesson IDs to safe paths under --exercise-root.")
    parser.add_argument("--git-commit")
    parser.add_argument("--structure", type=Path, default=Path("curriculum/structure.json"))
    parser.add_argument("--snapshot-dir", type=Path, default=Path("data/reviews/m5/development-20260903-062008"))
    parser.add_argument("--source-registry", type=Path, default=Path("sources/registry.yaml"))
    parser.add_argument("--m6-batch", type=Path, default=Path("data/generated/m6/development-batches/20260903-v6/development-batch.json"))
    parser.add_argument("--m6-root", type=Path, default=Path("data/generated/m6/development-candidates/20260903-v6-selected"))
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    try:
        authority = VerifiedM6DevelopmentAuthority.from_files(
            args.structure, args.snapshot_dir, args.source_registry, args.m6_batch, args.m6_root,
        )
        bundle_paths = None
        if args.bundle_paths is not None:
            selected = load_strict_document(args.bundle_paths)
            if not isinstance(selected, dict) or not all(isinstance(key, str) and isinstance(value, str) for key, value in selected.items()):
                raise ValueError("--bundle-paths must contain a JSON object of string lesson IDs and paths")
            from .exercise_generation.review import REQUIRED_DEVELOPMENT_LESSONS
            if set(selected) != set(REQUIRED_DEVELOPMENT_LESSONS):
                raise ValueError("--bundle-paths must select each required development lesson exactly once")
            bundle_paths = selected
        report = build_development_batch(
            authority, args.exercise_root, created_at=args.created_at, git_commit=args.git_commit, bundle_paths=bundle_paths,
        )
        issues = validate_development_batch(report, authority, args.exercise_root)
        if issues:
            for issue in issues:
                print(f"{issue.code} {issue.path}: {issue.message}")
            return 1
        if args.output_dir.exists() or args.output_dir.is_symlink():
            print(f"output already exists: {args.output_dir}")
            return 2
        publish_bundle(args.output_dir, {"development-batch.json": report})
        print(canonical_json({"batch_id": report["batch_id"], "path": str(args.output_dir / "development-batch.json")}))
        return 0
    except (OSError, ValueError, TypeError) as error:
        print(f"{type(error).__name__}: {error}")
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
