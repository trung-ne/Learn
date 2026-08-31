"""Source-agnostic, failure-safe ingestion orchestration."""

from __future__ import annotations

import hashlib
import json
import os
import shutil
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from english_master.ingestion.base import FetchOptions, RecordError
from english_master.ingestion.registry import AdapterRegistry
from english_master.schema_validation import (
    SchemaValidationError,
    SourcePermissionError,
    load_source_registry,
    require_source_permission,
    validate_instance,
)


class IngestionError(RuntimeError):
    """A fatal run failure that did not publish an invalid normalized record."""


class IngestionRunError(IngestionError):
    """A completed run with audited record errors."""

    def __init__(self, message: str, report: dict[str, Any]) -> None:
        self.report = report
        super().__init__(message)


@dataclass(frozen=True)
class PipelinePaths:
    """Storage roots for one pipeline invocation."""

    data_root: Path

    @property
    def raw(self) -> Path:
        return self.data_root / "raw"

    @property
    def normalized(self) -> Path:
        return self.data_root / "normalized"

    @property
    def quarantine(self) -> Path:
        return self.data_root / "quarantine"


def _canonical_json(value: Any) -> bytes:
    return (json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n").encode(
        "utf-8"
    )


def _pretty_json(value: Any) -> bytes:
    return (json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2) + "\n").encode("utf-8")


def _write_once(path: Path, content: bytes) -> bool:
    """Atomically create *path*, accepting an identical idempotent replay."""

    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        if path.read_bytes() == content:
            return False
        raise IngestionError(f"Refusing to overwrite existing output with different content: {path}")
    descriptor, temporary_name = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
    temporary = Path(temporary_name)
    try:
        with os.fdopen(descriptor, "wb") as file:
            file.write(content)
            file.flush()
            os.fsync(file.fileno())
        try:
            os.link(temporary, path)
        except FileExistsError:
            if path.read_bytes() == content:
                return False
            raise IngestionError(f"Concurrent output conflict: {path}") from None
    finally:
        temporary.unlink(missing_ok=True)
    return True


def _relative(path: Path, data_root: Path) -> str:
    try:
        return path.relative_to(data_root.parent).as_posix()
    except ValueError:
        return path.as_posix()


class IngestionPipeline:
    """Run an adapter only after source registry and operation permission checks."""

    def __init__(
        self,
        adapters: AdapterRegistry,
        registry_path: Path,
        paths: PipelinePaths,
    ) -> None:
        self.adapters = adapters
        self.registry_path = registry_path
        self.paths = paths

    def run(self, source_id: str, options: FetchOptions) -> dict[str, Any]:
        source_registry = load_source_registry(self.registry_path)
        registered_source = next(
            (
                candidate
                for candidate in source_registry["sources"]
                if candidate["source_id"] == source_id
            ),
            None,
        )
        if registered_source is None:
            raise SourcePermissionError(f"Source {source_id!r} is not registered")
        adapter = self.adapters.get(source_id)
        if adapter.source_id != source_id:
            raise IngestionError(
                f"Selected adapter declares {adapter.source_id!r}, expected {source_id!r}"
            )
        source: dict[str, Any] | None = None
        for operation in adapter.required_operations:
            source = require_source_permission(source_registry, source_id, operation)
        if source is None:  # An adapter with no permissions is a contract violation.
            raise IngestionError(f"Adapter {adapter.adapter_id!r} declares no required operations")

        payload = adapter.fetch(options)
        retrieved_at = options.retrieved_at.isoformat().replace("+00:00", "Z")
        run_material = {
            "source_id": source_id,
            "adapter_id": adapter.adapter_id,
            "ingestion_version": adapter.ingestion_version,
            "input": payload.input_description,
            "retrieved_at": retrieved_at,
        }
        run_hash = hashlib.sha256(_canonical_json(run_material)).hexdigest()
        run_id = f"run_{run_hash[:16]}"

        raw_path = self.paths.raw / source_id / run_id / "payload.tsv"
        _write_once(raw_path, payload.content)

        run_directory = self.paths.normalized / source_id / "runs" / run_id
        report_path = run_directory / "report.json"
        if report_path.is_file():
            existing = json.loads(report_path.read_text(encoding="utf-8"))
            if existing.get("run_hash") != run_hash:
                raise IngestionError(f"Existing run report has an unexpected hash: {report_path}")
            return existing
        if run_directory.exists():
            raise IngestionError(f"Incomplete normalized run directory already exists: {run_directory}")

        parsed = adapter.parse(payload)
        errors: list[RecordError] = list(parsed.errors)
        normalized: list[dict[str, Any]] = []
        normalized_ids: set[str] = set()
        for index, raw_record in enumerate(parsed.records, start=1):
            source_record_id = getattr(raw_record, "sentence_id", None)
            try:
                provenance = adapter.provenance(raw_record, source, options)
                record = adapter.normalize(raw_record, provenance)
                validate_instance(record, adapter.normalized_schema)
                record_id = record["id"]
                if record_id in normalized_ids:
                    raise ValueError(f"Duplicate normalized ID {record_id!r}")
            except (KeyError, TypeError, ValueError, SchemaValidationError) as error:
                errors.append(
                    RecordError(
                        stage="normalize",
                        code="record_rejected",
                        message=str(error),
                        record_index=index,
                        source_record_id=(
                            source_record_id if isinstance(source_record_id, str) else None
                        ),
                    )
                )
                continue
            normalized_ids.add(record_id)
            normalized.append(record)

        normalized.sort(key=lambda record: record["id"])
        errors.sort(
            key=lambda error: (
                error.record_index if error.record_index is not None else -1,
                error.stage,
                error.code,
            )
        )

        quarantine_path: Path | None = None
        if errors:
            quarantine_path = (
                self.paths.quarantine / "ingestion_record_error" / source_id / run_id / "errors.json"
            )
            quarantine_document = {
                "schema_version": "1.0",
                "source_id": source_id,
                "run_id": run_id,
                "errors": [error.as_dict() for error in errors],
            }
            _write_once(quarantine_path, _pretty_json(quarantine_document))

        stage_parent = run_directory.parent
        stage_parent.mkdir(parents=True, exist_ok=True)
        stage_directory = Path(
            tempfile.mkdtemp(prefix=f".{run_id}.", dir=stage_parent)
        )
        try:
            records_directory = stage_directory / "records"
            records_directory.mkdir()
            for record in normalized:
                (records_directory / f"{record['id']}.json").write_bytes(_pretty_json(record))

            counts = {
                "fetched": int(payload.input_description.get("record_count", 0)),
                "parsed": len(parsed.records),
                "normalized": len(normalized),
                "rejected": len(errors),
                "quarantined": len(errors),
            }
            report = {
                "schema_version": "1.0",
                "source_id": source_id,
                "adapter_id": adapter.adapter_id,
                "ingestion_version": adapter.ingestion_version,
                "run_id": run_id,
                "run_hash": run_hash,
                "retrieved_at": retrieved_at,
                "input": payload.input_description,
                "outcome": "COMPLETED_WITH_ERRORS" if errors else "COMPLETED",
                "counts": counts,
                "output_paths": {
                    "raw_payload": _relative(raw_path, self.paths.data_root),
                    "normalized_run": _relative(run_directory, self.paths.data_root),
                    "report": _relative(report_path, self.paths.data_root),
                    "quarantine": (
                        _relative(quarantine_path, self.paths.data_root)
                        if quarantine_path is not None
                        else None
                    ),
                },
                "normalized_content_hash": hashlib.sha256(
                    b"".join(_canonical_json(record) for record in normalized)
                ).hexdigest(),
            }
            (stage_directory / "report.json").write_bytes(_pretty_json(report))
            try:
                stage_directory.replace(run_directory)
            except FileExistsError as error:
                raise IngestionError(f"Normalized run appeared concurrently: {run_directory}") from error
        except Exception:
            shutil.rmtree(stage_directory, ignore_errors=True)
            raise

        if errors:
            raise IngestionRunError(
                f"Run {run_id} completed with {len(errors)} rejected record(s)", report
            )
        return report
