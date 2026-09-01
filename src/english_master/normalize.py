"""Offline CLI for deterministic M4 normalization and deduplication."""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path

from english_master.normalization.models import NearDuplicatePolicy
from english_master.normalization.pipeline import NormalizationError, NormalizationPipeline, PipelineConfig
from english_master.normalization.storage import NormalizationStorageError
from english_master.schema_validation import (
    SchemaValidationError,
    SourcePermissionError,
    repository_root,
)


def _timestamp(value: str) -> datetime:
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as error:
        raise argparse.ArgumentTypeError("timestamp must be ISO 8601") from error
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise argparse.ArgumentTypeError("timestamp must include a timezone or Z")
    return parsed


def build_parser() -> argparse.ArgumentParser:
    """Build the normalization command-line parser."""

    parser = argparse.ArgumentParser(
        description="Normalize and deduplicate bounded M3 normalized-text records offline."
    )
    parser.add_argument("--input", required=True, type=Path, help="M3 record file or run/directory")
    parser.add_argument("--output-root", required=True, type=Path, help="Root for atomic M4 runs")
    parser.add_argument("--processed-at", required=True, type=_timestamp, help="Explicit ISO 8601 run time")
    parser.add_argument("--max-records", required=True, type=int, help="Hard input record bound")
    parser.add_argument("--ngram-size", type=int, default=3)
    parser.add_argument("--near-threshold", type=float, default=0.85)
    parser.add_argument("--minimum-characters", type=int, default=12)
    parser.add_argument("--max-candidates-per-record", type=int, default=50)
    parser.add_argument(
        "--source-registry",
        type=Path,
        default=repository_root() / "sources" / "registry.yaml",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    """Execute one offline run and return a process exit status."""

    arguments = build_parser().parse_args(argv)
    try:
        config = PipelineConfig(
            input_path=arguments.input,
            output_root=arguments.output_root,
            source_registry_path=arguments.source_registry,
            processed_at=arguments.processed_at,
            max_records=arguments.max_records,
            near_policy=NearDuplicatePolicy(
                ngram_size=arguments.ngram_size,
                threshold=arguments.near_threshold,
                minimum_characters=arguments.minimum_characters,
                max_candidates_per_record=arguments.max_candidates_per_record,
            ),
        )
        report = NormalizationPipeline().run(config)
    except (
        OSError,
        ValueError,
        json.JSONDecodeError,
        NormalizationError,
        NormalizationStorageError,
        SchemaValidationError,
        SourcePermissionError,
    ) as error:
        print(f"Normalization failed: {error}", file=sys.stderr)
        return 1
    counts = report["counts"]
    print(
        f"{report['run_id']}: {counts['output_records']} records, "
        f"{counts['exact_groups']} exact groups, "
        f"{counts['near_duplicate_candidates']} review candidates"
    )
    print(f"Report: {report['output_paths']['report']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
