"""Command-line entry point for bounded M3 ingestion runs."""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path

from english_master.ingestion import default_adapter_registry
from english_master.ingestion.base import FetchOptions
from english_master.ingestion.pipeline import (
    IngestionError,
    IngestionPipeline,
    IngestionRunError,
    PipelinePaths,
)
from english_master.ingestion.registry import AdapterRegistryError
from english_master.schema_validation import (
    SchemaValidationError,
    SourcePermissionError,
    repository_root,
)


def _timestamp(value: str) -> datetime:
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as error:
        raise argparse.ArgumentTypeError("must be an ISO 8601 date-time") from error
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise argparse.ArgumentTypeError("must include a UTC offset or Z")
    return parsed


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Ingest a bounded, authorized source input without network access."
    )
    parser.add_argument("--source", required=True, help="Registered source_id")
    parser.add_argument("--input", required=True, type=Path, help="Small local source fixture")
    parser.add_argument(
        "--max-records",
        required=True,
        type=int,
        help="Explicit upper bound; the input fails if it contains more records",
    )
    parser.add_argument(
        "--retrieved-at",
        required=True,
        type=_timestamp,
        help="Explicit provenance timestamp (ISO 8601 with UTC offset)",
    )
    parser.add_argument(
        "--offline-fixture",
        action="store_true",
        help="Confirm this M3 adapter is reading a deterministic local fixture",
    )
    parser.add_argument(
        "--source-registry",
        type=Path,
        default=repository_root() / "sources" / "registry.yaml",
    )
    parser.add_argument("--data-root", type=Path, default=repository_root() / "data")
    return parser


def _print_report(report: dict[str, object], stream: object | None = None) -> None:
    if stream is None:
        stream = sys.stdout
    counts = report["counts"]
    assert isinstance(counts, dict)
    paths = report["output_paths"]
    assert isinstance(paths, dict)
    print(
        f"{report['outcome']}: source={report['source_id']} "
        f"fetched={counts['fetched']} normalized={counts['normalized']} "
        f"rejected={counts['rejected']}",
        file=stream,
    )
    print(f"report: {paths['report']}", file=stream)


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    arguments = parser.parse_args(argv)
    adapters = default_adapter_registry()
    if not arguments.offline_fixture:
        parser.error("--offline-fixture is required; M3 has no network fetch mode")

    pipeline = IngestionPipeline(
        adapters=adapters,
        registry_path=arguments.source_registry,
        paths=PipelinePaths(arguments.data_root),
    )
    try:
        report = pipeline.run(
            arguments.source,
            FetchOptions(
                input_path=arguments.input,
                max_records=arguments.max_records,
                retrieved_at=arguments.retrieved_at,
            ),
        )
    except IngestionRunError as error:
        _print_report(error.report, sys.stderr)
        print(str(error), file=sys.stderr)
        return 1
    except (
        AdapterRegistryError,
        FileNotFoundError,
        IngestionError,
        json.JSONDecodeError,
        OSError,
        SchemaValidationError,
        SourcePermissionError,
        ValueError,
    ) as error:
        print(f"INGESTION FAILED: {error}", file=sys.stderr)
        return 1
    _print_report(report)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
