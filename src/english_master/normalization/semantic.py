"""Human semantic-review boundary; no automatic semantic inference."""

from __future__ import annotations

from datetime import datetime

from english_master.normalization.hashes import canonical_json_bytes, sha256_bytes
from english_master.normalization.models import ReviewDisposition
from english_master.schema_validation import validate_instance


def create_review_decision(
    *,
    candidate_id: str,
    disposition: ReviewDisposition | str,
    relationship: str,
    reviewer: str,
    reviewed_at: datetime,
    reason: str,
    evidence: list[str] | tuple[str, ...],
) -> dict[str, object]:
    """Create an auditable human decision for an existing similarity candidate."""

    try:
        decision = ReviewDisposition(disposition)
    except ValueError as error:
        raise ValueError("Unsupported review disposition; automatic merge states are forbidden") from error
    if relationship not in {"PARAPHRASE", "TRANSLATION", "OTHER"}:
        raise ValueError("relationship must be PARAPHRASE, TRANSLATION, or OTHER")
    if reviewed_at.tzinfo is None or reviewed_at.utcoffset() is None:
        raise ValueError("reviewed_at must include a timezone")
    if not reviewer.strip() or not reason.strip():
        raise ValueError("reviewer and reason must be nonempty")
    if not evidence or any(not item.strip() for item in evidence):
        raise ValueError("at least one nonempty evidence item is required")
    timestamp = reviewed_at.isoformat().replace("+00:00", "Z")
    material = {
        "candidate_id": candidate_id,
        "disposition": decision.value,
        "reviewer": reviewer,
        "reviewed_at": timestamp,
    }
    return {
        "schema_version": "1.0",
        "record_type": "semantic_review_decision",
        "id": f"review_{sha256_bytes(canonical_json_bytes(material))[:20]}",
        "candidate_id": candidate_id,
        "disposition": decision.value,
        "relationship": relationship,
        "reviewer": reviewer,
        "reviewed_at": timestamp,
        "reason": reason,
        "evidence": list(evidence),
        "decision_method": "HUMAN_REVIEW",
    }


def validate_review_decisions(
    decisions: list[dict[str, object]] | tuple[dict[str, object], ...],
    candidate_ids: set[str],
) -> None:
    """Validate decision shape, identity uniqueness, and candidate references."""

    seen_ids: set[str] = set()
    decided_candidates: set[str] = set()
    for decision in decisions:
        validate_instance(decision, "semantic-review")
        decision_id = str(decision["id"])
        candidate_id = str(decision["candidate_id"])
        if decision_id in seen_ids:
            raise ValueError(f"Duplicate semantic review decision ID: {decision_id}")
        if candidate_id in decided_candidates:
            raise ValueError(f"Multiple semantic review decisions for candidate: {candidate_id}")
        if candidate_id not in candidate_ids:
            raise ValueError(f"Semantic review decision references unknown candidate: {candidate_id}")
        seen_ids.add(decision_id)
        decided_candidates.add(candidate_id)


def build_review_queue(candidates: tuple[dict[str, object], ...]) -> dict[str, object]:
    """Build a deterministic queue without guessing semantic equivalence."""

    candidate_ids = sorted(str(candidate["id"]) for candidate in candidates)
    queue_hash = sha256_bytes(canonical_json_bytes(candidate_ids))
    return {
        "schema_version": "1.0",
        "record_type": "semantic_review_queue",
        "id": f"queue_{queue_hash[:20]}",
        "candidate_ids": candidate_ids,
        "status": "REVIEW_REQUIRED" if candidate_ids else "EMPTY",
    }
