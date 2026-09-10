"""Strict version dispatch for independently verified M12 fixture lineage."""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from english_master.schema_validation import load_document, validate_instance

from .evidence_v2 import verify_v2
from .service import MediaIngestionError, verify

JsonObject = dict[str, Any]


@dataclass(frozen=True)
class VerifiedMediaLineage:
    schema_version: str
    authorization: JsonObject
    receipt: JsonObject
    report: JsonObject
    asset: JsonObject
    verification: JsonObject
    assessment: JsonObject | None


def _record(path: Path, schema_name: str) -> JsonObject:
    try:
        value = load_document(path)
        if not isinstance(value, dict):
            raise ValueError("record is not an object")
        validate_instance(value, schema_name)
        return value
    except (OSError, ValueError) as error:
        raise MediaIngestionError(f"invalid {schema_name}: {error}") from error


def verify_media_lineage(run_directory: Path) -> VerifiedMediaLineage:
    """Verify and load one M12 v1/v2 run without permissive fallback."""
    try:
        raw_report = load_document(run_directory / "run-report.json")
    except (OSError, ValueError) as error:
        raise MediaIngestionError(f"invalid media run report: {error}") from error
    if not isinstance(raw_report, dict):
        raise MediaIngestionError("media run report is not an object")
    dispatch = (raw_report.get("record_type"), raw_report.get("schema_version"))
    if dispatch == ("media_run_report", "1.0"):
        verification = verify(run_directory=run_directory)
        return VerifiedMediaLineage(
            schema_version="1.0",
            authorization=_record(run_directory / "authorization.json", "media-source-authorization"),
            receipt=_record(run_directory / "acquisition-receipt.json", "media-acquisition-receipt"),
            report=_record(run_directory / "run-report.json", "media-run-report"),
            asset=_record(run_directory / "asset-metadata.json", "media-asset-metadata"),
            verification=verification,
            assessment=None,
        )
    if dispatch == ("media_run_report", "2.0"):
        verification = verify_v2(run_directory=run_directory)
        return VerifiedMediaLineage(
            schema_version="2.0",
            authorization=_record(run_directory / "authorization.json", "media-source-authorization-v2"),
            receipt=_record(run_directory / "acquisition-receipt.json", "media-acquisition-receipt-v2"),
            report=_record(run_directory / "run-report.json", "media-run-report-v2"),
            asset=_record(run_directory / "asset-metadata.json", "media-asset-metadata"),
            verification=verification,
            assessment=_record(run_directory / "evidence-assessment.json", "media-evidence-assessment"),
        )
    raise MediaIngestionError(
        "unsupported M12 run report type/version; expected media_run_report 1.0 or 2.0"
    )
