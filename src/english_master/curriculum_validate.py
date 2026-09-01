"""Offline CLI for validating the M5 curriculum architecture."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import yaml

from english_master.curriculum_validation import load_bundle, validate_bundle
from english_master.schema_validation import SchemaValidationError, validate_instance


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Validate English Master M5 curriculum artifacts offline.")
    parser.add_argument("structure", type=Path, help="Path to curriculum/structure.json")
    parser.add_argument("--graph", type=Path, help="Override the graph path declared by the structure")
    parser.add_argument("--coverage", type=Path, help="Override the coverage path declared by the structure")
    parser.add_argument("--taxonomy", type=Path, help="Override the taxonomy path declared by the structure")
    parser.add_argument("--report", type=Path, help="Write a deterministic JSON validation report")
    parser.add_argument(
        "--require-approved-taxonomy",
        action="store_true",
        help="Reject planning references unless every taxonomy record is APPROVED",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    arguments = build_parser().parse_args(argv)
    try:
        bundle = load_bundle(
            arguments.structure,
            graph_path=arguments.graph,
            coverage_path=arguments.coverage,
            taxonomy_path=arguments.taxonomy,
        )
        result = validate_bundle(
            bundle,
            require_approved_taxonomy=arguments.require_approved_taxonomy,
        )
        validate_instance(result.report, "curriculum-validation-report")
        if arguments.report is not None:
            arguments.report.parent.mkdir(parents=True, exist_ok=True)
            arguments.report.write_text(json.dumps(result.report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    except (OSError, ValueError, json.JSONDecodeError, yaml.YAMLError, SchemaValidationError) as error:
        print(f"{arguments.structure}: INVALID", file=sys.stderr)
        if isinstance(error, SchemaValidationError):
            for issue in error.issues:
                print(f"  {issue.instance_path}: {issue.message}", file=sys.stderr)
        else:
            print(f"  {error}", file=sys.stderr)
        return 1
    if result.valid:
        counts = result.report["counts"]
        print(
            f"{arguments.structure}: VALID "
            f"({counts['tiers']} tiers, {counts['units']} units, {counts['lessons']} lessons, "
            f"{counts['reviews']} reviews, {counts['graph_nodes']} graph nodes)"
        )
        return 0
    print(f"{arguments.structure}: INVALID ({len(result.issues)} issues)", file=sys.stderr)
    for issue in result.issues:
        print(f"  {issue.code} {issue.path}: {issue.message}", file=sys.stderr)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
