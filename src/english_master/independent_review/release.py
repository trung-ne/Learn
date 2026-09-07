"""Optional M9 qualified-human and release-lane validation."""
from __future__ import annotations

from datetime import datetime
from typing import Any, Mapping, Sequence

from english_master.lesson_generation.canonical import identity, sha256_json
from english_master.schema_validation import validate_instance

JsonObject = dict[str, Any]


def _time(value: Any) -> datetime | None:
    if not isinstance(value, str):
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None


def validate_human_review(review: Mapping[str, Any], development_batch: Mapping[str, Any], registry: Mapping[str, Any]) -> tuple[str, ...]:
    """Validate real registry-bound human evidence; AI records never satisfy it."""
    issues: list[str] = []
    try:
        validate_instance(dict(review), "m9-human-review")
    except ValueError as error:
        return (f"SCHEMA: {error}",)
    if review.get("review_id") != identity("m9humanreview", review, "review_id"):
        issues.append("REVIEW_ID")
    if review.get("development_batch_id") != development_batch.get("batch_id") or review.get("development_batch_sha256") != sha256_json(development_batch):
        issues.append("DEVELOPMENT_BINDING")
    reviewer = review.get("reviewer", {})
    registered = next((item for item in registry.get("reviewers", []) if isinstance(item, Mapping) and item.get("reviewer_id") == reviewer.get("reviewer_id")), None)
    if not isinstance(registered, Mapping):
        issues.append("REVIEWER_NOT_REGISTERED")
    else:
        evidence = registered.get("identity_evidence", {})
        if registered.get("status") != "VERIFIED" or review.get("review_role") not in registered.get("permitted_roles", []):
            issues.append("REVIEWER_NOT_AUTHORIZED")
        if reviewer.get("display_name") != registered.get("display_name") or reviewer.get("qualifications") != registered.get("qualifications") or reviewer.get("identity_evidence_id") != evidence.get("evidence_id"):
            issues.append("REVIEWER_IDENTITY_MISMATCH")
    if review.get("decision") != "APPROVE" or any(item.get("result") == "FAIL" for item in review.get("checklist", []) if isinstance(item, Mapping)) or any(item.get("severity") in {"MAJOR", "CRITICAL"} for item in review.get("findings", []) if isinstance(item, Mapping)):
        issues.append("HUMAN_DECISION")
    review_at, development_at = _time(review.get("reviewed_at")), _time(development_batch.get("created_at"))
    if review_at is None or development_at is None or review_at < development_at:
        issues.append("CHRONOLOGY")
    return tuple(sorted(set(issues)))


def build_human_review_batch(development_batch: Mapping[str, Any], registry: Mapping[str, Any], reviews: Sequence[Mapping[str, Any]], *, created_at: str) -> JsonObject:
    """Build a HUMAN_REVIEWED overlay only from two genuine distinct people."""
    roles: set[str] = set()
    subjects: set[tuple[Any, Any]] = set()
    refs: list[JsonObject] = []
    for review in reviews:
        issues = validate_human_review(review, development_batch, registry)
        if issues:
            raise ValueError(", ".join(issues))
        roles.add(str(review["review_role"]))
        evidence = next(item["identity_evidence"] for item in registry["reviewers"] if item["reviewer_id"] == review["reviewer"]["reviewer_id"])
        subject = (evidence["issuer"], evidence["subject_id"])
        if subject in subjects:
            raise ValueError("human linguistic and pedagogical reviewers must be distinct")
        subjects.add(subject)
        refs.append({"review_role": review["review_role"], "review_id": review["review_id"], "sha256": sha256_json(review)})
    if roles != {"LINGUISTIC", "PEDAGOGICAL"}:
        raise ValueError("both qualified human review roles are required")
    value: JsonObject = {"schema_version": "1.0", "record_type": "m9_human_review_batch", "batch_id": "PENDING", "development_batch_id": development_batch["batch_id"], "development_batch_sha256": sha256_json(development_batch), "reviewer_registry_id": registry["registry_id"], "reviewer_registry_sha256": sha256_json(registry), "reviews": sorted(refs, key=lambda item: item["review_role"]), "approval_tier": "HUMAN_REVIEWED", "created_at": created_at, "release_approved": False}
    value["batch_id"] = identity("m9humanbatch", value, "batch_id")
    validate_instance(value, "m9-human-review-batch")
    return value


def validate_release_decision(decision: Mapping[str, Any], human_batch: Mapping[str, Any]) -> tuple[str, ...]:
    """Release remains a separate event and rejects representative-only evidence."""
    try:
        validate_instance(dict(decision), "m9-release-decision")
    except ValueError as error:
        return (f"SCHEMA: {error}",)
    issues: list[str] = []
    if decision.get("decision_id") != identity("m9release", decision, "decision_id"):
        issues.append("DECISION_ID")
    if decision.get("human_review_batch_id") != human_batch.get("batch_id") or decision.get("human_review_batch_sha256") != sha256_json(human_batch):
        issues.append("HUMAN_BATCH_BINDING")
    # This M9 pass deliberately covers a representative sample, never a complete release candidate.
    issues.append("REPRESENTATIVE_SAMPLE_CANNOT_RELEASE")
    return tuple(sorted(set(issues)))
