"""Read-only M9 development-batch reconstruction."""
from __future__ import annotations

from pathlib import Path
from typing import Any, Mapping

from english_master.curriculum_review.loading import load_strict_document
from english_master.lesson_generation.canonical import sha256_json
from english_master.schema_validation import validate_instance

from .authority import VerifiedM9Authority
from .development import build_development_batch
from .machine import build_machine_report
from .review import CHECKLISTS, validate_ai_review
from .selection import build_selection

JsonObject = dict[str, Any]


def _linklike(path: Path) -> bool:
    return path.is_symlink() or getattr(path, "is_junction", lambda: False)()


def _load(path: Path) -> JsonObject:
    if _linklike(path) or not path.is_file():
        raise ValueError(f"M9 expected regular file is unavailable: {path}")
    return load_strict_document(path)


def verify_development_batch(directory: Path, authority: VerifiedM9Authority) -> JsonObject:
    """Independently reconstruct every derived M9 development assertion."""
    root = directory.resolve()
    if _linklike(root) or not root.is_dir():
        raise ValueError("M9 development batch must be a regular directory")
    selection = _load(root / "selection.json")
    expected_selection = build_selection(authority, created_at=selection.get("created_at"))
    if selection != expected_selection:
        raise ValueError("M9 selection manifest is not authority-reconstructable")
    batch = _load(root / "development-batch.json")
    validate_instance(batch, "m9-development-batch")
    subject_by_id = {subject.subject_id: subject for subject in authority.subjects}
    if {entry.get("subject_id") for entry in batch["subjects"]} != set(subject_by_id):
        raise ValueError("M9 development batch has incomplete or substituted subject coverage")
    reports: dict[str, JsonObject] = {}
    reviews: dict[tuple[str, str], JsonObject] = {}
    expected_paths = {"selection.json", "development-batch.json"}
    for entry in batch["subjects"]:
        subject_id = entry["subject_id"]
        subject = subject_by_id[subject_id]
        report_path = root / entry["machine_report_path"]
        report = _load(report_path)
        expected_paths.add(entry["machine_report_path"])
        expected_report = build_machine_report(authority, selection, subject, reviewed_at=report.get("reviewed_at"))
        if report != expected_report or sha256_json(report) != entry["machine_report_sha256"]:
            raise ValueError(f"M9 machine report drift: {subject_id}")
        reports[subject_id] = report
        roles: set[str] = set()
        executions: set[str] = set()
        responses: set[str] = set()
        for reference in entry["ai_reviews"]:
            role = reference["review_role"]
            review_path = root / reference["path"]
            review = _load(review_path)
            expected_paths.add(reference["path"])
            if sha256_json(review) != reference["sha256"]:
                raise ValueError(f"M9 AI review hash drift: {subject_id}/{role}")
            issues = validate_ai_review(review, selection=selection, subject=subject, machine_report=report)
            if issues:
                raise ValueError(f"M9 AI review invalid: {subject_id}/{role}: {', '.join(issues)}")
            execution, response_hash = str(review["capture"]["execution_id"]), str(review["raw_response_sha256"])
            if execution in executions or response_hash in responses:
                raise ValueError(f"M9 AI roles are not capture-separated: {subject_id}")
            executions.add(execution)
            responses.add(response_hash)
            roles.add(role)
            reviews[(subject_id, role)] = review
        if roles != set(CHECKLISTS):
            raise ValueError(f"M9 AI role coverage is incomplete: {subject_id}")
    actual_paths = {path.relative_to(root).as_posix() for path in root.rglob("*") if path.is_file()}
    if actual_paths != expected_paths:
        raise ValueError("M9 development batch has missing or unexpected files")
    expected_inventory = [{"path": path, "sha256": sha256_json(_load(root / path))} for path in sorted(expected_paths - {"development-batch.json"})]
    if batch["inventory"] != expected_inventory:
        raise ValueError("M9 closed inventory drift")
    expected_batch = build_development_batch(
        authority, selection, reports, reviews, created_at=batch.get("created_at"), inventory=expected_inventory,
    )
    if batch != expected_batch:
        raise ValueError("M9 development batch is not reconstructable")
    return {"batch_id": batch["batch_id"], "approval_tier": "DEVELOPMENT_APPROVED", "selection_scope": "REPRESENTATIVE_SAMPLE", "selected_subject_count": 18, "ai_review_count": 36, "human_reviewed": False, "release_approved": False, "provider_authenticated": False}
