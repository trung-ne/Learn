"""Offline CLI for constrained M7 exercise generation."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from english_master.curriculum_review.loading import load_strict_document

from .exercise_generation.authority import VerifiedM6DevelopmentAuthority
from .exercise_generation.backend import CapturedResponseExerciseBackend
from .exercise_generation.builders import ExerciseGenerationConfig, build_authorization, build_request
from .exercise_generation.generator import ExerciseGenerator


def parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Generate an immutable M7 exercise set from verified M6 development evidence.")
    parser.add_argument("--lesson-id", required=True)
    parser.add_argument("--captured-response", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--rejection-dir", type=Path)
    parser.add_argument("--revision", type=int, default=1, choices=range(1, 100))
    parser.add_argument("--structure", type=Path, default=Path("curriculum/structure.json"))
    parser.add_argument("--source-registry", type=Path, default=Path("sources/registry.yaml"))
    parser.add_argument("--snapshot-dir", type=Path, default=Path("data/reviews/m5/development-20260903-062008"))
    parser.add_argument("--m6-batch", type=Path, default=Path("data/generated/m6/development-batches/20260903-v6/development-batch.json"))
    parser.add_argument("--m6-root", type=Path, default=Path("data/generated/m6/development-candidates/20260903-v6-selected"))
    return parser


def main(argv: list[str] | None = None) -> int:
    args = parser().parse_args(argv)
    try:
        authority = VerifiedM6DevelopmentAuthority.from_files(
            args.structure, args.snapshot_dir, args.source_registry, args.m6_batch, args.m6_root,
        )
        authorization = build_authorization(authority)
        request = build_request(authority, authorization, args.lesson_id, ExerciseGenerationConfig(revision=args.revision))
        backend = CapturedResponseExerciseBackend(load_strict_document(args.captured_response))
        result = ExerciseGenerator(backend, authority).generate(
            request, output_directory=args.output_dir, rejection_directory=args.rejection_dir,
        )
    except (OSError, ValueError, KeyError, TypeError) as error:
        print(f"SETUP_FAILURE: {error}", file=sys.stderr)
        return 2
    if result.accepted:
        print(json.dumps({"exercise_set_id": result.exercise_set["exercise_set_id"], "paths": [str(path) for path in result.paths]}, sort_keys=True))
        return 0
    for issue in result.audit["qa_issues_found"]:
        print(f"{issue['code']} {issue['path']}: {issue['message']}", file=sys.stderr)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
