"""Deterministic M10 revision-request planning without successor generation."""
from __future__ import annotations

import copy
from collections import defaultdict
from collections.abc import Iterable, Mapping
from typing import Any

from english_master.independent_review.authority import ReviewSubject
from english_master.lesson_generation.canonical import identity, sha256_json
from english_master.schema_validation import validate_instance

JsonObject = dict[str, Any]

_TARGETS = {
    "LESSON": "M6",
    "EXERCISE_SET": "M7",
    "AI_PRACTICE_PROMPT": "M8_2",
}
_SCOPE_BOUNDARIES = {
    "LESSON": "Revise only the selected lesson within its existing M6 authority, reference scope, and prerequisite bounds.",
    "EXERCISE_SET": "Regenerate the complete selected M7 exercise set from its unchanged lesson authority; do not edit the predecessor set in place.",
    "AI_PRACTICE_PROMPT": "Revise only the selected lesson/modality protocol under its existing M8.2 authority; republish and verify the complete closed pilot.",
}
_TARGET_CHECKS: dict[str, tuple[tuple[str, str], ...]] = {
    "LESSON": (
        ("M6_SUCCESSOR_VALID", "The revision-2 M6 lesson successor passes its schema, authority, scope, prerequisite, and deterministic machine checks."),
        ("M7_LESSON_SET_REBUILT", "The M7 exercise set for this lesson is rebuilt from the accepted revision-2 M6 lesson."),
        ("M8_2_FULL_PILOT_REBUILT", "The complete closed M8.2 pilot is rebuilt and independently verified against the revised M6 authority."),
    ),
    "EXERCISE_SET": (
        ("M7_SUCCESSOR_VALID", "The complete revision-2 M7 exercise-set successor passes all M7 schema, authority, answer, ambiguity, scope, and duplicate checks."),
    ),
    "AI_PRACTICE_PROMPT": (
        ("M8_2_FULL_PILOT_REBUILT", "The complete closed M8.2 pilot, including the revised prompt, is rebuilt and independently verified."),
    ),
}


def _rebuild_closure(subject: ReviewSubject) -> list[JsonObject]:
    if subject.content_type == "LESSON":
        return [
            {"target_milestone": "M7", "artifact_kind": "EXERCISE_SET", "scope": "SUBJECT_LESSON", "lesson_id": subject.lesson_id},
            {"target_milestone": "M8_2", "artifact_kind": "AI_PRACTICE_PILOT", "scope": "FULL_CLOSED_PILOT"},
        ]
    if subject.content_type == "EXERCISE_SET":
        return [{"target_milestone": "M7", "artifact_kind": "EXERCISE_SET", "scope": "SUBJECT_LESSON", "lesson_id": subject.lesson_id}]
    return [{"target_milestone": "M8_2", "artifact_kind": "AI_PRACTICE_PILOT", "scope": "FULL_CLOSED_PILOT"}]


def _repair_requirement(finding: Mapping[str, Any]) -> str:
    description = str(finding["description"])
    recommendation = finding.get("recommendation")
    if isinstance(recommendation, str) and recommendation:
        return f"Resolve the reported defect exactly: {description} Required repair: {recommendation}"
    return f"Resolve the reported defect exactly: {description}"


def _validate_source_input(input_id: str, value: Mapping[str, Any], subject: ReviewSubject) -> None:
    validate_instance(dict(value), "m10-review-input")
    if input_id != value.get("input_id") or input_id != identity("m10input", value, "input_id"):
        raise ValueError(f"M10 review-input identity drift: {input_id}")
    if value.get("promotion_status") != "NON_PROMOTABLE" or value.get("evidence_purpose") != "M10_REVISION_INPUT":
        raise ValueError(f"M10 review input is not non-promotable revision evidence: {input_id}")
    if value.get("subject_id") != subject.subject_id or value.get("artifact_sha256") != subject.artifact_sha256:
        raise ValueError(f"M10 review-input subject binding drift: {input_id}")
    if value.get("content_type") != subject.content_type or value.get("modality") != subject.modality:
        raise ValueError(f"M10 review-input subject type drift: {input_id}")
    findings = value.get("findings")
    if not isinstance(findings, list) or not findings:
        raise ValueError(f"M10 revision planning requires at least one verbatim finding: {input_id}")


def build_revision_requests(
    *,
    review_inputs: Mapping[str, Mapping[str, Any]] | Iterable[Mapping[str, Any]],
    subjects: Mapping[str, ReviewSubject] | Iterable[ReviewSubject],
) -> tuple[JsonObject, ...]:
    """Group validated non-promotable M9 findings and build one request per subject.

    This function creates planning records only. It neither modifies predecessors nor
    invokes any M6, M7, or M8.2 generation path.
    """
    subject_by_id = dict(subjects) if isinstance(subjects, Mapping) else {item.subject_id: item for item in subjects}
    if len(subject_by_id) == 0:
        raise ValueError("M10 revision planning requires ReviewSubjects")
    if isinstance(review_inputs, Mapping):
        input_items = list(review_inputs.items())
    else:
        input_items = [(str(item.get("input_id")), item) for item in review_inputs]
    if not input_items:
        raise ValueError("M10 revision planning requires review-input records")

    grouped: dict[str, list[tuple[str, Mapping[str, Any]]]] = defaultdict(list)
    seen_input_ids: set[str] = set()
    for input_id, value in input_items:
        if input_id in seen_input_ids:
            raise ValueError(f"duplicate M10 review-input ID: {input_id}")
        seen_input_ids.add(input_id)
        subject_id = str(value.get("subject_id"))
        subject = subject_by_id.get(subject_id)
        if subject is None:
            raise ValueError(f"M10 review input refers to an unavailable ReviewSubject: {input_id}")
        if subject.content_type not in _TARGETS:
            raise ValueError(f"unsupported M10 ReviewSubject content type: {subject.content_type}")
        _validate_source_input(input_id, value, subject)
        grouped[subject_id].append((input_id, value))

    requests: list[JsonObject] = []
    for subject_id in sorted(grouped):
        subject = subject_by_id[subject_id]
        ordered_inputs = sorted(grouped[subject_id], key=lambda item: item[0])
        source_inputs: list[JsonObject] = []
        findings: list[JsonObject] = []
        constraints: list[JsonObject] = []
        finding_checks: list[JsonObject] = []
        for input_id, input_value in ordered_inputs:
            input_sha256 = sha256_json(input_value)
            role = str(input_value["review_role"])
            source_inputs.append({"input_id": input_id, "input_sha256": input_sha256, "review_role": role})
            for finding_index, finding in enumerate(input_value["findings"]):
                verbatim_finding = copy.deepcopy(dict(finding))
                findings.append({
                    "source_input_id": input_id,
                    "source_input_sha256": input_sha256,
                    "review_role": role,
                    "finding_index": finding_index,
                    "finding": verbatim_finding,
                })
                constraints.append({
                    "source_input_id": input_id,
                    "finding_index": finding_index,
                    "requirement": _repair_requirement(verbatim_finding),
                    "scope_boundary": _SCOPE_BOUNDARIES[subject.content_type],
                })
                finding_checks.append({
                    "check_code": "SOURCE_FINDING_RESOLVED",
                    "source_input_id": input_id,
                    "finding_index": finding_index,
                    "requirement": f"Independent re-review confirms this exact reported defect is absent from the successor: {verbatim_finding['description']}",
                })

        value: JsonObject = {
            "schema_version": "1.0",
            "record_type": "m10_revision_request",
            "request_id": "PENDING",
            "source_milestone": "M9",
            "target_milestone": _TARGETS[subject.content_type],
            "revision_number": 2,
            "subject_id": subject.subject_id,
            "content_type": subject.content_type,
            "lesson_id": subject.lesson_id,
            "predecessor": {
                "artifact_path": subject.artifact_path,
                "artifact_sha256": subject.artifact_sha256,
                "audit_path": subject.audit_path,
                "audit_sha256": subject.audit_sha256,
            },
            "source_inputs": source_inputs,
            "findings": findings,
            "repair_constraints": constraints,
            "acceptance_checks": finding_checks + [
                {"check_code": code, "requirement": requirement}
                for code, requirement in _TARGET_CHECKS[subject.content_type]
            ],
            "rebuild_closure": _rebuild_closure(subject),
            "planning_only": True,
            "successor_created": False,
            "lifecycle_transition_authorized": False,
            "approval_claim_authorized": False,
            "content_lifecycle_status": "UNREVIEWED",
            "development_approved": False,
        }
        if subject.modality is not None:
            value["modality"] = subject.modality
        value["request_id"] = identity("m10request", value, "request_id")
        validate_instance(value, "m10-revision-request")
        requests.append(value)
    return tuple(requests)
