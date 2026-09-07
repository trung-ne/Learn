"""Closed-inventory M10 finding-batch construction and verification."""
from __future__ import annotations

from collections.abc import Mapping
from pathlib import Path
from typing import Any

from english_master.independent_review.authority import ReviewSubject
from english_master.lesson_generation.canonical import identity, sha256_json
from english_master.schema_validation import validate_instance

from .evidence import validate_review_input

JsonObject = dict[str, Any]


def _named_references(prefix: str, values: Mapping[str, Mapping[str, Any]]) -> list[JsonObject]:
    return [
        {"path": f"{prefix}/{key.split('_', 1)[-1][:16]}.json", "sha256": sha256_json(value)}
        for key, value in sorted(values.items())
    ]


def build_finding_batch(
    *,
    selection: Mapping[str, Any],
    subjects: Mapping[str, ReviewSubject],
    machine_reports: Mapping[str, Mapping[str, Any]],
    inputs: Mapping[str, Mapping[str, Any]],
    imported_at: str,
    inventory: list[Mapping[str, Any]],
) -> JsonObject:
    """Build a non-promotable immutable batch from actual failed M9 captures."""
    if not inputs:
        raise ValueError("M10 requires at least one imported M9 review input")
    for input_id, input_value in inputs.items():
        subject_id = str(input_value.get("subject_id"))
        subject = subjects.get(subject_id)
        report = machine_reports.get(subject_id)
        if input_id != input_value.get("input_id") or subject is None or report is None:
            raise ValueError(f"M10 input refers to unavailable subject/report: {input_id}")
        issues = validate_review_input(input_value, selection=selection, subject=subject, machine_report=report)
        if issues:
            raise ValueError(f"invalid M10 review input {input_id}: {'; '.join(issues)}")
    value: JsonObject = {
        "schema_version": "1.0",
        "record_type": "m10_finding_batch",
        "batch_id": "PENDING",
        "source_milestone": "M9",
        "evidence_purpose": "M10_REVISION_INPUT",
        "promotion_status": "NON_PROMOTABLE",
        "selection_id": selection["selection_id"],
        "selection_sha256": sha256_json(selection),
        "machine_reports": _named_references("machine", machine_reports),
        "review_inputs": _named_references("inputs", inputs),
        "inventory": [dict(entry) for entry in sorted(inventory, key=lambda entry: str(entry["path"]))],
        "imported_at": imported_at,
        "content_lifecycle_status": "UNREVIEWED",
        "human_reviewed": False,
        "release_approved": False,
        "provider_authenticated": False,
    }
    value["batch_id"] = identity("m10findings", value, "batch_id")
    validate_instance(value, "m10-finding-batch")
    return value


def verify_finding_batch(
    directory: Path,
    *,
    selection: Mapping[str, Any],
    subjects: Mapping[str, ReviewSubject],
) -> JsonObject:
    """Read-only validation of a published M10 finding batch."""
    from english_master.curriculum_review.loading import load_strict_document

    root = directory.resolve(strict=True)
    if not root.is_dir() or root.is_symlink():
        raise ValueError("M10 finding batch must be a real directory")
    for path in root.rglob("*"):
        if path.is_symlink() or (path.exists() and not path.is_dir() and not path.is_file()):
            raise ValueError(f"M10 finding batch contains unsafe path: {path}")
    stored_selection = load_strict_document(root / "selection.json")
    if not isinstance(stored_selection, dict) or sha256_json(stored_selection) != sha256_json(selection):
        raise ValueError("M10 finding batch selection file drift")
    batch = load_strict_document(root / "finding-batch.json")
    if not isinstance(batch, dict):
        raise ValueError("M10 finding batch root must be an object")
    validate_instance(batch, "m10-finding-batch")
    if batch.get("batch_id") != identity("m10findings", batch, "batch_id"):
        raise ValueError("M10 finding batch ID does not reconstruct")
    if batch.get("selection_id") != selection.get("selection_id") or batch.get("selection_sha256") != sha256_json(selection):
        raise ValueError("M10 finding batch selection binding drift")
    input_references = batch.get("review_inputs", [])
    if not isinstance(input_references, list) or not input_references:
        raise ValueError("M10 finding batch has no review input references")
    expected_paths = {"selection.json", "finding-batch.json"}
    report_by_hash: dict[str, Mapping[str, Any]] = {}
    for reference in batch.get("machine_reports", []):
        path = root / str(reference["path"])
        value = load_strict_document(path)
        if not isinstance(value, dict) or sha256_json(value) != reference.get("sha256"):
            raise ValueError("M10 machine report hash drift")
        report_by_hash[sha256_json(value)] = value
        expected_paths.add(str(reference["path"]))
    for reference in input_references:
        path = root / str(reference["path"])
        value = load_strict_document(path)
        if not isinstance(value, dict) or sha256_json(value) != reference.get("sha256"):
            raise ValueError("M10 review input hash drift")
        subject_id = value.get("subject_id")
        subject = subjects.get(str(subject_id))
        report = report_by_hash.get(str(value.get("machine_report_sha256")))
        if subject is None or report is None:
            raise ValueError("M10 review input subject/report reference drift")
        issues = validate_review_input(value, selection=selection, subject=subject, machine_report=report)
        if issues:
            raise ValueError(f"invalid M10 review input: {'; '.join(issues)}")
        expected_paths.add(str(reference["path"]))
    actual_paths = {path.relative_to(root).as_posix() for path in root.rglob("*.json")}
    if actual_paths != expected_paths:
        raise ValueError("M10 finding batch has missing or extra JSON files")
    inventory = [{"path": path, "sha256": sha256_json(load_strict_document(root / path))} for path in sorted(actual_paths - {"finding-batch.json"})]
    if inventory != batch.get("inventory"):
        raise ValueError("M10 finding batch inventory drift")
    return batch
