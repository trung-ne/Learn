"""Offline command-line entry point for M6 lesson generation."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from english_master.lesson_generation import (
    FileMockLessonBackend,
    LessonGenerationAuthority,
    LessonGenerationRequest,
    LessonGenerator,
)
from english_master.schema_validation import load_document


def repository_root() -> Path:
    return Path(__file__).resolve().parents[2]


def build_parser() -> argparse.ArgumentParser:
    root = repository_root()
    parser = argparse.ArgumentParser(description="Generate one constrained M6 lesson with independently loaded authority")
    parser.add_argument("--request", type=Path, required=True, help="Authored generation request JSON/YAML")
    parser.add_argument("--authorization", type=Path, required=True, help="Independent M6 authorization JSON/YAML")
    parser.add_argument("--structure", type=Path, default=root / "curriculum" / "structure.json", help="Authoritative M5 structure")
    parser.add_argument("--graph", type=Path, help="M5 graph override declared by the structure")
    parser.add_argument("--coverage", type=Path, help="M5 coverage override declared by the structure")
    parser.add_argument("--taxonomy", type=Path, help="M5 taxonomy override declared by the structure")
    parser.add_argument("--source-registry", type=Path, default=root / "sources" / "registry.yaml", help="Authoritative source registry")
    parser.add_argument("--mock-response", type=Path, required=True, help="Authored offline backend content response JSON")
    parser.add_argument("--output-dir", type=Path, required=True, help="New immutable directory for accepted output")
    parser.add_argument("--rejection-dir", type=Path, help="Optional immutable directory for rejection and audit records")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        request_document = load_document(args.request)
        if not isinstance(request_document, dict):
            raise TypeError("generation request must be an object")
        authority = LessonGenerationAuthority.from_files(
            args.structure,
            args.authorization,
            args.source_registry,
            graph_path=args.graph,
            coverage_path=args.coverage,
            taxonomy_path=args.taxonomy,
        )
        request = LessonGenerationRequest.from_dict(request_document)
        backend = FileMockLessonBackend(args.mock_response)
        result = LessonGenerator(backend, authority).generate(
            request,
            output_directory=args.output_dir,
            rejection_directory=args.rejection_dir,
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
