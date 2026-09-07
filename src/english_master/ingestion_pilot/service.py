"""Deterministic, offline-only implementation for the post-M3 Tatoeba pilot."""
from __future__ import annotations

import csv
import hashlib
import io
import json
import os
import tempfile
from datetime import datetime
from pathlib import Path
from typing import Any, Mapping
from urllib.parse import urlsplit

from english_master.ingest import _timestamp
from english_master.ingestion import default_adapter_registry
from english_master.ingestion.base import FetchOptions
from english_master.ingestion.pipeline import IngestionError, IngestionPipeline, PipelinePaths
from english_master.lesson_generation.canonical import identity, sha256_json
from english_master.normalization.pipeline import NormalizationPipeline, PipelineConfig
from english_master.schema_validation import (
    SchemaValidationError,
    load_source_registry,
    require_source_permission,
    validate_instance,
)

from english_master.ingestion.adapters.tatoeba_text import EXPECTED_HEADER

JsonObject = dict[str, Any]


class PilotError(RuntimeError):
    """A boundary failure that must not publish pilot-normalized records."""


def _sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _canonical(value: Any) -> bytes:
    return (json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n").encode("utf-8")


def _write_once(path: Path, data: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        if path.read_bytes() == data:
            return
        raise PilotError(f"Refusing to overwrite immutable pilot output: {path}")
    descriptor, temporary_name = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
    temporary = Path(temporary_name)
    try:
        with os.fdopen(descriptor, "wb") as handle:
            handle.write(data)
            handle.flush()
            os.fsync(handle.fileno())
        try:
            os.link(temporary, path)
        except FileExistsError:
            if path.read_bytes() != data:
                raise PilotError(f"Concurrent immutable pilot output conflict: {path}") from None
    finally:
        temporary.unlink(missing_ok=True)


def _load_json(path: Path, schema: str) -> JsonObject:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise PilotError(f"Cannot load pilot document {path}: {error}") from error
    if not isinstance(value, dict):
        raise PilotError(f"Pilot document must be an object: {path}")
    try:
        validate_instance(value, schema)
    except SchemaValidationError as error:
        raise PilotError(f"Invalid {schema}: {error}") from error
    return value


def _require_descendant(path: Path, root: Path, label: str) -> Path:
    resolved_path = path.resolve(strict=False)
    resolved_root = root.resolve(strict=False)
    try:
        resolved_path.relative_to(resolved_root)
    except ValueError as error:
        raise PilotError(f"{label} must remain below {resolved_root}") from error
    return resolved_path


def _verify_identity(value: Mapping[str, Any], prefix: str, key: str) -> None:
    if value.get(key) != identity(prefix, value, key):
        raise PilotError(f"Pilot {key} does not reconstruct canonically")


def _registry_hash(path: Path) -> str:
    return _sha256_bytes(path.read_bytes())


def _registered_source(registry_path: Path) -> JsonObject:
    registry = load_source_registry(registry_path)
    for operation in (
        "fetch_source", "ingest_source", "store_source", "transform_source",
        "ingest_text", "store_text", "transform_text",
    ):
        require_source_permission(registry, "src_tatoeba_text", operation)
    return registry


def _verify_boundary(
    authorization: Mapping[str, Any], receipt: Mapping[str, Any], payload: Path, registry_path: Path,
) -> bytes:
    _verify_identity(authorization, "pilotauth", "authorization_id")
    _verify_identity(receipt, "pilotreceipt", "receipt_id")
    registry = _registered_source(registry_path)
    required_operations = {
        "fetch_source", "ingest_source", "store_source", "transform_source",
        "ingest_text", "store_text", "transform_text",
    }
    if not required_operations.issubset(set(authorization["authorized_operations"])):
        raise PilotError("Pilot authorization does not grant every required source operation")
    if authorization["registry_sha256"] != _sha256_bytes(registry_path.read_bytes()):
        raise PilotError("Pilot authorization registry hash drift")
    reference = receipt["authorization"]
    if reference != {"id": authorization["authorization_id"], "sha256": sha256_json(authorization)}:
        raise PilotError("Pilot receipt authorization binding drift")
    for key in ("source_id", "official_download_url", "expected_filename", "expected_payload_sha256", "expected_payload_bytes"):
        receipt_key = {"expected_filename": "filename", "expected_payload_sha256": "payload_sha256", "expected_payload_bytes": "payload_bytes"}.get(key, key)
        if authorization[key] != receipt[receipt_key]:
            raise PilotError(f"Pilot receipt {receipt_key} conflicts with authorization")
    if receipt["acquisition_method"] not in {"OFFICIAL_DOWNLOAD", "OFFICIAL_API"}:
        raise PilotError("Pilot acquisition method is not an official route")
    source = next(
        candidate for candidate in registry["sources"] if candidate["source_id"] == "src_tatoeba_text"
    )
    access = source.get("access")
    if not isinstance(access, Mapping):
        raise PilotError("Registered Tatoeba source lacks access metadata")
    allowed_urls = [urlsplit(str(access[key])) for key in ("dataset_url", "api_url") if isinstance(access.get(key), str)]
    actual = urlsplit(str(authorization["official_download_url"]))
    path_allowed = any(actual.netloc == allowed.netloc and (actual.path == allowed.path or actual.path.startswith(allowed.path.rstrip("/") + "/")) for allowed in allowed_urls)
    if actual.scheme != "https" or not path_allowed:
        raise PilotError("Pilot official download URL is outside the registered source host")
    if payload.name != authorization["expected_filename"]:
        raise PilotError("Pilot payload filename conflicts with authorization")
    content = payload.read_bytes()
    if len(content) != authorization["expected_payload_bytes"] or _sha256_bytes(content) != authorization["expected_payload_sha256"]:
        raise PilotError("Pilot payload bytes do not match authorization")
    if receipt["checksum_verified"] is not True:
        raise PilotError("Pilot receipt does not verify its declared payload checksum")
    return content


def _parse_authorized_rows(content: bytes, authorization: Mapping[str, Any]) -> tuple[list[dict[str, str]], dict[str, int]]:
    try:
        text = content.decode("utf-8-sig")
        if content.lstrip().startswith(b"{"):
            document = json.loads(text)
            raw_rows = document.get("data") if isinstance(document, dict) else None
            if not isinstance(raw_rows, list):
                raise PilotError("Official API payload must contain a data array")
            rows = [{"sentence_id": str(item.get("id", "")), "language": str(item.get("lang", "")), "text": str(item.get("text", "")), "author": str(item.get("owner", "")), "license": (str(item.get("license", "")) if str(item.get("license", "")) != "CC BY 2.0 FR" else str(authorization["license"])), "license_url": str(authorization["license_url"])} for item in raw_rows if isinstance(item, dict)]
        else:
            rows = list(csv.DictReader(text.splitlines(), delimiter="\t", strict=True))
    except (UnicodeDecodeError, UnicodeEncodeError, csv.Error, json.JSONDecodeError) as error:
        raise PilotError(f"Unsupported or malformed pinned Tatoeba TSV: {error}") from error
    if not rows or tuple(rows[0]) != EXPECTED_HEADER:
        raise PilotError("Pilot payload does not use the supported six-column Tatoeba TSV layout")
    selected: list[dict[str, str]] = []
    excluded: dict[str, int] = {}
    seen: set[str] = set()
    for row in rows:
        if set(row) != set(EXPECTED_HEADER) or any(not isinstance(row.get(key), str) or not row[key] for key in EXPECTED_HEADER):
            excluded["MALFORMED"] = excluded.get("MALFORMED", 0) + 1
            continue
        sentence_id = row["sentence_id"]
        if not sentence_id.isascii() or not sentence_id.isdigit() or sentence_id in seen:
            excluded["INVALID_OR_DUPLICATE_ID"] = excluded.get("INVALID_OR_DUPLICATE_ID", 0) + 1
            continue
        seen.add(sentence_id)
        if row["language"].lower() != authorization["language"]:
            excluded["NON_ENGLISH"] = excluded.get("NON_ENGLISH", 0) + 1
            continue
        if row["license"] != authorization["license"] or row["license_url"] != authorization["license_url"]:
            excluded["LICENSE_MISMATCH"] = excluded.get("LICENSE_MISMATCH", 0) + 1
            continue
        selected.append({key: row[key] for key in EXPECTED_HEADER})
    selected.sort(key=lambda row: int(row["sentence_id"]))
    target = int(authorization["target_records"])
    if len(selected) < target:
        raise PilotError(f"Only {len(selected)} authorized English records are available; {target} required")
    return selected[:target], excluded


def prepare(*, authorization_path: Path, receipt_path: Path, payload_path: Path, registry_path: Path, output_directory: Path, data_root: Path) -> JsonObject:
    """Verify a local official payload and create an immutable prepared TSV/report."""
    _require_descendant(output_directory, data_root / "raw", "Pilot preparation output")
    authorization = _load_json(authorization_path, "ingestion-pilot-authorization")
    receipt = _load_json(receipt_path, "ingestion-pilot-receipt")
    content = _verify_boundary(authorization, receipt, payload_path, registry_path)
    selected, exclusions = _parse_authorized_rows(content, authorization)
    destination = output_directory.resolve()
    tsv_path = destination / "prepared" / "english-authorized-records.tsv"
    output = io.StringIO(newline="")
    writer = csv.DictWriter(output, fieldnames=EXPECTED_HEADER, delimiter="\t", lineterminator="\n", quoting=csv.QUOTE_MINIMAL)
    writer.writeheader()
    writer.writerows(selected)
    prepared = output.getvalue().encode("utf-8")
    report: JsonObject = {
        "schema_version": "1.0", "record_type": "ingestion_pilot_preparation_report", "report_id": "PENDING",
        "authorization": {"id": authorization["authorization_id"], "sha256": sha256_json(authorization)},
        "receipt": {"id": receipt["receipt_id"], "sha256": sha256_json(receipt)},
        "source_id": "src_tatoeba_text", "official_payload_sha256": _sha256_bytes(content),
        "prepared_tsv_sha256": _sha256_bytes(prepared), "prepared_tsv_bytes": len(prepared),
        "records_examined": (
            len(json.loads(content.decode("utf-8-sig")).get("data", []))
            if content.lstrip().startswith(b"{")
            else len(content.decode("utf-8-sig").splitlines()) - 1
        ),
        "records_selected": len(selected), "exclusions": exclusions,
        "selected_source_ids_sha256": _sha256_bytes("\n".join(row["sentence_id"] for row in selected).encode("ascii")),
        "outcome": "PREPARED", "content_lifecycle_status": "UNREVIEWED", "approved_corpus": False,
        "lesson_material": False, "release_eligible": False,
    }
    report["report_id"] = identity("pilotprep", report, "report_id")
    validate_instance(report, "ingestion-pilot-preparation-report")
    _write_once(tsv_path, prepared)
    _write_once(destination / "preparation-report.json", json.dumps(report, ensure_ascii=False, sort_keys=True, indent=2).encode("utf-8") + b"\n")
    return report


def _verify_preparation(authorization: Mapping[str, Any], receipt: Mapping[str, Any], report: Mapping[str, Any], prepared_path: Path) -> None:
    _verify_identity(report, "pilotprep", "report_id")
    validate_instance(dict(report), "ingestion-pilot-preparation-report")
    if report["authorization"] != {"id": authorization["authorization_id"], "sha256": sha256_json(authorization)} or report["receipt"] != {"id": receipt["receipt_id"], "sha256": sha256_json(receipt)}:
        raise PilotError("Pilot preparation authority binding drift")
    content = prepared_path.read_bytes()
    if report["prepared_tsv_sha256"] != _sha256_bytes(content) or report["prepared_tsv_bytes"] != len(content):
        raise PilotError("Pilot prepared TSV hash drift")
    if report["records_selected"] != authorization["target_records"]:
        raise PilotError("Pilot preparation count does not match authorization")


def run(*, authorization_path: Path, receipt_path: Path, preparation_report_path: Path, prepared_tsv_path: Path, registry_path: Path, data_root: Path, retrieved_at: datetime, processed_at: datetime) -> JsonObject:
    """Run strict M3 ingestion and M4 deduplication from a verified prepared TSV."""
    prohibited_output_names = {"approved", "curriculum", "lessons", "exercises", "exports"}
    if prohibited_output_names.intersection(part.lower() for part in data_root.parts):
        raise PilotError("Pilot output root cannot be approved, curriculum, or export storage")
    authorization = _load_json(authorization_path, "ingestion-pilot-authorization")
    receipt = _load_json(receipt_path, "ingestion-pilot-receipt")
    _verify_identity(authorization, "pilotauth", "authorization_id")
    _verify_identity(receipt, "pilotreceipt", "receipt_id")
    if authorization["registry_sha256"] != _registry_hash(registry_path):
        raise PilotError("Pilot authorization registry hash drift")
    required_operations = {"fetch_source", "ingest_source", "store_source", "transform_source", "ingest_text", "store_text", "transform_text"}
    if not required_operations.issubset(set(authorization["authorized_operations"])):
        raise PilotError("Pilot authorization does not grant every required source operation")
    _registered_source(registry_path)
    report = _load_json(preparation_report_path, "ingestion-pilot-preparation-report")
    _verify_preparation(authorization, receipt, report, prepared_tsv_path)
    ingestion = IngestionPipeline(default_adapter_registry(), registry_path, PipelinePaths(data_root))
    try:
        ingestion_report = ingestion.run("src_tatoeba_text", FetchOptions(prepared_tsv_path, int(authorization["target_records"]), retrieved_at, "authorized_pilot"))
    except IngestionError as error:
        raise PilotError(str(error)) from error
    normalized_run = data_root / "normalized" / "src_tatoeba_text" / "runs" / str(ingestion_report["run_id"])
    normalized = NormalizationPipeline().run(PipelineConfig(
        input_path=normalized_run, output_root=data_root / "deduplicated", source_registry_path=registry_path,
        processed_at=processed_at, max_records=int(authorization["target_records"]),
    ))
    return {"preparation_report_id": report["report_id"], "ingestion_report": ingestion_report, "normalization_report": normalized, "approved_corpus": False, "lesson_material": False, "release_eligible": False}


def verify(*, authorization_path: Path, receipt_path: Path, preparation_report_path: Path, prepared_tsv_path: Path, registry_path: Path) -> JsonObject:
    """Read-only verification of local authorization and preparation artifacts."""
    authorization = _load_json(authorization_path, "ingestion-pilot-authorization")
    receipt = _load_json(receipt_path, "ingestion-pilot-receipt")
    _verify_identity(authorization, "pilotauth", "authorization_id")
    _verify_identity(receipt, "pilotreceipt", "receipt_id")
    if authorization["registry_sha256"] != _registry_hash(registry_path):
        raise PilotError("Pilot authorization registry hash drift")
    required_operations = {"fetch_source", "ingest_source", "store_source", "transform_source", "ingest_text", "store_text", "transform_text"}
    if not required_operations.issubset(set(authorization["authorized_operations"])):
        raise PilotError("Pilot authorization does not grant every required source operation")
    _registered_source(registry_path)
    report = _load_json(preparation_report_path, "ingestion-pilot-preparation-report")
    _verify_preparation(authorization, receipt, report, prepared_tsv_path)
    return {"authorization_id": authorization["authorization_id"], "receipt_id": receipt["receipt_id"], "preparation_report_id": report["report_id"], "records_selected": report["records_selected"], "verified": True}
