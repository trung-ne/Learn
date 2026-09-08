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
    all_executions: set[str] = set()
    all_responses: set[str] = set()
    for subject in authority.subjects:
        report = machine_reports.get(subject.subject_id)
        if report is None:
            raise ValueError(f"missing M9 machine report: {subject.subject_id}")
        expected_report = build_machine_report(authority, selection, subject, reviewed_at=report.get("reviewed_at"))
        if dict(report) != expected_report or report.get("result") != "PASS":
            raise ValueError(f"M9 machine report is not a passing reconstruction: {subject.subject_id}")
        review_refs: list[JsonObject] = []
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
            if execution in all_executions or response_hash in all_responses:
                raise ValueError("M9 full-population reviews require globally distinct execution IDs and raw responses")
            all_executions.add(execution)
            all_responses.add(response_hash)
            token = subject.subject_id.split("_", 1)[1]
            review_refs.append({"review_role": role, "path": f"reviews/{token}--{role.lower()}.json", "sha256": sha256_json(review)})
        token = subject.subject_id.split("_", 1)[1]
        entries.append({"subject_id": subject.subject_id, "machine_report_path": f"machine/{token}.json", "machine_report_sha256": sha256_json(report), "ai_reviews": review_refs})
    batch: JsonObject = {
        "schema_version": "2.0", "record_type": "m9_development_batch", "batch_id": "PENDING",
        "selection_id": selection["selection_id"], "selection_sha256": sha256_json(selection),
        "approval_tier": "DEVELOPMENT_APPROVED", "content_lifecycle_status": "UNREVIEWED",
        "created_at": created_at, "subjects": entries,
        "aggregate_report": {
            "selection_scope": "FULL_POPULATION",
            "selected_subject_count": len(entries),
            "machine_pass_count": len(entries),
            "ai_review_count": len(entries) * len(CHECKLISTS),
            "blocking_finding_count": 0,
            "unreviewed_outside_selection": False,
        },
        "limitations": [
            "This DEVELOPMENT_APPROVED evidence covers the complete declared current population; it does not change artifact lifecycle status.",
            "Underlying artifacts remain UNREVIEWED.",
            "No human review, release approval, provider authentication, live-provider behavior, or Internet-wide originality search is claimed.",
        ],
        "inventory": [dict(item) for item in inventory],
    }
    batch["batch_id"] = identity("m9devbatch", batch, "batch_id")
    validate_instance(batch, "m9-development-batch-v2")
    return batch
