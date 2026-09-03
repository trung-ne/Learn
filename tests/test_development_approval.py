from __future__ import annotations

import copy
import json
from pathlib import Path

import pytest

from english_master.curriculum_review.loading import load_strict_document
from english_master.curriculum_review.workflow import (
    build_manifest,
    publish_development_snapshot,
    verify_development_snapshot_bundle,
)
from english_master.curriculum_validation.validator import load_bundle
from english_master.lesson_generation.authority import (
    VerifiedM5Authority,
    VerifiedM5DevelopmentAuthority,
)
from english_master.lesson_generation.builders import build_authorization, build_request
from english_master.lesson_generation.canonical import identity, sha256_json, sha256_text
from english_master.lesson_generation.development import build_development_batch
from english_master.lesson_generation.review import (
    AI_CHECKLIST_BY_ROLE,
    REQUIRED_DEVELOPMENT_LESSONS,
    build_ai_review_prompt,
    m7_eligibility_issues,
    validate_ai_lesson_review,
    validate_development_batch,
)
from english_master.schema_validation import load_json, validation_issues

ROOT = Path(__file__).resolve().parents[1]
SOURCE_REGISTRY = ROOT / "sources" / "registry.yaml"
GENERATED_BUNDLES = ROOT / "data" / "generated" / "m6" / "bundles"


def _development_authority_with_path(tmp_path: Path) -> tuple[VerifiedM5DevelopmentAuthority, Path]:
    bundle = load_bundle(ROOT / "curriculum" / "structure.json")
    registry = load_strict_document(SOURCE_REGISTRY)
    manifest = build_manifest(bundle, registry, source_registry_path=SOURCE_REGISTRY)
    output = tmp_path / "development-snapshot"
    snapshot = publish_development_snapshot(
        output, bundle, manifest, source_registry=registry, source_registry_path=SOURCE_REGISTRY,
        produced_at="2026-09-03T12:00:00Z", git_commit="1f393a2",
    )
    assert snapshot["approval_tier"] == "DEVELOPMENT_APPROVED"
    verified = verify_development_snapshot_bundle(output, bundle, source_registry=registry, source_registry_path=SOURCE_REGISTRY)
    assert verified == snapshot
    authority = VerifiedM5DevelopmentAuthority.from_files(ROOT / "curriculum" / "structure.json", output, SOURCE_REGISTRY)
    return authority, output


def _development_authority(tmp_path: Path) -> VerifiedM5DevelopmentAuthority:
    return _development_authority_with_path(tmp_path)[0]


def test_development_snapshot_needs_no_human_registry(tmp_path: Path) -> None:
    authority = _development_authority(tmp_path)
    assert authority.snapshot["record_type"] == "curriculum_development_snapshot"
    authorization = build_authorization(authority, ["A1-U01-L01"])
    assert authorization["authority_source"] == "VERIFIED_M5_DEVELOPMENT_SNAPSHOT"
    assert build_request(authority, authorization, "A1-U01-L01")["snapshot_binding"] == authority.snapshot_binding()


def _ai_review(lesson: dict, audit: dict, authority: VerifiedM5DevelopmentAuthority, role: str, *, capture_mode: str = "SESSION_CAPTURED") -> dict:
    prompt = build_ai_review_prompt(role, lesson, audit)
    review = {
        "schema_version": "1.0", "record_type": "lesson_ai_review", "approval_tier": "AI_REVIEWED",
        "lesson_id": lesson["id"], "lesson_sha256": sha256_json(lesson), "audit_sha256": sha256_json(audit),
        "snapshot_binding": authority.snapshot_binding(), "reviewer_type": "AI", "review_role": role,
        "independent_of_generation": True,
        "review_prompt": {"version": "test-v1", "sha256": sha256_text(prompt), "capture_mode": capture_mode, "run_id": "session-test-run"},
        "response": {"sha256": sha256_text("test response"), "provider": "UNKNOWN", "model": "UNKNOWN", "parameters": {}, "replayable_from_capture": True},
        "reviewed_at": "2026-09-03T12:01:00Z", "decision": "APPROVE",
        "checklist": [{"criterion": criterion, "result": "PASS", "notes": "Synthetic validation record only."} for criterion in sorted(AI_CHECKLIST_BY_ROLE[role])],
        "findings": [],
        "copyright_originality_check": {"methods": ["authorized input scope"], "result": "NO_CONCERN_FOUND", "scope_limitations": "No external search performed."},
        "limitations": ["Synthetic test record; not production evidence."],
    }
    review["ai_review_id"] = identity("m6aireview", review, "ai_review_id")
    return review


def _write_document(path: Path, document: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(document, ensure_ascii=False, sort_keys=True), encoding="utf-8")


def _refresh_identity(document: dict, prefix: str, field: str) -> None:
    document[field] = identity(prefix, document, field)


def _complete_development_batch(
    tmp_path: Path,
) -> tuple[VerifiedM5DevelopmentAuthority, Path, dict]:
    """Build a genuine-shape ten-lesson batch entirely under a temporary root."""
    authority = _development_authority(tmp_path)
    bundle_root = tmp_path / "m6-development"
    for lesson_id in REQUIRED_DEVELOPMENT_LESSONS:
        lesson = copy.deepcopy(load_json(GENERATED_BUNDLES / lesson_id / "lesson.json"))
        audit = copy.deepcopy(load_json(GENERATED_BUNDLES / lesson_id / "audit.json"))
        audit["snapshot_binding"] = authority.snapshot_binding()
        audit["response_provenance"]["provider"] = "UNKNOWN"
        lesson_path = bundle_root / "bundles" / lesson_id / "lesson.json"
        audit_path = bundle_root / "bundles" / lesson_id / "audit.json"
        _write_document(lesson_path, lesson)
        _write_document(audit_path, audit)
        for role in sorted(AI_CHECKLIST_BY_ROLE):
            review = _ai_review(lesson, audit, authority, role)
            _write_document(bundle_root / "reviews" / lesson_id / f"{role}.json", review)
    report = build_development_batch(
        authority,
        bundle_root,
        created_at="2026-09-03T12:02:00Z",
        git_commit="1f393a2",
    )
    return authority, bundle_root, report


def _issue_codes(issues: tuple) -> set[str]:
    return {issue.code for issue in issues}


def test_ai_review_is_not_human_and_test_only_is_non_promotable(tmp_path: Path) -> None:
    authority = _development_authority(tmp_path)
    lesson = {"id": "A1-U01-L01"}
    # Use a real machine audit shape from the existing test fixture generator is unnecessary here;
    # the invalid audit proves no test-only AI review can be promoted.
    audit = {"lesson_id": lesson["id"], "status": "REJECTED", "qa_status": "REJECTED"}
    review = _ai_review(lesson, audit, authority, "LINGUISTIC_AI_REVIEWER", capture_mode="TEST_ONLY")
    issues = validate_ai_lesson_review(review, lesson, audit, authority)
    assert any(issue.code == "NON_PROMOTABLE_AI_PROVENANCE" for issue in issues)
    assert review["reviewer_type"] == "AI"
    assert "reviewer" not in review


def test_complete_ten_lesson_development_batch_passes_offline(tmp_path: Path) -> None:
    authority, bundle_root, report = _complete_development_batch(tmp_path)

    assert [entry["lesson_id"] for entry in report["lessons"]] == list(REQUIRED_DEVELOPMENT_LESSONS)
    assert all(entry["generation_provenance_mode"] == "SESSION_CAPTURED" for entry in report["lessons"])
    for entry in report["lessons"]:
        for review_ref in entry["ai_reviews"]:
            review = load_json(bundle_root / review_ref["path"])
            assert review["review_prompt"]["capture_mode"] == "SESSION_CAPTURED"
            assert review["response"]["provider"] != "TEST_ONLY_MOCK"
    assert validate_development_batch(report, authority, bundle_root) == ()
    assert m7_eligibility_issues(report, authority, bundle_root) == ()


def test_development_batch_requires_both_ai_roles(tmp_path: Path) -> None:
    authority, bundle_root, report = _complete_development_batch(tmp_path)
    report["lessons"][0]["ai_reviews"][1] = copy.deepcopy(report["lessons"][0]["ai_reviews"][0])
    _refresh_identity(report, "m6devbatch", "batch_id")

    assert "AI_REVIEW_ROLE_COVERAGE" in _issue_codes(validate_development_batch(report, authority, bundle_root))


def test_development_batch_rejects_blocking_ai_finding(tmp_path: Path) -> None:
    authority, bundle_root, report = _complete_development_batch(tmp_path)
    review_ref = report["lessons"][0]["ai_reviews"][0]
    review_path = bundle_root / review_ref["path"]
    review = load_json(review_path)
    review["findings"] = [{
        "severity": "MAJOR",
        "category": "LANGUAGE_QUALITY",
        "description": "A blocking linguistic problem remains.",
        "recommendation": "Revise and review again.",
    }]
    _refresh_identity(review, "m6aireview", "ai_review_id")
    _write_document(review_path, review)
    review_ref["sha256"] = sha256_json(review)
    _refresh_identity(report, "m6devbatch", "batch_id")

    assert "AI_REVIEW_DECISION_MISMATCH" in _issue_codes(validate_development_batch(report, authority, bundle_root))


@pytest.mark.parametrize("unsafe_reference", ["lesson", "review"])
def test_development_batch_rejects_unsafe_paths(tmp_path: Path, unsafe_reference: str) -> None:
    authority, bundle_root, report = _complete_development_batch(tmp_path)
    if unsafe_reference == "lesson":
        report["lessons"][0]["lesson_path"] = "../outside/lesson.json"
        expected = "BUNDLE_PATH_ESCAPE"
    else:
        report["lessons"][0]["ai_reviews"][0]["path"] = "../outside/review.json"
        expected = "REVIEW_PATH_ESCAPE"
    _refresh_identity(report, "m6devbatch", "batch_id")

    assert expected in _issue_codes(validate_development_batch(report, authority, bundle_root))


def test_development_batch_rejects_duplicate_lesson_content(tmp_path: Path) -> None:
    authority, bundle_root, report = _complete_development_batch(tmp_path)
    first, duplicate = report["lessons"][0], report["lessons"][1]
    for field in ("lesson_path", "audit_path", "lesson_sha256", "audit_sha256", "ai_reviews"):
        duplicate[field] = copy.deepcopy(first[field])
    _refresh_identity(report, "m6devbatch", "batch_id")

    assert "DUPLICATE_LESSON_CONTENT" in _issue_codes(validate_development_batch(report, authority, bundle_root))


@pytest.mark.parametrize(
    ("hash_kind", "expected"),
    [
        ("lesson", "BUNDLE_HASH_MISMATCH"),
        ("audit", "BUNDLE_HASH_MISMATCH"),
        ("ai_review", "AI_REVIEW_HASH_MISMATCH"),
    ],
)
def test_development_batch_rejects_hash_drift(
    tmp_path: Path,
    hash_kind: str,
    expected: str,
) -> None:
    authority, bundle_root, report = _complete_development_batch(tmp_path)
    entry = report["lessons"][0]
    if hash_kind == "lesson":
        entry["lesson_sha256"] = "0" * 64
    elif hash_kind == "audit":
        entry["audit_sha256"] = "0" * 64
    else:
        entry["ai_reviews"][0]["sha256"] = "0" * 64
    _refresh_identity(report, "m6devbatch", "batch_id")

    development_issues = validate_development_batch(report, authority, bundle_root)
    assert expected in _issue_codes(development_issues)
    assert m7_eligibility_issues(report, authority, bundle_root) == development_issues


@pytest.mark.parametrize(
    ("capture_mode", "provider"),
    [
        ("TEST_ONLY", "UNKNOWN"),
        ("REPLAY_CAPTURED", "UNKNOWN"),
        ("SESSION_CAPTURED", "TEST_ONLY_MOCK"),
    ],
)
def test_ai_review_rejects_test_replay_and_mock_provenance(
    tmp_path: Path,
    capture_mode: str,
    provider: str,
) -> None:
    authority, bundle_root, report = _complete_development_batch(tmp_path)
    entry = report["lessons"][0]
    lesson = load_json(bundle_root / entry["lesson_path"])
    audit = load_json(bundle_root / entry["audit_path"])
    review = _ai_review(lesson, audit, authority, "LINGUISTIC_AI_REVIEWER", capture_mode=capture_mode)
    review["response"]["provider"] = provider
    _refresh_identity(review, "m6aireview", "ai_review_id")

    assert "NON_PROMOTABLE_AI_PROVENANCE" in _issue_codes(
        validate_ai_lesson_review(review, lesson, audit, authority)
    )


def test_development_batch_rejects_mock_generation_provenance(tmp_path: Path) -> None:
    authority, bundle_root, report = _complete_development_batch(tmp_path)
    entry = report["lessons"][0]
    lesson = load_json(bundle_root / entry["lesson_path"])
    audit_path = bundle_root / entry["audit_path"]
    audit = load_json(audit_path)
    audit["response_provenance"]["provider"] = "TEST_ONLY_MOCK"
    _write_document(audit_path, audit)
    entry["audit_sha256"] = sha256_json(audit)
    for review_ref in entry["ai_reviews"]:
        review_path = bundle_root / review_ref["path"]
        review = load_json(review_path)
        review["lesson_sha256"] = sha256_json(lesson)
        review["audit_sha256"] = sha256_json(audit)
        _refresh_identity(review, "m6aireview", "ai_review_id")
        _write_document(review_path, review)
        review_ref["sha256"] = sha256_json(review)
    _refresh_identity(report, "m6devbatch", "batch_id")

    assert "NON_PROMOTABLE_GENERATION_PROVENANCE" in _issue_codes(
        validate_development_batch(report, authority, bundle_root)
    )


@pytest.mark.parametrize("mode", ["TEST_ONLY", "REPLAY_CAPTURED"])
def test_development_batch_schema_rejects_non_promotable_generation_modes(
    tmp_path: Path,
    mode: str,
) -> None:
    authority, bundle_root, report = _complete_development_batch(tmp_path)
    report["lessons"][0]["generation_provenance_mode"] = mode
    _refresh_identity(report, "m6devbatch", "batch_id")

    assert "REVIEW_SCHEMA" in _issue_codes(validate_development_batch(report, authority, bundle_root))


def test_development_lane_cannot_claim_human_or_release_approval(tmp_path: Path) -> None:
    authority, snapshot_directory = _development_authority_with_path(tmp_path)
    assert authority.snapshot["source_bundle_policy"]["not_human_reviewed"] is True
    assert authority.snapshot["source_bundle_policy"]["not_release_approved"] is True

    for claimed_tier in ("HUMAN_REVIEWED", "RELEASE_APPROVED"):
        changed_snapshot = copy.deepcopy(authority.snapshot)
        changed_snapshot["approval_tier"] = claimed_tier
        assert validation_issues(changed_snapshot, "curriculum-development-snapshot")

    _, _, report = _complete_development_batch(tmp_path / "batch")
    for claimed_tier in ("HUMAN_REVIEWED", "RELEASE_APPROVED"):
        changed_report = copy.deepcopy(report)
        changed_report["approval_tier"] = claimed_tier
        assert validation_issues(changed_report, "lesson-development-batch")

    with pytest.raises((OSError, ValueError)):
        VerifiedM5Authority.from_files(
            ROOT / "curriculum" / "structure.json",
            snapshot_directory,
            SOURCE_REGISTRY,
            SOURCE_REGISTRY,
        )
