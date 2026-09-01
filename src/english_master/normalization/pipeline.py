"""Deterministic orchestration for post-M3 normalization and deduplication."""

from __future__ import annotations

import json
import shutil
import tempfile
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

from english_master.normalization.exact import ExactDeduplicationError, build_exact_groups
from english_master.normalization.hashes import (
    canonical_json_bytes,
    normalized_comparison_hash,
    raw_record_hash,
    sha256_bytes,
)
from english_master.normalization.models import (
    InputRecord,
    NearDuplicatePolicy,
    NormalizationPolicy,
    ProcessedRecord,
)
from english_master.normalization.near import find_near_duplicate_candidates
from english_master.normalization.semantic import build_review_queue
from english_master.normalization.storage import NormalizationStorageError, pretty_json_bytes
from english_master.normalization.text import normalize_comparison_text, normalize_display_text
from english_master.schema_validation import (
    SchemaValidationError,
    load_source_registry,
    require_source_permission,
    validate_instance,
)


class NormalizationError(RuntimeError):
    """A normalization failure that did not publish partial accepted output."""


@dataclass(frozen=True)
class PipelineConfig:
    """Explicit bounded input and policy configuration."""

    input_path: Path
    output_root: Path
    source_registry_path: Path
    processed_at: datetime
    max_records: int = 10_000
    normalization_policy: NormalizationPolicy = NormalizationPolicy()
    near_policy: NearDuplicatePolicy = NearDuplicatePolicy()
    deduplication_policy_version: str = "hash-exact-v1"

    def validate(self) -> None:
        if not 1 <= self.max_records <= 100_000:
            raise ValueError("max_records must be between 1 and 100000")
        if self.processed_at.tzinfo is None or self.processed_at.utcoffset() is None:
            raise ValueError("processed_at must include a timezone")
        if self.normalization_policy.unicode_form != "NFC":
            raise ValueError("Only the documented NFC normalization policy is supported")
        self.near_policy.validate()


def _record_paths(input_path: Path) -> tuple[Path, ...]:
    if input_path.is_file():
        return (input_path,)
    if not input_path.is_dir():
        raise NormalizationError(f"Input does not exist or is not a file/directory: {input_path}")
    records_directory = input_path / "records"
    search_root = records_directory if records_directory.is_dir() else input_path
    paths = tuple(sorted(search_root.glob("*.json"), key=lambda path: path.name))
    if not paths:
        raise NormalizationError(f"No JSON record files found in: {search_root}")
    return paths


def load_input_records(input_path: Path, max_records: int) -> tuple[InputRecord, ...]:
    """Load a bounded set of strict M3 normalized-text record files."""

    paths = _record_paths(input_path)
    if len(paths) > max_records:
        raise NormalizationError(
            f"Input contains {len(paths)} records, exceeding max_records={max_records}"
        )
    records: list[InputRecord] = []
    for path in paths:
        try:
            value = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, UnicodeError, json.JSONDecodeError) as error:
            raise NormalizationError(f"Cannot load input record {path}: {error}") from error
        if not isinstance(value, dict):
            raise NormalizationError(f"Input record must be a JSON object: {path}")
        try:
            validate_instance(value, "normalized-text")
        except SchemaValidationError as error:
            raise NormalizationError(f"Invalid M3 normalized record {path}: {error}") from error
        records.append(InputRecord(document=value, location=path))
    return tuple(records)


def _relative_location(path: Path, input_path: Path) -> str:
    root = input_path if input_path.is_dir() else input_path.parent
    try:
        return path.resolve().relative_to(root.resolve()).as_posix()
    except ValueError:
        return path.name


def _process_record(
    record: InputRecord,
    input_path: Path,
    policy: NormalizationPolicy,
    deduplication_policy_version: str,
    processed_at: str,
) -> ProcessedRecord:
    source = record.document
    location = _relative_location(record.location, input_path)
    display_text = normalize_display_text(source["text"], policy)
    comparison_text = normalize_comparison_text(source["text"], policy)
    if not comparison_text:
        raise NormalizationError(f"Comparison text is empty after normalization: {record.location}")
    raw_hash = raw_record_hash(source)
    normalized_hash = normalized_comparison_hash(source["language"], comparison_text)
    identity_material = {"m3_record_id": source["id"], "original_raw_location": location}
    processed_id = f"norm_{sha256_bytes(canonical_json_bytes(identity_material))[:20]}"
    document: dict[str, Any] = {
        "schema_version": "1.0",
        "record_type": "normalized_comparison_record",
        "id": processed_id,
        "m3_record_id": source["id"],
        "m3_ingestion_version": source["ingestion_version"],
        "source_id": source["provenance"]["source_id"],
        "source_record_id": source["provenance"]["source_record_id"],
        "language": source["language"],
        "original_text": source["text"],
        "display_text": display_text,
        "comparison_text": comparison_text,
        "original_raw_location": location,
        "raw_hash": raw_hash,
        "normalized_hash": normalized_hash,
        "source_content_hash": source["provenance"]["content_hash"].lower(),
        "source_content_hash_verification": {
            "status": "NOT_VERIFIABLE_FROM_M3_RECORD",
            "reason": "M3 provenance hashes source-row bytes, which are not embedded in the normalized record",
        },
        "normalization_policy": policy.as_dict(),
        "deduplication_policy_version": deduplication_policy_version,
        "processed_at": processed_at,
        "provenance": source["provenance"],
        "disposition": "ACCEPTED",
    }
    validate_instance(document, "normalization-record")
    return ProcessedRecord(document=document)


def _validate_derived_integrity(
    records: tuple[ProcessedRecord, ...],
    groups: tuple[dict[str, object], ...],
    candidates: tuple[dict[str, object], ...],
    queue: dict[str, object],
) -> None:
    record_ids = {record.id for record in records}
    if len(record_ids) != len(records):
        raise NormalizationError("Derived normalized record IDs are not unique")
    for record in records:
        document = record.document
        if raw_record_hash(_m3_view(document)) != record.raw_hash:
            raise NormalizationError(f"raw_hash recomputation failed for {record.id}")
        expected = normalized_comparison_hash(record.language, record.comparison_text)
        if expected != record.normalized_hash:
            raise NormalizationError(f"normalized_hash recomputation failed for {record.id}")
    group_ids: set[str] = set()
    for group in groups:
        validate_instance(group, "duplicate-group")
        group_id = str(group["id"])
        if group_id in group_ids:
            raise NormalizationError(f"Duplicate duplicate-group ID: {group_id}")
        group_ids.add(group_id)
        references = set(group["member_record_ids"]) | {str(group["canonical_record_id"])}  # type: ignore[arg-type]
        if not references <= record_ids:
            raise NormalizationError(f"Duplicate group {group_id} references missing records")
    candidate_ids: set[str] = set()
    for candidate in candidates:
        validate_instance(candidate, "similarity-candidate")
        candidate_id = str(candidate["id"])
        candidate_ids.add(candidate_id)
        if {str(candidate["left_record_id"]), str(candidate["right_record_id"])} - record_ids:
            raise NormalizationError(f"Similarity candidate {candidate_id} references missing records")
    validate_instance(queue, "semantic-review-queue")
    if set(queue["candidate_ids"]) != candidate_ids:  # type: ignore[arg-type]
        raise NormalizationError("Semantic review queue does not exactly reference candidate output")


def _m3_view(document: dict[str, Any]) -> dict[str, Any]:
    """Reconstruct the exact validated M3 object represented in a derived record."""

    return {
        "schema_version": "1.0",
        "record_type": "normalized_text",
        "id": document["m3_record_id"],
        "language": document["language"],
        "text": document["original_text"],
        "ingestion_version": document["m3_ingestion_version"],
        "provenance": document["provenance"],
    }


def _load_output_documents(directory: Path) -> list[dict[str, Any]]:
    documents: list[dict[str, Any]] = []
    for path in sorted(directory.glob("*.json"), key=lambda item: item.name):
        value = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(value, dict):
            raise NormalizationStorageError(f"Existing output is not a JSON object: {path}")
        documents.append(value)
    return documents


def _verify_existing_run(run_directory: Path, expected_run_hash: str) -> dict[str, Any]:
    report_path = run_directory / "report.json"
    try:
        report = json.loads(report_path.read_text(encoding="utf-8"))
        if not isinstance(report, dict):
            raise NormalizationStorageError(f"Existing report is not an object: {report_path}")
        validate_instance(report, "normalization-report")
        if report["run_hash"] != expected_run_hash:
            raise NormalizationStorageError(f"Existing report has unexpected run hash: {report_path}")
        records = _load_output_documents(run_directory / "records")
        groups = _load_output_documents(run_directory / "groups")
        candidates = _load_output_documents(run_directory / "candidates")
        queue_path = run_directory / "review" / "queue.json"
        queue = json.loads(queue_path.read_text(encoding="utf-8"))
        if not isinstance(queue, dict):
            raise NormalizationStorageError(f"Existing review queue is not an object: {queue_path}")
        content_hash = sha256_bytes(
            b"".join(canonical_json_bytes(item) for item in records)
            + b"".join(canonical_json_bytes(item) for item in groups)
            + b"".join(canonical_json_bytes(item) for item in candidates)
            + canonical_json_bytes(queue)
        )
        if content_hash != report["output_content_hash"]:
            raise NormalizationStorageError(f"Existing run content hash mismatch: {run_directory}")
    except (OSError, json.JSONDecodeError, SchemaValidationError) as error:
        raise NormalizationStorageError(f"Cannot verify existing run {run_directory}: {error}") from error
    return report


class NormalizationPipeline:
    """Normalize, deduplicate, stage, validate, and atomically publish one run."""

    def run(self, config: PipelineConfig) -> dict[str, Any]:
        config.validate()
        registry = load_source_registry(config.source_registry_path)
        inputs = load_input_records(config.input_path, config.max_records)
        source_ids = sorted({record.document["provenance"]["source_id"] for record in inputs})
        for source_id in source_ids:
            require_source_permission(registry, source_id, "store_text")
            require_source_permission(registry, source_id, "transform_text")

        processed_at = config.processed_at.isoformat().replace("+00:00", "Z")
        processed = tuple(
            sorted(
                (
                    _process_record(
                        record,
                        config.input_path,
                        config.normalization_policy,
                        config.deduplication_policy_version,
                        processed_at,
                    )
                    for record in inputs
                ),
                key=lambda record: record.id,
            )
        )
        try:
            groups = build_exact_groups(processed, config.deduplication_policy_version)
        except ExactDeduplicationError as error:
            raise NormalizationError(str(error)) from error
        candidates = find_near_duplicate_candidates(processed, config.near_policy)
        queue = build_review_queue(candidates)

        duplicate_members = {
            member_id
            for group in groups
            for member_id in group["member_record_ids"]  # type: ignore[union-attr]
            if member_id != group["canonical_record_id"]
        }
        review_members = {
            str(candidate[field])
            for candidate in candidates
            for field in ("left_record_id", "right_record_id")
        }
        final_records: list[ProcessedRecord] = []
        for record in processed:
            document = dict(record.document)
            if record.id in duplicate_members:
                document["disposition"] = "DUPLICATE"
            elif record.id in review_members:
                document["disposition"] = "REVIEW_REQUIRED"
            final_records.append(ProcessedRecord(document))
        processed = tuple(final_records)
        _validate_derived_integrity(processed, groups, candidates, queue)

        run_material = {
            "input_records": [
                {"id": record.document["m3_record_id"], "raw_hash": record.raw_hash}
                for record in processed
            ],
            "normalization_policy": config.normalization_policy.as_dict(),
            "near_duplicate_policy": config.near_policy.as_dict(),
            "deduplication_policy_version": config.deduplication_policy_version,
            "processed_at": processed_at,
        }
        run_hash = sha256_bytes(canonical_json_bytes(run_material))
        run_id = f"normrun_{run_hash[:20]}"
        run_directory = config.output_root / "runs" / run_id
        report_path = run_directory / "report.json"
        if report_path.is_file():
            return _verify_existing_run(run_directory, run_hash)
        if run_directory.exists():
            raise NormalizationStorageError(f"Incomplete run directory already exists: {run_directory}")

        counts = {
            "input_records": len(inputs),
            "output_records": len(processed),
            "exact_groups": len(groups),
            "raw_duplicate_groups": sum(group["deduplication_reason"] == "RAW_HASH" for group in groups),
            "normalized_duplicate_groups": sum(
                group["deduplication_reason"] == "NORMALIZED_HASH" for group in groups
            ),
            "near_duplicate_candidates": len(candidates),
            "review_required": len(candidates),
        }
        report: dict[str, Any] = {
            "schema_version": "1.0",
            "record_type": "normalization_run_report",
            "run_id": run_id,
            "run_hash": run_hash,
            "processed_at": processed_at,
            "source_ids": source_ids,
            "input": {"path": config.input_path.as_posix(), "max_records": config.max_records},
            "normalization_policy": config.normalization_policy.as_dict(),
            "deduplication_policy": {
                "version": config.deduplication_policy_version,
                "exact_methods": ["RAW_HASH", "NORMALIZED_HASH"],
            },
            "near_duplicate_policy": config.near_policy.as_dict(),
            "counts": counts,
            "outcome": "COMPLETED",
            "output_paths": {
                "run": run_directory.as_posix(),
                "records": (run_directory / "records").as_posix(),
                "groups": (run_directory / "groups").as_posix(),
                "candidates": (run_directory / "candidates").as_posix(),
                "review_queue": (run_directory / "review" / "queue.json").as_posix(),
                "report": report_path.as_posix(),
            },
            "output_content_hash": sha256_bytes(
                b"".join(canonical_json_bytes(record.document) for record in processed)
                + b"".join(canonical_json_bytes(group) for group in groups)
                + b"".join(canonical_json_bytes(candidate) for candidate in candidates)
                + canonical_json_bytes(queue)
            ),
        }
        validate_instance(report, "normalization-report")

        run_directory.parent.mkdir(parents=True, exist_ok=True)
        stage = Path(tempfile.mkdtemp(prefix=f".{run_id}.", dir=run_directory.parent))
        try:
            for directory in ("records", "groups", "candidates", "review"):
                (stage / directory).mkdir()
            for record in processed:
                (stage / "records" / f"{record.id}.json").write_bytes(pretty_json_bytes(record.document))
            for group in groups:
                (stage / "groups" / f"{group['id']}.json").write_bytes(pretty_json_bytes(group))
            for candidate in candidates:
                (stage / "candidates" / f"{candidate['id']}.json").write_bytes(
                    pretty_json_bytes(candidate)
                )
            (stage / "review" / "queue.json").write_bytes(pretty_json_bytes(queue))
            (stage / "report.json").write_bytes(pretty_json_bytes(report))
            try:
                stage.replace(run_directory)
            except FileExistsError as error:
                raise NormalizationStorageError(f"Run appeared concurrently: {run_directory}") from error
        except Exception:
            shutil.rmtree(stage, ignore_errors=True)
            raise
        return report
