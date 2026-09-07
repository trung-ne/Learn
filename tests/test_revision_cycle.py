from __future__ import annotations

from pathlib import Path

import pytest

from english_master.independent_review.authority import VerifiedM9Authority
from english_master.independent_review.machine import build_machine_report
from english_master.independent_review.review import CHECKLISTS
from english_master.independent_review.selection import build_selection
from english_master.lesson_generation.canonical import sha256_json
from english_master.revision_cycle.evidence import build_review_input, validate_review_input
from english_master.revision_cycle.planning import build_revision_requests
from english_master.revision_cycle.terminal import build_revision_manifest, validate_revision_manifest
from english_master.revision_cycle.storage import publish_finding_batch
from english_master.revision_cycle.verification import build_finding_batch, verify_finding_batch

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


def test_non_promotable_failed_m9_capture_is_valid_revision_input() -> None:
    authority = _authority()
    selection = build_selection(authority, created_at="2026-09-05T10:00:00Z")
    subject = authority.subjects[0]
    report = build_machine_report(authority, selection, subject, reviewed_at="2026-09-05T10:00:00Z")
    role = "LINGUISTIC_AI_REVIEWER"
    response = {
        "decision": "NEEDS_REVISION",
        "checklist": [
            {"criterion": criterion, "result": "FAIL" if criterion == "LANGUAGE_ACCURACY" else "PASS", "notes": "TEST_ONLY captured finding."}
            for criterion in CHECKLISTS[role]
        ],
        "findings": [{"severity": "MAJOR", "category": "TEST_ONLY", "description": "A test-only material defect.", "recommendation": "Repair it."}],
        "limitations": ["TEST_ONLY; this is non-promotable M10 input evidence."],
    }
    value = build_review_input(
        selection=selection,
        subject=subject,
        machine_report=report,
        role=role,
        capture={"capture_mode": "TEST_ONLY", "provider": "TEST_CAPTURE_ONLY", "model": "TEST_CAPTURE_ONLY", "execution_id": "test-m10-input", "provider_authenticated": False, "observed_at": "2026-09-05T10:01:00Z"},
        raw_response=response,
        observed_at="2026-09-05T10:01:00Z",
        imported_at="2026-09-05T10:02:00Z",
    )
    assert value["promotion_status"] == "NON_PROMOTABLE"
    assert value["decision"] == "NEEDS_REVISION"
    assert not validate_review_input(value, selection=selection, subject=subject, machine_report=report)


def test_unknown_factual_observation_time_is_retained_without_invention() -> None:
    authority = _authority()
    selection = build_selection(authority, created_at="2026-09-05T10:00:00Z")
    subject = authority.subjects[0]
    report = build_machine_report(authority, selection, subject, reviewed_at="2026-09-05T10:00:00Z")
    role = "LINGUISTIC_AI_REVIEWER"
    response = {"decision": "NEEDS_REVISION", "checklist": [{"criterion": criterion, "result": "FAIL" if criterion == "LANGUAGE_ACCURACY" else "PASS", "notes": "TEST_ONLY"} for criterion in CHECKLISTS[role]], "findings": [{"severity": "MAJOR", "category": "TEST_ONLY", "description": "Test defect."}], "limitations": ["TEST_ONLY"]}
    value = build_review_input(selection=selection, subject=subject, machine_report=report, role=role, capture={"capture_mode": "SESSION_CAPTURED", "provider": "UNKNOWN", "model": "UNKNOWN", "execution_id": "TEST_ONLY_UNKNOWN_TIME", "provider_authenticated": False, "observed_at": "UNKNOWN"}, raw_response=response, observed_at="UNKNOWN", imported_at="2026-09-05T10:02:00Z")
    assert value["observed_at"] == "UNKNOWN"


def test_approval_cannot_be_imported_as_m10_finding_input() -> None:
    authority = _authority()
    selection = build_selection(authority, created_at="2026-09-05T10:00:00Z")
    subject = authority.subjects[0]
    report = build_machine_report(authority, selection, subject, reviewed_at="2026-09-05T10:00:00Z")
    response = {"decision": "APPROVE", "checklist": [{"criterion": criterion, "result": "PASS", "notes": "TEST_ONLY"} for criterion in CHECKLISTS["LINGUISTIC_AI_REVIEWER"]], "findings": [], "limitations": ["TEST_ONLY"]}
    with pytest.raises(ValueError, match="PROMOTION_BOUNDARY"):
        build_review_input(selection=selection, subject=subject, machine_report=report, role="LINGUISTIC_AI_REVIEWER", capture={"capture_mode": "TEST_ONLY", "provider": "TEST_CAPTURE_ONLY", "model": "TEST_CAPTURE_ONLY", "execution_id": "test-m10-approve", "provider_authenticated": False, "observed_at": "2026-09-05T10:01:00Z"}, raw_response=response, observed_at="2026-09-05T10:01:00Z", imported_at="2026-09-05T10:02:00Z")


def test_finding_batch_is_atomic_and_detects_tampering(tmp_path: Path) -> None:
    authority = _authority()
    selection = build_selection(authority, created_at="2026-09-05T10:00:00Z")
    subject = authority.subjects[0]
    report = build_machine_report(authority, selection, subject, reviewed_at="2026-09-05T10:00:00Z")
    response = {"decision": "NEEDS_REVISION", "checklist": [{"criterion": criterion, "result": "FAIL" if criterion == "LANGUAGE_ACCURACY" else "PASS", "notes": "TEST_ONLY"} for criterion in CHECKLISTS["LINGUISTIC_AI_REVIEWER"]], "findings": [{"severity": "MAJOR", "category": "TEST_ONLY", "description": "Test defect."}], "limitations": ["TEST_ONLY"]}
    item = build_review_input(selection=selection, subject=subject, machine_report=report, role="LINGUISTIC_AI_REVIEWER", capture={"capture_mode": "TEST_ONLY", "provider": "TEST_CAPTURE_ONLY", "model": "TEST_CAPTURE_ONLY", "execution_id": "test-m10-batch", "provider_authenticated": False, "observed_at": "2026-09-05T10:01:00Z"}, raw_response=response, observed_at="2026-09-05T10:01:00Z", imported_at="2026-09-05T10:02:00Z")
    destination = publish_finding_batch(tmp_path / "m10", selection=selection, subjects={candidate.subject_id: candidate for candidate in authority.subjects}, machine_reports={subject.subject_id: report}, inputs={item["input_id"]: item}, imported_at="2026-09-05T10:02:00Z")
    assert verify_finding_batch(destination, selection=selection, subjects={candidate.subject_id: candidate for candidate in authority.subjects})["promotion_status"] == "NON_PROMOTABLE"
    with pytest.raises(FileExistsError):
        publish_finding_batch(destination, selection=selection, subjects={candidate.subject_id: candidate for candidate in authority.subjects}, machine_reports={subject.subject_id: report}, inputs={item["input_id"]: item}, imported_at="2026-09-05T10:02:00Z")
    path = next((destination / "inputs").glob("*.json"))
    path.write_text(path.read_text(encoding="utf-8").replace("TEST_ONLY", "tampered"), encoding="utf-8")
    with pytest.raises(ValueError, match="hash drift"):
        verify_finding_batch(destination, selection=selection, subjects={candidate.subject_id: candidate for candidate in authority.subjects})


def test_revision_requests_group_findings_and_derive_closure() -> None:
    authority = _authority()
    selection = build_selection(authority, created_at="2026-09-05T10:00:00Z")
    subject = authority.subjects[0]
    report = build_machine_report(authority, selection, subject, reviewed_at="2026-09-05T10:00:00Z")
    role = "LINGUISTIC_AI_REVIEWER"
    response = {"decision": "NEEDS_REVISION", "checklist": [{"criterion": criterion, "result": "FAIL" if criterion == "LANGUAGE_ACCURACY" else "PASS", "notes": "TEST_ONLY"} for criterion in CHECKLISTS[role]], "findings": [{"severity": "MAJOR", "category": "TEST_ONLY", "description": "Test defect.", "recommendation": "Repair it."}], "limitations": ["TEST_ONLY"]}
    item = build_review_input(selection=selection, subject=subject, machine_report=report, role=role, capture={"capture_mode": "TEST_ONLY", "provider": "TEST_CAPTURE_ONLY", "model": "TEST_CAPTURE_ONLY", "execution_id": "test-m10-plan", "provider_authenticated": False, "observed_at": "2026-09-05T10:01:00Z"}, raw_response=response, observed_at="2026-09-05T10:01:00Z", imported_at="2026-09-05T10:02:00Z")
    requests = build_revision_requests(review_inputs={item["input_id"]: item}, subjects=authority.subjects)
    assert len(requests) == 1
    request = requests[0]
    assert request["target_milestone"] == "M6"
    assert request["rebuild_closure"] == [{"target_milestone": "M7", "artifact_kind": "EXERCISE_SET", "scope": "SUBJECT_LESSON", "lesson_id": subject.lesson_id}, {"target_milestone": "M8_2", "artifact_kind": "AI_PRACTICE_PILOT", "scope": "FULL_CLOSED_PILOT"}]
    assert request["findings"][0]["finding"] == response["findings"][0]


def test_terminal_manifest_rejects_test_only_readiness() -> None:
    authority = _authority()
    selection = build_selection(authority, created_at="2026-09-05T10:00:00Z")
    subject = authority.subjects[0]
    report = build_machine_report(authority, selection, subject, reviewed_at="2026-09-05T10:00:00Z")
    role = "LINGUISTIC_AI_REVIEWER"
    response = {"decision": "NEEDS_REVISION", "checklist": [{"criterion": criterion, "result": "FAIL" if criterion == "LANGUAGE_ACCURACY" else "PASS", "notes": "TEST_ONLY"} for criterion in CHECKLISTS[role]], "findings": [{"severity": "MAJOR", "category": "TEST_ONLY", "description": "Test defect."}], "limitations": ["TEST_ONLY"]}
    item = build_review_input(selection=selection, subject=subject, machine_report=report, role=role, capture={"capture_mode": "TEST_ONLY", "provider": "TEST_CAPTURE_ONLY", "model": "TEST_CAPTURE_ONLY", "execution_id": "test-m10-terminal", "provider_authenticated": False, "observed_at": "2026-09-05T10:01:00Z"}, raw_response=response, observed_at="2026-09-05T10:01:00Z", imported_at="2026-09-05T10:02:00Z")
    requests = build_revision_requests(review_inputs={item["input_id"]: item}, subjects=authority.subjects)
    finding_batch = build_finding_batch(
        selection=selection,
        subjects={candidate.subject_id: candidate for candidate in authority.subjects},
        machine_reports={subject.subject_id: report},
        inputs={item["input_id"]: item},
        imported_at="2026-09-05T10:02:00Z",
        inventory=[
            {"path": "selection.json", "sha256": sha256_json(selection)},
            {"path": f"machine/{subject.subject_id.split('_', 1)[1][:16]}.json", "sha256": sha256_json(report)},
            {"path": f"inputs/{item['input_id'].split('_', 1)[1][:16]}.json", "sha256": sha256_json(item)},
        ],
    )
    with pytest.raises(ValueError, match="TEST_ONLY"):
        build_revision_manifest(finding_batch=finding_batch, finding_batch_path="finding-batch.json", revision_requests=requests, review_inputs={item["input_id"]: item}, dispositions=[{"request_id": requests[0]["request_id"], "request_sha256": sha256_json(requests[0]), "status": "RESOLVED", "successor_evidence": [{"kind": "M6_SUCCESSOR_BATCH", "path": "successor/m6.json", "sha256": "0" * 64}, {"kind": "M7_SUCCESSOR_BATCH", "path": "successor/m7.json", "sha256": "0" * 64}, {"kind": "M8_2_SUCCESSOR_PILOT", "path": "successor/m8.json", "sha256": "0" * 64}]}], terminal_state="READY_FOR_FRESH_M9", created_at="2026-09-05T10:03:00Z")


def test_governance_rejection_binds_receipts_and_retry_budget() -> None:
    from english_master.revision_cycle.governance import (
        build_attempt,
        build_capture,
        build_governance_run,
        build_receipts,
        build_rejection,
    )
    from english_master.revision_cycle.models import RevisionIssue

    authority = _authority()
    selection = build_selection(authority, created_at="2026-09-05T10:00:00Z")
    subject = authority.subjects[0]
    report = build_machine_report(authority, selection, subject, reviewed_at="2026-09-05T10:00:00Z")
    response = {"decision": "NEEDS_REVISION", "checklist": [{"criterion": criterion, "result": "FAIL" if criterion == "LANGUAGE_ACCURACY" else "PASS", "notes": "Test defect."} for criterion in CHECKLISTS["LINGUISTIC_AI_REVIEWER"]], "findings": [{"severity": "MAJOR", "category": "TEST", "description": "Test defect."}], "limitations": ["TEST_ONLY"]}
    item = build_review_input(selection=selection, subject=subject, machine_report=report, role="LINGUISTIC_AI_REVIEWER", capture={"capture_mode": "TEST_ONLY", "provider": "TEST_CAPTURE_ONLY", "model": "TEST_CAPTURE_ONLY", "execution_id": "test-m10-governance", "provider_authenticated": False, "observed_at": "2026-09-05T10:01:00Z"}, raw_response=response, observed_at="2026-09-05T10:01:00Z", imported_at="2026-09-05T10:02:00Z")
    request = build_revision_requests(review_inputs={item["input_id"]: item}, subjects=authority.subjects)[0]
    finding_batch = build_finding_batch(
        selection=selection,
        subjects={candidate.subject_id: candidate for candidate in authority.subjects},
        machine_reports={subject.subject_id: report},
        inputs={item["input_id"]: item},
        imported_at="2026-09-05T10:02:00Z",
        inventory=[
            {"path": "selection.json", "sha256": sha256_json(selection)},
            {"path": f"machine/{subject.subject_id.split('_', 1)[1][:16]}.json", "sha256": sha256_json(report)},
            {"path": f"inputs/{item['input_id'].split('_', 1)[1][:16]}.json", "sha256": sha256_json(item)},
        ],
    )
    run = build_governance_run(finding_batch=finding_batch, request=request, predecessor=request["predecessor"], maximum_attempts=3, policy_version="M10_GOVERNANCE_v1", created_at="2026-09-05T10:03:00Z")
    capture = build_capture(run=run, attempt_number=1, prompt="repair", raw_response={"content": "new"}, capture={"capture_mode": "TEST_ONLY", "provider": "TEST_CAPTURE_ONLY", "model": "TEST_CAPTURE_ONLY", "execution_id": "test-m10-regenerate"}, captured_at="2026-09-05T10:04:00Z")
    attempt = build_attempt(run=run, request=request, attempt_number=1, predecessor=request["predecessor"], artifact={"lesson": "new"}, audit={"audit": "new"}, capture=capture, parent_rejection=None, created_at="2026-09-05T10:04:00Z")
    receipts = build_receipts(run=run, attempt=attempt, stage_issues={"REPAIR_SCOPE": [RevisionIssue("SCOPE", "/body", "Changes exceed repair authority")]}, reviewed_at="2026-09-05T10:05:00Z")
    assert [receipt["outcome"] for receipt in receipts] == ["PASS", "PASS", "PASS", "FAIL", "NOT_RUN", "NOT_RUN"]
    rejection = build_rejection(run=run, attempt=attempt, receipts=receipts, rejected_at="2026-09-05T10:06:00Z")
    assert rejection["retryable"] is True
    assert rejection["remaining_attempts"] == 2
    assert len(rejection["receipt_hashes"]) == 6
    with pytest.raises(ValueError, match="unchanged successor bytes"):
        build_attempt(run=run, request=request, attempt_number=2, predecessor=request["predecessor"], artifact={"lesson": "new"}, audit={"audit": "replacement"}, capture=capture, parent_rejection=rejection, created_at="2026-09-05T10:07:00Z")


def test_non_retryable_failure_escalates() -> None:
    from english_master.revision_cycle.governance import build_rejection
    from english_master.revision_cycle.models import RevisionIssue

    run = {"run_id": "m10run_" + "0" * 64, "maximum_attempts": 3}
    attempt = {"attempt_id": "m10attempt_" + "0" * 64, "attempt_number": 1, "candidate": {"content_sha256": "b" * 64}}
    receipts = [{"outcome": "FAIL", "issues": [RevisionIssue("AUTHORITY_CONFLICT", "/title", "M5-bound title").as_dict()]}]
    rejection = build_rejection(run=run, attempt=attempt, receipts=receipts, rejected_at="2026-09-05T10:06:00Z")
    assert rejection["retryable"] is False
