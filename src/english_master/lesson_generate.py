"""Offline command-line entry point for M6 lesson generation."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from english_master.schema_validation import load_document
from english_master.lesson_generation import FileMockLessonBackend, LessonGenerationRequest, LessonGenerator


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Generate one constrained M6 lesson with an offline mock backend")
    parser.add_argument("--request", type=Path, required=True, help="Authored generation request JSON/YAML")
    parser.add_argument("--mock-response", type=Path, required=True, help="Authored offline backend response JSON")
    parser.add_argument("--output-dir", type=Path, required=True, help="New immutable directory for accepted output")
    parser.add_argument("--rejection", type=Path, help="Optional no-overwrite rejection record path")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        request = LessonGenerationRequest.from_dict(load_document(args.request))
        backend = FileMockLessonBackend(args.mock_response)
        result = LessonGenerator(backend).generate(request, output_directory=args.output_dir, rejection_path=args.rejection)
    except (OSError, ValueError, TypeError, json.JSONDecodeError) as error:
        print(f"lesson generation failed: {error}", file=sys.stderr)
        return 2
    if not result.accepted:
        for issue in result.audit["unresolved_issues"]:
            print(f"{issue['code']} {issue['path']}: {issue['message']}", file=sys.stderr)
        return 1
    print(f"accepted {result.lesson['id']} -> {args.output_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
