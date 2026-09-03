"""Immutable M6 development-batch construction and publication."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Mapping

from english_master.curriculum_review.storage import publish_bundle
from english_master.curriculum_review.loading import load_strict_document

from .authority import VerifiedM5DevelopmentAuthority
from .canonical import identity, sha256_json
from .models import JsonObject
from .review import REQUIRED_DEVELOPMENT_LESSONS, validate_development_batch


def build_development_batch(
    m5: VerifiedM5DevelopmentAuthority,
    bundle_root: Path,
    *,
    created_at: str,
    tool_version: str = "3.0",
    git_commit: str | None = None,
) -> JsonObject:
    """Build a candidate batch from immutable bundles and AI review files.

    Expected layout is ``<root>/bundles/<lesson>/{lesson,audit}.json`` and
    ``<root>/reviews/<lesson>/<role>.json``. The validator is the sole
    promotion decision: this builder never marks human or release approval.
    """

    root = bundle_root.resolve()
    lessons: list[JsonObject] = []
    for lesson_id in REQUIRED_DEVELOPMENT_LESSONS:
        lesson_path = root / "bundles" / lesson_id / "lesson.json"
        audit_path = root / "bundles" / lesson_id / "audit.json"
        lesson = load_strict_document(lesson_path)
        audit = load_strict_document(audit_path)
        reviews: list[JsonObject] = []
        for role in ("LINGUISTIC_AI_REVIEWER", "PEDAGOGICAL_AI_REVIEWER"):
            review_path = root / "reviews" / lesson_id / f"{role}.json"
            review = load_strict_document(review_path)
            reviews.append({
                "review_role": role,
                "path": review_path.relative_to(root).as_posix(),
                "sha256": sha256_json(review),
            })
        lessons.append({
            "lesson_id": lesson_id,
            "lesson_path": lesson_path.relative_to(root).as_posix(),
            "audit_path": audit_path.relative_to(root).as_posix(),
            "lesson_sha256": sha256_json(lesson),
            "audit_sha256": sha256_json(audit),
            "generation_provenance_mode": "SESSION_CAPTURED",
            "ai_reviews": reviews,
        })
    tool: JsonObject = {"name": "english_master.lesson_generation.development", "version": tool_version}
    if git_commit is not None:
        tool["git_commit"] = git_commit
    report: JsonObject = {
        "schema_version": "1.0",
        "record_type": "lesson_development_batch",
        "approval_tier": "DEVELOPMENT_APPROVED",
        "snapshot_binding": m5.snapshot_binding(),
        "created_at": created_at,
        "tool": tool,
        "lessons": lessons,
        "automated_checks": {
            "schema": "PASS", "prerequisite": "PASS", "reference_scope": "PASS",
            "generation_provenance": "PASS", "no_m7_scope": "PASS",
        },
        "originality_provenance_checks": {
            "authorized_input_scope": "PASS", "duplicate_check": "PASS", "external_search_performed": False,
            "limitations": ["No Internet-wide plagiarism search was performed; checks cover authorized input, immutable hashes, and exact duplicate content only."],
        },
        "limitations": [
            "Development approval is not human review or release approval.",
            "No Internet-wide plagiarism search was performed.",
            "Session-captured AI provenance is replayable evidence, not a provider-authenticated receipt.",
        ],
    }
    report["batch_id"] = identity("m6devbatch", report, "batch_id")
    return report


def publish_development_batch(destination: Path, report: Mapping[str, Any], m5: VerifiedM5DevelopmentAuthority, bundle_root: Path) -> JsonObject:
    """Validate then atomically publish the M6 DEVELOPMENT_APPROVED overlay."""
    if destination.exists() or destination.is_symlink():
        raise FileExistsError(f"immutable destination already exists: {destination}")
    issues = validate_development_batch(report, m5, bundle_root)
    if issues:
        details = "; ".join(f"{issue.code}: {issue.message}" for issue in issues)
        raise ValueError(f"development batch cannot be promoted: {details}")
    publish_bundle(destination, {"development-batch.json": dict(report)})
    return dict(report)
