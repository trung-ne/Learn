"""M10 intake for non-promotable M9 review evidence.

A failed M9 review is valuable immutable revision input, but must never be
represented as M9 approval evidence.
"""
from __future__ import annotations

from collections.abc import Mapping
from datetime import datetime
from typing import Any

from english_master.independent_review.authority import ReviewSubject
from english_master.independent_review.review import CHECKLISTS, build_review_prompt
from english_master.lesson_generation.canonical import identity, sha256_json, sha256_text
from english_master.schema_validation import validate_instance

JsonObject = dict[str, Any]


def _parsed_timestamp(value: object) -> datetime | None:
    if not isinstance(value, str):
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None


def build_review_input(
    *,
    selection: Mapping[str, Any],
    subject: ReviewSubject,
    machine_report: Mapping[str, Any],
    role: str,
    capture: Mapping[str, Any],
    raw_response: Mapping[str, Any],
    observed_at: str,
    imported_at: str,
) -> JsonObject:
    """Wrap one actual M9 response as non-promotable M10 finding evidence."""
    prompt = build_review_prompt(role, subject, machine_report)
    value: JsonObject = {
        "schema_version": "1.0",
        "record_type": "m10_review_input",
        "input_id": "PENDING",
        "source_milestone": "M9",
        "evidence_purpose": "M10_REVISION_INPUT",
        "promotion_status": "NON_PROMOTABLE",
        "selection_id": selection["selection_id"],
        "subject_id": subject.subject_id,
        "content_type": subject.content_type,
        "artifact_sha256": subject.artifact_sha256,
        "machine_report_sha256": sha256_json(machine_report),
        "review_role": role,
        "capture": dict(capture),
        "review_prompt": prompt,
        "review_prompt_sha256": sha256_text(prompt),
        "raw_response": dict(raw_response),
        "raw_response_sha256": sha256_json(raw_response),
        "decision": raw_response["decision"],
        "checklist": list(raw_response["checklist"]),
        "findings": list(raw_response["findings"]),
        "limitations": list(raw_response["limitations"]),
        "observed_at": observed_at,
        "imported_at": imported_at,
        "content_lifecycle_status": "UNREVIEWED",
        "human_reviewed": False,
        "release_approved": False,
        "provider_authenticated": False,
    }
    if subject.modality is not None:
        value["modality"] = subject.modality
    value["input_id"] = identity("m10input", value, "input_id")
    validate_instance(value, "m10-review-input")
    issues = validate_review_input(value, selection=selection, subject=subject, machine_report=machine_report)
    if issues:
        raise ValueError("; ".join(issues))
    return value


def validate_review_input(
    value: Mapping[str, Any], *, selection: Mapping[str, Any], subject: ReviewSubject, machine_report: Mapping[str, Any]
) -> tuple[str, ...]:
    """Validate factual M9 bindings while allowing non-approval findings."""
    try:
        validate_instance(dict(value), "m10-review-input")
    except ValueError as error:
        return (f"SCHEMA: {error}",)
    issues: list[str] = []
    if value.get("input_id") != identity("m10input", value, "input_id"):
        issues.append("INPUT_ID")
    if value.get("selection_id") != selection.get("selection_id") or value.get("subject_id") != subject.subject_id:
        issues.append("SELECTION_BINDING")
    if value.get("content_type") != subject.content_type or value.get("modality") != subject.modality:
        issues.append("SUBJECT_TYPE")
    if value.get("artifact_sha256") != subject.artifact_sha256 or value.get("machine_report_sha256") != sha256_json(machine_report):
        issues.append("HASH_BINDING")
    role = value.get("review_role")
    if role not in CHECKLISTS:
        issues.append("ROLE")
    elif value.get("review_prompt") != build_review_prompt(str(role), subject, machine_report):
        issues.append("PROMPT_RECONSTRUCTION")
    if value.get("review_prompt_sha256") != sha256_text(str(value.get("review_prompt", ""))):
        issues.append("PROMPT_HASH")
    raw = value.get("raw_response")
    if not isinstance(raw, Mapping) or value.get("raw_response_sha256") != sha256_json(raw):
        issues.append("RAW_RESPONSE_HASH")
    elif any(value.get(field) != raw.get(field) for field in ("decision", "checklist", "findings", "limitations")):
        issues.append("RAW_RESPONSE_PROJECTION")
    criteria = [item.get("criterion") for item in value.get("checklist", []) if isinstance(item, Mapping)]
    if role not in CHECKLISTS or set(criteria) != set(CHECKLISTS[role]) or len(criteria) != len(set(criteria)):
        issues.append("CHECKLIST_SCOPE")
    capture = value.get("capture")
    if not isinstance(capture, Mapping) or capture.get("capture_mode") not in {"SESSION_CAPTURED", "PROVIDER_CAPTURED", "TEST_ONLY"} or capture.get("provider_authenticated") is not False:
        issues.append("CAPTURE_PROVENANCE")
    if value.get("promotion_status") != "NON_PROMOTABLE" or value.get("decision") == "APPROVE":
        issues.append("PROMOTION_BOUNDARY")
    has_failed_check = any(item.get("result") == "FAIL" for item in value.get("checklist", []) if isinstance(item, Mapping))
    has_blocking_finding = any(item.get("severity") in {"MAJOR", "CRITICAL"} for item in value.get("findings", []) if isinstance(item, Mapping))
    if not has_failed_check and not has_blocking_finding:
        issues.append("NO_ACTIONABLE_FINDING")
    if not isinstance(capture, Mapping) or value.get("observed_at") != capture.get("observed_at"):
        issues.append("OBSERVATION_BINDING")
    observed_at, imported_at = _parsed_timestamp(value.get("observed_at")), _parsed_timestamp(value.get("imported_at"))
    report_at = _parsed_timestamp(machine_report.get("reviewed_at"))
    if imported_at is None or (value.get("observed_at") != "UNKNOWN" and (observed_at is None or report_at is None or observed_at < report_at)) or (observed_at is not None and imported_at < observed_at):
        issues.append("CHRONOLOGY")
    return tuple(sorted(set(issues)))
