"""M9 development decision construction."""
from __future__ import annotations

from typing import Any, Mapping, Sequence

from english_master.lesson_generation.canonical import identity, sha256_json
from english_master.schema_validation import validate_instance

from .authority import VerifiedM9Authority
from .machine import build_machine_report
from .review import CHECKLISTS, parse_orderable_timestamp, validate_ai_review
from .selection import build_selection

JsonObject = dict[str, Any]


def build_development_batch(
    authority: VerifiedM9Authority,
    selection: Mapping[str, Any],
    machine_reports: Mapping[str, Mapping[str, Any]],
    ai_reviews: Mapping[tuple[str, str], Mapping[str, Any]],
    *,
    created_at: str,
    inventory: Sequence[Mapping[str, Any]],
) -> JsonObject:
    """Build the M9 development overlay after full fresh evidence is supplied."""
    expected_selection = build_selection(authority, created_at=selection.get("created_at"))
    if dict(selection) != expected_selection:
        raise ValueError("M9 development batch requires a reconstructable selection manifest")
    selection_at = parse_orderable_timestamp(selection.get("created_at"))
    batch_at = parse_orderable_timestamp(created_at)
    if selection_at is None or batch_at is None or batch_at < selection_at:
        raise ValueError("M9 development batch has invalid chronology")
    entries: list[JsonObject] = []
    for subject in authority.subjects:
        report = machine_reports.get(subject.subject_id)
        if report is None:
            raise ValueError(f"missing M9 machine report: {subject.subject_id}")
        expected_report = build_machine_report(authority, selection, subject, reviewed_at=report.get("reviewed_at"))
        if dict(report) != expected_report or report.get("result") != "PASS":
            raise ValueError(f"M9 machine report is not a passing reconstruction: {subject.subject_id}")
        review_refs: list[JsonObject] = []
        executions: set[str] = set()
        responses: set[str] = set()
        for role in CHECKLISTS:
            review = ai_reviews.get((subject.subject_id, role))
            if review is None:
                raise ValueError(f"missing M9 {role} review: {subject.subject_id}")
            issues = validate_ai_review(review, selection=selection, subject=subject, machine_report=report)
            if issues:
                raise ValueError(f"invalid M9 AI review {subject.subject_id}/{role}: {', '.join(issues)}")
            review_at = parse_orderable_timestamp(review.get("reviewed_at"))
            if review_at is None or batch_at < review_at:
                raise ValueError(f"M9 development batch predates AI review: {subject.subject_id}/{role}")
            capture = review["capture"]
            execution = str(capture["execution_id"])
            response_hash = str(review["raw_response_sha256"])
            if execution in executions or response_hash in responses:
                raise ValueError(f"M9 review roles require distinct capture evidence: {subject.subject_id}")
            executions.add(execution)
            responses.add(response_hash)
            review_refs.append({"review_role": role, "path": f"reviews/{subject.subject_id.split('_', 1)[1][:16]}--{role.lower()}.json", "sha256": sha256_json(review)})
        entries.append({"subject_id": subject.subject_id, "machine_report_path": f"machine/{subject.subject_id.split('_', 1)[1][:16]}.json", "machine_report_sha256": sha256_json(report), "ai_reviews": review_refs})
    batch: JsonObject = {
        "schema_version": "1.0", "record_type": "m9_development_batch", "batch_id": "PENDING",
        "selection_id": selection["selection_id"], "selection_sha256": sha256_json(selection),
        "approval_tier": "DEVELOPMENT_APPROVED", "content_lifecycle_status": "UNREVIEWED", "human_reviewed": False,
        "release_approved": False, "provider_authenticated": False, "created_at": created_at, "subjects": entries,
        "aggregate_report": {"selection_scope": "REPRESENTATIVE_SAMPLE", "selected_subject_count": 18, "machine_pass_count": 18, "ai_review_count": 36, "blocking_finding_count": 0, "unreviewed_outside_sample": True},
        "limitations": ["This DEVELOPMENT_APPROVED overlay covers only the declared representative sample.", "Underlying artifacts remain UNREVIEWED.", "No human review, release approval, provider authentication, live-provider behavior, or Internet-wide originality search is claimed."],
        "inventory": [dict(item) for item in inventory],
    }
    batch["batch_id"] = identity("m9devbatch", batch, "batch_id")
    validate_instance(batch, "m9-development-batch")
    return batch
