"""M9 role-separated AI-review prompts and evidence validation."""
from __future__ import annotations

import json
from datetime import datetime
from typing import Any, Mapping

from english_master.lesson_generation.canonical import identity, sha256_json
from english_master.schema_validation import validate_instance

from .authority import ReviewSubject

JsonObject = dict[str, Any]

CHECKLISTS = {
    "LINGUISTIC_AI_REVIEWER": ("CEFR_ALIGNMENT", "LANGUAGE_ACCURACY", "TARGET_SCOPE", "ANSWER_OR_PROTOCOL_ACCURACY", "NATURALNESS", "ORIGINALITY_LIMITATIONS"),
    "PEDAGOGICAL_AI_REVIEWER": ("OBJECTIVE_ALIGNMENT", "TEACHABILITY", "PROGRESSION", "CLARITY", "COGNITIVE_LOAD", "MODALITY_APPROPRIATENESS", "VIETNAMESE_LEARNER_RELEVANCE"),
}


def build_review_prompt(role: str, subject: ReviewSubject, machine_report: Mapping[str, Any]) -> str:
    """Build a context-isolated review prompt without generator reasoning."""
    if role not in CHECKLISTS:
        raise ValueError(f"unsupported M9 AI role: {role}")
    context = {
        "subject": {"subject_id": subject.subject_id, "content_type": subject.content_type, "lesson_id": subject.lesson_id, "modality": subject.modality, "artifact": subject.artifact, "machine_audit": subject.audit},
        "m9_machine_report": machine_report,
    }
    return (
        f"You are the independent {role}. Review only this immutable M9 subject and its fresh machine report. "
        "Do not infer generator reasoning, claim human/release approval, provider authentication, live-provider behavior, or an Internet-wide originality search. "
        f"Evaluate exactly: {', '.join(CHECKLISTS[role])}. Return JSON with decision, checklist, findings, and limitations. "
        "For AI-practice prompts, evaluate static protocol wording only; do not claim observed runtime behavior.\n\n"
        + json.dumps(context, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False)
    )


def parse_orderable_timestamp(value: Any) -> datetime | None:
    """Parse one M9 orderable timestamp without silently accepting ambiguity."""
    if not isinstance(value, str):
        return None
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
    return parsed if parsed.tzinfo is not None else None


def _has_valid_review_chronology(
    selection: Mapping[str, Any], machine_report: Mapping[str, Any], review: Mapping[str, Any]
) -> bool:
    """Require actual capture observation after the frozen machine evidence."""
    capture = review.get("capture")
    if not isinstance(capture, Mapping):
        return False
    selection_at = parse_orderable_timestamp(selection.get("created_at"))
    report_at = parse_orderable_timestamp(machine_report.get("reviewed_at"))
    observed_at = parse_orderable_timestamp(capture.get("observed_at"))
    reviewed_at = parse_orderable_timestamp(review.get("reviewed_at"))
    if any(value is None for value in (selection_at, report_at, observed_at, reviewed_at)):
        return False
    try:
        return selection_at <= report_at <= observed_at <= reviewed_at
    except TypeError:
        return False


def build_ai_review(
    *,
    selection: Mapping[str, Any],
    subject: ReviewSubject,
    machine_report: Mapping[str, Any],
    role: str,
    capture: Mapping[str, Any],
    raw_response: Mapping[str, Any],
    reviewed_at: str,
) -> JsonObject:
    """Wrap one actual role-specific captured response in immutable M9 evidence."""
    prompt = build_review_prompt(role, subject, machine_report)
    value: JsonObject = {
        "schema_version": "1.0", "record_type": "m9_ai_review", "review_id": "PENDING", "approval_tier": "AI_REVIEWED",
        "selection_id": selection["selection_id"], "subject_id": subject.subject_id, "content_type": subject.content_type,
        "artifact_sha256": subject.artifact_sha256, "machine_report_sha256": sha256_json(machine_report),
        "reviewer_type": "AI", "review_role": role, "independent_of_generation": True, "capture": dict(capture),
        "review_prompt": prompt, "raw_response": dict(raw_response), "raw_response_sha256": sha256_json(raw_response),
        "decision": raw_response["decision"], "checklist": list(raw_response["checklist"]), "findings": list(raw_response["findings"]),
        "limitations": list(raw_response["limitations"]), "reviewed_at": reviewed_at, "content_lifecycle_status": "UNREVIEWED",
        "human_reviewed": False, "release_approved": False, "provider_authenticated": False,
    }
    value["review_id"] = identity("m9aireview", value, "review_id")
    validate_instance(value, "m9-ai-review")
    issues = validate_ai_review(value, selection=selection, subject=subject, machine_report=machine_report)
    if issues:
        raise ValueError("; ".join(issues))
    return value


def validate_ai_review(
    review: Mapping[str, Any],
    *,
    selection: Mapping[str, Any],
    subject: ReviewSubject,
    machine_report: Mapping[str, Any],
) -> tuple[str, ...]:
    """Reject stale, role-incomplete, non-promotable, or self-consistent fake evidence."""
    issues: list[str] = []
    try:
        validate_instance(dict(review), "m9-ai-review")
    except ValueError as error:
        return (f"SCHEMA: {error}",)
    if review.get("review_id") != identity("m9aireview", review, "review_id"):
        issues.append("REVIEW_ID")
    if review.get("selection_id") != selection.get("selection_id") or review.get("subject_id") != subject.subject_id:
        issues.append("SELECTION_BINDING")
    if review.get("artifact_sha256") != subject.artifact_sha256 or review.get("machine_report_sha256") != sha256_json(machine_report):
        issues.append("HASH_BINDING")
    if review.get("review_prompt") != build_review_prompt(str(review.get("review_role")), subject, machine_report):
        issues.append("PROMPT_RECONSTRUCTION")
    raw = review.get("raw_response")
    if not isinstance(raw, Mapping) or review.get("raw_response_sha256") != sha256_json(raw):
        issues.append("RAW_RESPONSE_HASH")
    elif any(review.get(key) != raw.get(key) for key in ("decision", "checklist", "findings", "limitations")):
        issues.append("RAW_RESPONSE_PROJECTION")
    role = review.get("review_role")
    criteria = [item.get("criterion") for item in review.get("checklist", []) if isinstance(item, Mapping)]
    if role not in CHECKLISTS or set(criteria) != set(CHECKLISTS[role]) or len(criteria) != len(set(criteria)):
        issues.append("CHECKLIST_SCOPE")
    capture = review.get("capture", {})
    if not isinstance(capture, Mapping) or capture.get("capture_mode") not in {"SESSION_CAPTURED", "PROVIDER_CAPTURED"} or capture.get("provider_authenticated") is not False:
        issues.append("CAPTURE_PROVENANCE")
    if isinstance(capture, Mapping) and (
        capture.get("capture_mode") == "TEST_ONLY"
        or str(capture.get("provider", "")).startswith("TEST_")
        or str(capture.get("model", "")).startswith("TEST_")
        or str(capture.get("execution_id", "")).startswith("test-")
    ):
        issues.append("NON_PROMOTABLE_AI_PROVENANCE")
    if review.get("decision") == "APPROVE":
        if any(item.get("result") == "FAIL" for item in review.get("checklist", []) if isinstance(item, Mapping)):
            issues.append("DECISION_CHECKLIST")
        if any(item.get("severity") in {"MAJOR", "CRITICAL"} for item in review.get("findings", []) if isinstance(item, Mapping)):
            issues.append("DECISION_FINDINGS")
    else:
        issues.append("NON_APPROVAL")
    if not _has_valid_review_chronology(selection, machine_report, review):
        issues.append("CHRONOLOGY")
    return tuple(sorted(set(issues)))
