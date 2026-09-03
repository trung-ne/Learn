"""Offline command-line entry point for snapshot-bound M6 lesson generation."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from english_master.lesson_generation import (
    CapturedResponseLessonBackend,
    LessonGenerationAuthority,
    LessonGenerationRequest,
    LessonGenerator,
    VerifiedM5Authority,
    VerifiedM5DevelopmentAuthority,
    build_authorization,
    build_request,
)


def repository_root() -> Path:
    return Path(__file__).resolve().parents[2]


def build_parser() -> argparse.ArgumentParser:
    root = repository_root()
    parser = argparse.ArgumentParser(description="Generate one constrained M6 lesson from a reverified M5 approval snapshot")
    parser.add_argument("--lesson-id", required=True, help="Authoritative M5 lesson ID to generate")
    parser.add_argument("--snapshot-dir", type=Path, required=True, help="Immutable verified M5 snapshot directory")
    parser.add_argument("--reviewer-registry", type=Path, help="Required only for strict human/release snapshots")
    parser.add_argument("--development", action="store_true", help="Require an M5 development-only snapshot; never creates release approval")
    parser.add_argument("--structure", type=Path, default=root / "curriculum" / "structure.json", help="Authoritative M5 structure")
    parser.add_argument("--graph", type=Path, help="M5 graph override declared by the structure")
    parser.add_argument("--coverage", type=Path, help="M5 coverage override declared by the structure")
    parser.add_argument("--taxonomy", type=Path, help="M5 taxonomy override declared by the structure")
    parser.add_argument("--source-registry", type=Path, default=root / "sources" / "registry.yaml", help="Independently loaded authoritative source registry")
    parser.add_argument("--captured-response", type=Path, required=True, help="Prompt-hash-bound provider response capture JSON")
    parser.add_argument("--output-dir", type=Path, required=True, help="New immutable directory for accepted output")
    parser.add_argument("--rejection-dir", type=Path, help="Optional immutable directory for rejection and audit records")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        if args.development:
            m5 = VerifiedM5DevelopmentAuthority.from_files(
                args.structure, args.snapshot_dir, args.source_registry,
                graph_path=args.graph, coverage_path=args.coverage, taxonomy_path=args.taxonomy,
            )
        else:
            if args.reviewer_registry is None:
                raise ValueError("--reviewer-registry is required unless --development is selected")
            m5 = VerifiedM5Authority.from_files(
                args.structure, args.snapshot_dir, args.source_registry, args.reviewer_registry,
                graph_path=args.graph, coverage_path=args.coverage, taxonomy_path=args.taxonomy,
            )
        authorization = build_authorization(m5, [args.lesson_id])
        authority = LessonGenerationAuthority(m5=m5, authorization=authorization)
        request = LessonGenerationRequest.from_dict(build_request(m5, authorization, args.lesson_id))
        backend = CapturedResponseLessonBackend.from_file(args.captured_response)
        result = LessonGenerator(backend, authority).generate(
            request, output_directory=args.output_dir, rejection_directory=args.rejection_dir,
        )
    except Exception as error:
        print(f"lesson generation setup failed: {type(error).__name__}: {error}", file=sys.stderr)
        return 2
    if not result.accepted:
        for issue in result.audit["unresolved_issues"]:
            print(f"{issue['code']} {issue['path']}: {issue['message']}", file=sys.stderr)
        persistence_failed = any(issue["code"] in {"PUBLICATION_FAILURE", "REJECTION_PERSISTENCE_FAILURE"} for issue in result.audit["unresolved_issues"])
        return 2 if persistence_failed else 1
    print(f"accepted {result.lesson['id']} -> {args.output_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
