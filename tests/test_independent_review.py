from __future__ import annotations

import copy
from pathlib import Path

import pytest

from english_master.independent_review.authority import VerifiedM9Authority
from english_master.independent_review.development import build_development_batch
from english_master.independent_review.machine import build_machine_report
from english_master.independent_review.release import validate_release_decision
from english_master.independent_review.review import CHECKLISTS, build_ai_review, validate_ai_review
from english_master.independent_review.selection import build_selection
from english_master.independent_review.storage import publish_development_batch
from english_master.independent_review.verification import verify_development_batch

ROOT = Path(__file__).resolve().parents[1]


def _authority() -> VerifiedM9Authority:
    return VerifiedM9Authority.from_files(
        structure_path=ROOT / "curriculum" / "structure.json",
        snapshot_directory=ROOT / "data" / "reviews" / "m5" / "development-20260903-062008",
        source_registry_path=ROOT / "sources" / "registry.yaml",
        m6_batch_path=ROOT / "data" / "generated" / "m6" / "development-batches" / "20260903-v6" / "development-batch.json",
        m6_root=ROOT / "data" / "generated" / "m6" / "development-candidates" / "20260903-v6-selected",
        exercise_root=ROOT / "curriculum" / "exercises",
        m7_batch_path=ROOT / "curriculum" / "exercises" / "development-batches" / "20260903-v3" / "development-batch.json",
        pilot_directory=ROOT / "curriculum" / "ai-practice" / "pilot-batches" / "20260905-v13",
    )


@pytest.fixture(scope="module")
def authority() -> VerifiedM9Authority:
    return _authority()


def _response(role: str) -> dict[str, object]:
    return {
        "decision": "APPROVE",
        "checklist": [{"criterion": criterion, "result": "PASS", "notes": "Test-only fixture confirms the criterion is recorded."} for criterion in CHECKLISTS[role]],
        "findings": [],
        "limitations": ["Test fixture only; it is never published as real M9 AI evidence."],
    }


def _evidence(authority: VerifiedM9Authority):
    selection = build_selection(authority, created_at="2026-09-05T10:00:00Z")
    reports = {subject.subject_id: build_machine_report(authority, selection, subject, reviewed_at="2026-09-05T10:00:00Z") for subject in authority.subjects}
    reviews = {}
    for subject in authority.subjects:
        for position, role in enumerate(CHECKLISTS):
            reviews[(subject.subject_id, role)] = build_ai_review(
                selection=selection, subject=subject, machine_report=reports[subject.subject_id], role=role,
                capture={"capture_mode": "SESSION_CAPTURED", "provider": "TEST_CAPTURE_ONLY", "model": "TEST_CAPTURE_ONLY", "execution_id": f"test-{subject.subject_id}-{position}", "provider_authenticated": False, "observed_at": "2026-09-05T10:01:00Z"},
                raw_response=_response(role), reviewed_at="2026-09-05T10:01:00Z",
            )
    return selection, reports, reviews


def _publishable_evidence(authority: VerifiedM9Authority):
    selection = build_selection(authority, created_at="2026-09-05T10:00:00Z")
    reports = {subject.subject_id: build_machine_report(authority, selection, subject, reviewed_at="2026-09-05T10:00:00Z") for subject in authority.subjects}
    reviews = {}
    for subject in authority.subjects:
        for position, role in enumerate(CHECKLISTS):
            reviews[(subject.subject_id, role)] = build_ai_review(
                selection=selection, subject=subject, machine_report=reports[subject.subject_id], role=role,
                capture={"capture_mode": "SESSION_CAPTURED", "provider": "UNKNOWN", "model": "UNKNOWN", "execution_id": f"fixture-{subject.subject_id}-{position}", "provider_authenticated": False, "observed_at": "2026-09-05T10:01:00Z"},
                raw_response=_response(role), reviewed_at="2026-09-05T10:01:00Z",
            )
    return selection, reports, reviews


def test_authority_selects_complete_current_population(authority: VerifiedM9Authority) -> None:
    assert len(authority.subjects) == 60
    assert len({subject.lesson_id for subject in authority.subjects}) == 10
    assert {subject.content_type for subject in authority.subjects} == {"LESSON", "EXERCISE_SET", "AI_PRACTICE_PROMPT"}
    assert {subject.modality for subject in authority.subjects if subject.modality} == {"LISTENING", "SPEAKING", "PRONUNCIATION", "WRITING"}
    assert all("/" in subject.artifact_path for subject in authority.subjects)
    selection = build_selection(authority, created_at="2026-09-05T10:00:00Z")
    assert selection["schema_version"] == "2.0"
    assert selection["selection_scope"] == "FULL_POPULATION"
    assert selection["population"] == {
        "lesson_count": 10,
        "exercise_set_count": 10,
        "prompt_count": 40,
        "total_subject_count": 60,
        "selected_subject_count": 60,
        "unreviewed_outside_selection": False,
    }
    assert selection["upstream"]["m8_1_terminal_run_consumed"] is False


def test_machine_reports_reconstruct_all_subjects(authority: VerifiedM9Authority) -> None:
    selection = build_selection(authority, created_at="2026-09-05T10:00:00Z")
    reports = [build_machine_report(authority, selection, subject, reviewed_at="2026-09-05T10:00:00Z") for subject in authority.subjects]
    assert all(report["result"] == "PASS" for report in reports)
    assert sum(report["review_scope"] == "STATIC_PROTOCOL" for report in reports) == 40


def test_test_only_capture_cannot_publish_development_evidence(authority: VerifiedM9Authority, tmp_path: Path) -> None:
    # TEST_CAPTURE_ONLY is deliberately non-promotable; successful production
    # M9 evidence requires separately retained real capture provenance.
    with pytest.raises(ValueError, match="NON_PROMOTABLE_AI_PROVENANCE"):
        _evidence(authority)


def test_capture_observed_before_machine_report_is_rejected(authority: VerifiedM9Authority) -> None:
    selection = build_selection(authority, created_at="2026-09-05T10:00:00Z")
    subject = authority.subjects[0]
    report = build_machine_report(authority, selection, subject, reviewed_at="2026-09-05T10:00:00Z")
    with pytest.raises(ValueError, match="CHRONOLOGY"):
        build_ai_review(
            selection=selection, subject=subject, machine_report=report, role="LINGUISTIC_AI_REVIEWER",
            capture={"capture_mode": "SESSION_CAPTURED", "provider": "UNKNOWN", "model": "UNKNOWN", "execution_id": "chronology-before-report", "provider_authenticated": False, "observed_at": "2026-09-05T09:59:59Z"},
            raw_response=_response("LINGUISTIC_AI_REVIEWER"), reviewed_at="2026-09-05T10:01:00Z",
        )


def test_machine_report_before_selection_is_rejected(authority: VerifiedM9Authority) -> None:
    selection = build_selection(authority, created_at="2026-09-05T10:01:00Z")
    subject = authority.subjects[0]
    report = build_machine_report(authority, selection, subject, reviewed_at="2026-09-05T10:00:00Z")
    with pytest.raises(ValueError, match="CHRONOLOGY"):
        build_ai_review(
            selection=selection, subject=subject, machine_report=report, role="LINGUISTIC_AI_REVIEWER",
            capture={"capture_mode": "SESSION_CAPTURED", "provider": "UNKNOWN", "model": "UNKNOWN", "execution_id": "chronology-before-selection", "provider_authenticated": False, "observed_at": "2026-09-05T10:02:00Z"},
            raw_response=_response("LINGUISTIC_AI_REVIEWER"), reviewed_at="2026-09-05T10:02:00Z",
        )


def test_review_recorded_before_capture_is_rejected(authority: VerifiedM9Authority) -> None:
    selection = build_selection(authority, created_at="2026-09-05T10:00:00Z")
    subject = authority.subjects[0]
    report = build_machine_report(authority, selection, subject, reviewed_at="2026-09-05T10:00:00Z")
    with pytest.raises(ValueError, match="CHRONOLOGY"):
        build_ai_review(
            selection=selection, subject=subject, machine_report=report, role="LINGUISTIC_AI_REVIEWER",
            capture={"capture_mode": "SESSION_CAPTURED", "provider": "UNKNOWN", "model": "UNKNOWN", "execution_id": "chronology-before-record", "provider_authenticated": False, "observed_at": "2026-09-05T10:02:00Z"},
            raw_response=_response("LINGUISTIC_AI_REVIEWER"), reviewed_at="2026-09-05T10:01:00Z",
        )


def test_equal_chronology_boundaries_are_valid(authority: VerifiedM9Authority) -> None:
    selection = build_selection(authority, created_at="2026-09-05T10:00:00Z")
    subject = authority.subjects[0]
    report = build_machine_report(authority, selection, subject, reviewed_at="2026-09-05T10:00:00Z")
    review = build_ai_review(
        selection=selection, subject=subject, machine_report=report, role="LINGUISTIC_AI_REVIEWER",
        capture={"capture_mode": "SESSION_CAPTURED", "provider": "UNKNOWN", "model": "UNKNOWN", "execution_id": "chronology-equal", "provider_authenticated": False, "observed_at": "2026-09-05T10:00:00Z"},
        raw_response=_response("LINGUISTIC_AI_REVIEWER"), reviewed_at="2026-09-05T10:00:00Z",
    )
    assert validate_ai_review(review, selection=selection, subject=subject, machine_report=report) == ()
    assert review["schema_version"] == "2.0"
    assert "human_reviewed" not in review
    assert "release_approved" not in review
    forbidden_claim = copy.deepcopy(review)
    forbidden_claim["human_reviewed"] = False
    assert validate_ai_review(
        forbidden_claim, selection=selection, subject=subject, machine_report=report,
    )[0].startswith("SCHEMA:")


def test_historical_v1_review_contract_remains_selectable(authority: VerifiedM9Authority) -> None:
    selection = build_selection(authority, created_at="2026-09-05T10:00:00Z")
    selection["schema_version"] = "1.0"
    subject = authority.subjects[0]
    report = build_machine_report(authority, selection, subject, reviewed_at="2026-09-05T10:00:00Z")
    review = build_ai_review(
        selection=selection, subject=subject, machine_report=report, role="LINGUISTIC_AI_REVIEWER",
        capture={"capture_mode": "SESSION_CAPTURED", "provider": "UNKNOWN", "model": "UNKNOWN", "execution_id": "historical-v1", "provider_authenticated": False, "observed_at": "2026-09-05T10:00:00Z"},
        raw_response=_response("LINGUISTIC_AI_REVIEWER"), reviewed_at="2026-09-05T10:00:00Z",
    )
    assert review["schema_version"] == "1.0"
    assert review["human_reviewed"] is False
    assert review["release_approved"] is False
    assert validate_ai_review(review, selection=selection, subject=subject, machine_report=report) == ()


def test_development_batch_cannot_predate_reviews(authority: VerifiedM9Authority, tmp_path: Path) -> None:
    selection, reports, reviews = _publishable_evidence(authority)
    with pytest.raises(ValueError, match="predates AI review"):
        publish_development_batch(tmp_path / "m9", authority, selection, reports, reviews, created_at="2026-09-05T10:00:00Z")


def test_representative_sample_cannot_authorize_release() -> None:
    assert validate_release_decision({}, {})
