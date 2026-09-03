"""Validation contracts for independent M6 lesson review and batch QA evidence."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Any, Mapping

from english_master.schema_validation import validation_issues

from .authority import VerifiedM5Authority
from .canonical import identity, sha256_json
from .models import GenerationIssue, JsonObject

CHECKLIST_BY_ROLE = {
    "LINGUISTIC": {"CEFR_ALIGNMENT", "GRAMMAR_LEXICAL_ACCURACY", "LANGUAGE_QUALITY", "PREREQUISITE_SCOPE", "COPYRIGHT_SPOT_CHECK"},
    "PEDAGOGICAL": {"CEFR_ALIGNMENT", "LANGUAGE_QUALITY", "PEDAGOGICAL_SOUNDNESS", "PREREQUISITE_SCOPE", "COPYRIGHT_SPOT_CHECK"},
}


def _issue(code: str, path: str, message: str) -> GenerationIssue:
    return GenerationIssue(code, path, message)


def _schema_issues(value: Mapping[str, Any], schema: str) -> list[GenerationIssue]:
    return [_issue("REVIEW_SCHEMA", item.instance_path, item.message) for item in validation_issues(dict(value), schema)]


def _parse_timestamp(value: Any) -> datetime | None:
    if not isinstance(value, str):
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None


def validate_lesson_review(
    review: Mapping[str, Any],
    lesson: Mapping[str, Any],
    audit: Mapping[str, Any],
    m5: VerifiedM5Authority,
) -> tuple[GenerationIssue, ...]:
    """Validate a human review without treating it as content approval."""

    issues = _schema_issues(review, "lesson-independent-review")
    if issues:
        return tuple(sorted(set(issues)))
    if review["lesson_review_id"] != identity("m6review", review, "lesson_review_id"):
        issues.append(_issue("REVIEW_ID_MISMATCH", "$.lesson_review_id", "must be the canonical review identity"))
    if lesson.get("id") != review["lesson_id"]:
        issues.append(_issue("LESSON_BINDING_MISMATCH", "$.lesson_id", "does not name the independently loaded lesson"))
    if sha256_json(lesson) != review["lesson_sha256"]:
        issues.append(_issue("LESSON_HASH_MISMATCH", "$.lesson_sha256", "does not bind the complete lesson record"))
    if sha256_json(audit) != review["audit_sha256"]:
        issues.append(_issue("AUDIT_HASH_MISMATCH", "$.audit_sha256", "does not bind the complete automated audit"))
    if audit.get("status") != "ACCEPTED" or audit.get("qa_status") != "UNREVIEWED":
        issues.append(_issue("AUDIT_NOT_REVIEWABLE", "$.audit", "only accepted UNREVIEWED automated output may be independently reviewed"))
    if lesson.get("generation_metadata", {}).get("qa_status") != "UNREVIEWED":
        issues.append(_issue("LESSON_NOT_UNREVIEWED", "$.lesson.generation_metadata.qa_status", "review does not mutate or approve the lesson record"))
    expected_binding = m5.snapshot_binding()
    if review["snapshot_binding"] != expected_binding or audit.get("snapshot_binding") != expected_binding:
        issues.append(_issue("SNAPSHOT_BINDING_MISMATCH", "$.snapshot_binding", "review and audit must bind the independently reverified M5 snapshot"))

    reviewer = review["reviewer"]
    registry_reviewers = m5.reviewer_registry.get("reviewers", [])
    registered = next((entry for entry in registry_reviewers if isinstance(entry, Mapping) and entry.get("reviewer_id") == reviewer["reviewer_id"]), None) if isinstance(registry_reviewers, list) else None
    if registered is None:
        issues.append(_issue("REVIEWER_NOT_TRUSTED", "$.reviewer.reviewer_id", "reviewer is absent from the independently loaded registry"))
    else:
        if registered.get("status") != "VERIFIED" or review["review_role"] not in registered.get("permitted_roles", []):
            issues.append(_issue("REVIEWER_NOT_AUTHORIZED", "$.reviewer", "trusted reviewer is not verified for this review role"))
        evidence = registered.get("identity_evidence", {})
        for field in ("display_name", "qualifications"):
            if reviewer[field] != registered.get(field):
                issues.append(_issue("REVIEWER_IDENTITY_MISMATCH", f"$.reviewer.{field}", "must match the trusted registry"))
        if reviewer["identity_evidence_id"] != evidence.get("evidence_id"):
            issues.append(_issue("REVIEWER_IDENTITY_MISMATCH", "$.reviewer.identity_evidence_id", "must match trusted identity evidence"))

    checklist = review["checklist"]
    criteria = [entry["criterion"] for entry in checklist]
    expected_criteria = CHECKLIST_BY_ROLE[review["review_role"]]
    if set(criteria) != expected_criteria or len(criteria) != len(set(criteria)):
        issues.append(_issue("CHECKLIST_SCOPE_MISMATCH", "$.checklist", "must contain each role-specific criterion exactly once"))
    findings = review["findings"]
    has_blocking = any(item["severity"] in {"MAJOR", "CRITICAL"} for item in findings)
    has_failure = any(item["result"] == "FAIL" for item in checklist)
    if review["decision"] == "APPROVE" and (has_blocking or has_failure):
        issues.append(_issue("REVIEW_DECISION_MISMATCH", "$.decision", "approval cannot contain failing checks or major/critical findings"))
    if review["decision"] != "APPROVE" and not (has_blocking or has_failure):
        issues.append(_issue("REVIEW_DECISION_MISMATCH", "$.decision", "non-approval requires a recorded failure or blocking finding"))
    spot_check = review["copyright_spot_check"]
    if spot_check["result"] == "NOT_PERFORMED" and review["decision"] == "APPROVE":
        issues.append(_issue("COPYRIGHT_SPOT_CHECK_INCOMPLETE", "$.copyright_spot_check", "approval requires a truthful completed spot check"))
    reviewed_at, qa_at = _parse_timestamp(review["reviewed_at"]), _parse_timestamp(audit.get("qa_timestamp"))
    if reviewed_at is None or qa_at is None or reviewed_at < qa_at:
        issues.append(_issue("REVIEW_CHRONOLOGY_INVALID", "$.reviewed_at", "review timestamp must be at or after the automated audit timestamp"))
    return tuple(sorted(set(issues)))


def validate_batch_report(
    report: Mapping[str, Any],
    m5: VerifiedM5Authority,
    bundle_root: Path,
) -> tuple[GenerationIssue, ...]:
    """Fail closed on ten ordered immutable bundles and their declared review sample."""

    issues = _schema_issues(report, "lesson-batch-qa-report")
    if issues:
        return tuple(sorted(set(issues)))
    if report["batch_id"] != identity("m6batch", report, "batch_id"):
        issues.append(_issue("BATCH_ID_MISMATCH", "$.batch_id", "must be the canonical batch identity"))
    if report["snapshot_binding"] != m5.snapshot_binding():
        issues.append(_issue("SNAPSHOT_BINDING_MISMATCH", "$.snapshot_binding", "must bind the independently reverified M5 snapshot"))
    lesson_ids = [record["lesson_id"] for record in report["lesson_bundles"]]
    if len(lesson_ids) != len(set(lesson_ids)):
        issues.append(_issue("DUPLICATE_LESSON", "$.lesson_bundles", "batch lesson IDs must be distinct"))
    order = {lesson_id: index for index, lesson_id in enumerate(
        sorted(
            (node["id"] for node in m5.bundle.graph.get("nodes", []) if isinstance(node, Mapping) and node.get("type") == "lesson"),
            key=lambda lesson_id: next(node.get("sequence_key", "") for node in m5.bundle.graph["nodes"] if node.get("id") == lesson_id),
        )
    )}
    if lesson_ids != sorted(lesson_ids, key=lambda value: order.get(value, float("inf"))):
        issues.append(_issue("LESSON_ORDER_MISMATCH", "$.lesson_bundles", "bundles must be in authoritative graph order"))
    resolved_root = bundle_root.resolve()
    reviewed_ids: set[str] = set()
    for index, record in enumerate(report["lesson_bundles"]):
        path = (resolved_root / record["bundle_path"]).resolve()
        if resolved_root not in path.parents:
            issues.append(_issue("BUNDLE_PATH_ESCAPE", f"$.lesson_bundles[{index}].bundle_path", "bundle path escapes the declared root"))
            continue
        try:
            from english_master.curriculum_review.loading import load_strict_document
            lesson = load_strict_document(path / "lesson.json")
            audit = load_strict_document(path / "audit.json")
        except (OSError, ValueError, TypeError) as error:
            issues.append(_issue("BUNDLE_UNAVAILABLE", f"$.lesson_bundles[{index}]", f"immutable bundle cannot be loaded: {type(error).__name__}"))
            continue
        if lesson.get("id") != record["lesson_id"] or sha256_json(lesson) != record["lesson_sha256"] or sha256_json(audit) != record["audit_sha256"]:
            issues.append(_issue("BUNDLE_HASH_MISMATCH", f"$.lesson_bundles[{index}]", "bundle identity or hash differs from the report"))
        if audit.get("status") != "ACCEPTED" or audit.get("snapshot_binding") != m5.snapshot_binding():
            issues.append(_issue("BUNDLE_NOT_ACCEPTED", f"$.lesson_bundles[{index}]", "bundle is not accepted automated M6 output for this snapshot"))
    for index, record in enumerate(report["review_records"]):
        path = (resolved_root / record["review_path"]).resolve()
        if resolved_root not in path.parents:
            issues.append(_issue("REVIEW_PATH_ESCAPE", f"$.review_records[{index}].review_path", "review path escapes the declared root"))
            continue
        try:
            from english_master.curriculum_review.loading import load_strict_document
            review = load_strict_document(path)
        except (OSError, ValueError, TypeError) as error:
            issues.append(_issue("REVIEW_UNAVAILABLE", f"$.review_records[{index}]", f"review cannot be loaded: {type(error).__name__}"))
            continue
        if review.get("lesson_review_id") != record["lesson_review_id"] or review.get("lesson_id") != record["lesson_id"] or sha256_json(review) != record["review_sha256"]:
            issues.append(_issue("REVIEW_HASH_MISMATCH", f"$.review_records[{index}]", "review identity or hash differs from the report"))
        reviewed_ids.add(record["lesson_id"])
    if not set(report["human_review_sample"]).issubset(reviewed_ids):
        issues.append(_issue("HUMAN_SAMPLE_MISSING", "$.human_review_sample", "every declared human-review sample lesson needs a referenced review record"))
    return tuple(sorted(set(issues)))
