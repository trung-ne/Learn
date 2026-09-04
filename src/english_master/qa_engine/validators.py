"""Deterministic QA-stage adapters for immutable M7 exercise-set candidates."""
from __future__ import annotations

import copy
from typing import Any, Mapping, Sequence

from english_master.exercise_generation.builders import build_authorization, build_request
from english_master.exercise_generation.validator import assembled_issues, candidate_semantic_issues
from english_master.schema_validation import validation_issues

from .authority import VerifiedM7QaAuthority
from .models import QaIssue
from .projection import is_near_duplicate, projection_hash


def _issue(code: str, path: str, message: str, severity: str = "MAJOR") -> QaIssue:
    return QaIssue(code, path, message, severity)


def schema_issues(candidate: Mapping[str, Any], authority: VerifiedM7QaAuthority, lesson_id: str) -> tuple[QaIssue, ...]:
    issues = [_issue("SCHEMA_INVALID", item.instance_path, item.message) for item in validation_issues(dict(candidate), "exercise-set")]
    if issues:
        return tuple(sorted(set(issues)))
    issues.extend(_issue(f"SET_{item.code}", item.path, item.message) for item in assembled_issues({}, candidate))
    try:
        expected = authority.m6.binding(lesson_id)
        expected_set, _, _ = authority.artifacts(lesson_id)
    except (KeyError, TypeError, ValueError) as error:
        return tuple(sorted(set(issues + [_issue("AUTHORITY_INVALID", "$.lesson_id", str(error), "CRITICAL")])))
    if candidate.get("request_id") != expected_set.get("request_id"):
        issues.append(_issue("M7_REQUEST_BINDING_MISMATCH", "$.request_id", "candidate must retain the verified M7 request binding", "CRITICAL"))
    metadata = candidate.get("generation_metadata")
    if not isinstance(metadata, Mapping) or metadata.get("qa_status") != "UNREVIEWED":
        issues.append(_issue("SET_GENERATION_STATUS_INVALID", "$.generation_metadata.qa_status", "QA engine never accepts pre-approved generated content", "CRITICAL"))
    for index, exercise in enumerate(candidate.get("exercises", []), 1):
        if not isinstance(exercise, Mapping) or exercise.get("id") != f"ex_{lesson_id}_{index:03d}":
            issues.append(_issue("EXERCISE_ID_INVALID", f"$.exercises[{index - 1}].id", "exercise ID must be deterministic for the verified lesson and sequence", "CRITICAL"))
    if candidate.get("lesson_id") != lesson_id or candidate.get("lesson_sha256") != expected["lesson_sha256"]:
        issues.append(_issue("LESSON_BINDING_MISMATCH", "$.lesson_id", "candidate must bind the verified lesson", "CRITICAL"))
    if candidate.get("m6_batch_id") != authority.m6.batch["batch_id"]:
        issues.append(_issue("M6_BATCH_BINDING_MISMATCH", "$.m6_batch_id", "candidate must bind the verified M6 batch", "CRITICAL"))
    if candidate.get("status") != "UNREVIEWED":
        issues.append(_issue("CONTENT_STATUS_INVALID", "$.status", "QA engine never accepts pre-approved content", "CRITICAL"))
    for index, exercise in enumerate(candidate.get("exercises", [])):
        exercise_metadata = exercise.get("generation_metadata") if isinstance(exercise, Mapping) else None
        if not isinstance(exercise, Mapping) or not isinstance(exercise_metadata, Mapping) or exercise_metadata.get("qa_status") != "UNREVIEWED":
            issues.append(_issue("EXERCISE_STATUS_INVALID", f"$.exercises[{index}].generation_metadata.qa_status", "QA engine never accepts pre-approved exercise content", "CRITICAL"))
    return tuple(sorted(set(issues)))


def regeneration_evidence_issues(invocation: Mapping[str, Any]) -> tuple[QaIssue, ...]:
    """Return the fixed non-promotable-capture findings for a retry invocation."""
    issues: list[QaIssue] = []
    if invocation.get("capture_mode") not in {"SESSION_CAPTURED", "PROVIDER_CAPTURED"}:
        issues.append(
            _issue(
                "REGENERATION_EVIDENCE_NOT_PROMOTABLE",
                "$.generation_provenance.capture_mode",
                "replay, test, mock, or unsupported regeneration evidence cannot support development promotion",
                "CRITICAL",
            )
        )
    if invocation.get("parameters_match") is not True:
        issues.append(
            _issue(
                "CAPTURE_PARAMETERS_MISMATCH",
                "$.generation_provenance.invocation_id",
                "captured generation parameters differ from the trusted invocation parameters",
                "CRITICAL",
            )
        )
    if invocation.get("reported_provider_authenticated") is True:
        issues.append(
            _issue(
                "UNVERIFIED_PROVIDER_AUTHENTICATION_CLAIM",
                "$.generation_provenance.invocation_id",
                "backend-reported provider authentication is retained but not trusted by M8",
                "CRITICAL",
            )
        )
    return tuple(issues)


_ANSWER_PREFIXES = (
    "TYPE_CONTRACT", "MCQ", "FILL_", "MATCHING", "ORDERING",
    "ERROR_CORRECTION", "TRANSLATION", "COMPREHENSION_", "SUBJECTIVE",
    "UNSUPPORTED_MEDIA", "EXTERNAL_STIMULUS", "TYPE_LIMIT", "SIZE_LIMIT",
    "LATER_MILESTONE_SCOPE_LEAKAGE", "M8_LEAKAGE", "FORBIDDEN_TERM",
)
_PREREQUISITE_PREFIXES = ("REFERENCE_SCOPE", "TARGET_REVIEW", "OBJECTIVE_ALIGNMENT")
_DUPLICATE_CODES = {"DUPLICATE_EXERCISE"}


def _semantic(candidate: Mapping[str, Any], authority: VerifiedM7QaAuthority, lesson_id: str) -> tuple[QaIssue, ...]:
    request = build_request(authority.m6, build_authorization(authority.m6), lesson_id).as_dict()
    raw = {
        "items": [
            {key: copy.deepcopy(item[key]) for key in ("title", "exercise_type", "difficulty", "instructions", "objective_indices", "target_references", "review_references", "scoring_mode", "payload") if key in item}
            for item in candidate.get("exercises", []) if isinstance(item, Mapping)
        ]
    }
    return tuple(_issue(item.code, item.path, item.message) for item in candidate_semantic_issues(request, raw))


def answer_issues(candidate: Mapping[str, Any], authority: VerifiedM7QaAuthority, lesson_id: str) -> tuple[QaIssue, ...]:
    semantic = _semantic(candidate, authority, lesson_id)
    known = tuple(
        item
        for item in semantic
        if item.code.startswith(_ANSWER_PREFIXES)
        or item.code.startswith(_PREREQUISITE_PREFIXES)
        or item.code in _DUPLICATE_CODES
    )
    unassigned = tuple(
        _issue(
            "SEMANTIC_QA_CODE_UNASSIGNED",
            item.path,
            f"unassigned M7 semantic QA code: {item.code}",
            "CRITICAL",
        )
        for item in semantic
        if item not in known
    )
    return tuple(item for item in known if item.code.startswith(_ANSWER_PREFIXES)) + unassigned


def cefr_issues(candidate: Mapping[str, Any], authority: VerifiedM7QaAuthority, lesson_id: str) -> tuple[QaIssue, ...]:
    lesson = authority.m6.lesson(lesson_id)
    return tuple(
        _issue("CEFR_MISMATCH", f"$.exercises[{index}].cefr_level", "exercise CEFR must equal its verified lesson CEFR")
        for index, item in enumerate(candidate.get("exercises", []))
        if not isinstance(item, Mapping) or item.get("cefr_level") != lesson["cefr_level"]
    )


def prerequisite_issues(candidate: Mapping[str, Any], authority: VerifiedM7QaAuthority, lesson_id: str) -> tuple[QaIssue, ...]:
    return tuple(
        item
        for item in _semantic(candidate, authority, lesson_id)
        if item.code.startswith(_PREREQUISITE_PREFIXES)
    )


def duplicate_issues(
    candidate: Mapping[str, Any],
    authority: VerifiedM7QaAuthority,
    lesson_id: str,
    prior_candidates: Sequence[Mapping[str, Any]],
) -> tuple[QaIssue, ...]:
    semantic = tuple(
        item
        for item in _semantic(candidate, authority, lesson_id)
        if item.code == "DUPLICATE_EXERCISE"
    )
    repeated: list[QaIssue] = []
    current_hash = projection_hash(candidate)
    for index, prior in enumerate(prior_candidates, 1):
        if current_hash == projection_hash(prior):
            repeated.append(
                _issue(
                    "DUPLICATE_REGENERATION",
                    "$.exercises",
                    f"learner-facing content is unchanged from attempt {index}",
                )
            )
            break
        if is_near_duplicate(candidate, prior):
            repeated.append(
                _issue(
                    "NEAR_DUPLICATE_REGENERATION",
                    "$.exercises",
                    f"normalized learner-facing content is materially unchanged from attempt {index}",
                )
            )
            break
    return tuple(sorted(set(semantic + tuple(repeated))))
