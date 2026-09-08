"""Immutable M10 authority-conflict escalation evidence."""
from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any

from english_master.lesson_generation.canonical import identity, sha256_json
from english_master.schema_validation import validate_instance

JsonObject = dict[str, Any]


def _reference(identifier: str, value: Mapping[str, Any]) -> JsonObject:
    return {"id": identifier, "sha256": sha256_json(value)}


def _title_conflicts(
    request: Mapping[str, Any], source_input: Mapping[str, Any]
) -> list[JsonObject]:
    input_id = source_input.get("input_id")
    conflicts: list[JsonObject] = []
    for finding in request.get("findings", []):
        if not isinstance(finding, Mapping) or finding.get("source_input_id") != input_id:
            continue
        source_finding = finding.get("finding")
        if not isinstance(source_finding, Mapping):
            continue
        text = " ".join(
            str(source_finding.get(key, "")) for key in ("description", "recommendation")
        ).casefold()
        if "title" not in text:
            continue
        conflicts.append(
            {
                "finding_index": finding["finding_index"],
                "field_path": "/title",
                "repair_requirement": next(
                    constraint["requirement"]
                    for constraint in request.get("repair_constraints", [])
                    if isinstance(constraint, Mapping)
                    and constraint.get("source_input_id") == input_id
                    and constraint.get("finding_index") == finding["finding_index"]
                ),
                "reason": "The required title replacement would violate the M5-derived M6 lesson specification.",
            }
        )
    return conflicts


def build_authority_conflict_escalation(
    *,
    run: Mapping[str, Any],
    finding_batch: Mapping[str, Any],
    request: Mapping[str, Any],
    source_input: Mapping[str, Any],
    predecessor_lesson: Mapping[str, Any],
    authority_source: str,
    authority_record: Mapping[str, Any],
    created_at: str,
) -> JsonObject:
    """Record a mandatory title repair that M10 lacks authority to make."""
    if run.get("finding_batch_id") != finding_batch.get("batch_id") or run.get("finding_batch_sha256") != sha256_json(finding_batch):
        raise ValueError("M10 escalation run does not bind the finding batch")
    if run.get("revision_request_id") != request.get("request_id") or run.get("revision_request_sha256") != sha256_json(request):
        raise ValueError("M10 escalation run does not bind the revision request")
    source_ids = {
        item.get("input_id")
        for item in request.get("source_inputs", [])
        if isinstance(item, Mapping)
    }
    if source_input.get("input_id") not in source_ids:
        raise ValueError("M10 escalation source input is absent from the revision request")
    title = predecessor_lesson.get("title")
    if not isinstance(title, str) or authority_record.get("title") != title:
        raise ValueError("M10 escalation authority title does not match the immutable predecessor")
    conflicts = _title_conflicts(request, source_input)
    if not conflicts:
        raise ValueError("M10 escalation requires a mandatory title finding")
    value: JsonObject = {
        "schema_version": "1.0",
        "record_type": "m10_escalation",
        "escalation_id": "PENDING",
        "run": _reference(str(run["run_id"]), run),
        "finding_batch": _reference(str(finding_batch["batch_id"]), finding_batch),
        "revision_request": _reference(str(request["request_id"]), request),
        "source_input": _reference(str(source_input["input_id"]), source_input),
        "conflict_code": "AUTHORITY_CONFLICT",
        "retryable": False,
        "authority_constraint": {
            "field_path": "/title",
            "authority_source": authority_source,
            "authority_sha256": sha256_json(authority_record),
            "required_value": title,
            "validator_code": "LESSON_SPEC_MISMATCH",
        },
        "conflicts": conflicts,
        "required_resolution_boundary": "A separately authorized M5 curriculum amendment and regenerated downstream authority are required before another M10 attempt.",
        "created_at": created_at,
        "content_lifecycle_status": "UNREVIEWED",
        "development_approved": False,
        "provider_authenticated": False,
    }
    value["escalation_id"] = identity("m10escalation", value, "escalation_id")
    validate_instance(value, "m10-escalation")
    return value


def validate_authority_conflict_escalation(
    value: Mapping[str, Any],
    *,
    run: Mapping[str, Any],
    finding_batch: Mapping[str, Any],
    request: Mapping[str, Any],
    source_input: Mapping[str, Any],
    predecessor_lesson: Mapping[str, Any],
    authority_record: Mapping[str, Any],
) -> tuple[str, ...]:
    """Validate all immutable cross-record bindings for an escalation."""
    try:
        validate_instance(dict(value), "m10-escalation")
    except ValueError as error:
        return (f"SCHEMA: {error}",)
    issues: list[str] = []
    if value.get("escalation_id") != identity("m10escalation", value, "escalation_id"):
        issues.append("ESCALATION_ID")
    expected = {
        "run": _reference(str(run.get("run_id")), run),
        "finding_batch": _reference(str(finding_batch.get("batch_id")), finding_batch),
        "revision_request": _reference(str(request.get("request_id")), request),
        "source_input": _reference(str(source_input.get("input_id")), source_input),
    }
    for key, reference in expected.items():
        if value.get(key) != reference:
            issues.append(f"{key.upper()}_BINDING")
    constraint = value.get("authority_constraint")
    if not isinstance(constraint, Mapping) or constraint.get("required_value") != predecessor_lesson.get("title") or constraint.get("authority_sha256") != sha256_json(authority_record):
        issues.append("AUTHORITY_CONSTRAINT")
    try:
        expected_conflicts = _title_conflicts(request, source_input)
    except (KeyError, StopIteration, TypeError):
        expected_conflicts = []
    if value.get("conflicts") != expected_conflicts:
        issues.append("FINDING_CONFLICT_BINDING")
    if value.get("retryable") is not False or value.get("conflict_code") != "AUTHORITY_CONFLICT":
        issues.append("RETRY_BOUNDARY")
    return tuple(sorted(set(issues)))
