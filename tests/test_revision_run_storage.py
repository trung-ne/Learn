from __future__ import annotations

import json
from pathlib import Path

import pytest

from english_master.lesson_generation.canonical import identity, sha256_json
from english_master.revision_cycle.governance import (
    build_attempt,
    build_capture,
    build_governance_run,
    build_receipts,
    build_rejection,
)
from english_master.revision_cycle.models import RevisionIssue
from english_master.revision_cycle.run_storage import publish_governance_run, verify_governance_run


def _manifest(*, run: dict[str, object], request: dict[str, object]) -> dict[str, object]:
    value: dict[str, object] = {
        "schema_version": "1.0", "record_type": "m10_revision_manifest", "manifest_id": "PENDING",
        "terminal_state": "RETRY_EXHAUSTED", "finding_batch": {"path": "finding-batch.json", "sha256": run["finding_batch_sha256"]},
        "revision_requests": [{"request_id": request["request_id"], "path": "requests/1.json", "sha256": run["revision_request_sha256"]}],
        "dispositions": [{"request_id": request["request_id"], "request_sha256": run["revision_request_sha256"], "status": "RETRY_EXHAUSTED", "unresolved_issues": ["Budget exhausted."]}],
        "created_at": "2026-09-05T10:00:00Z", "fresh_m9_required": True, "content_lifecycle_status": "UNREVIEWED",
        "development_approved": False, "human_reviewed": False, "release_approved": False, "provider_authenticated": False,
        "limitations": ["No approval."],
    }
    value["manifest_id"] = identity("m10manifest", value, "manifest_id")
    return value


def test_closed_governance_run_publishes_once_and_detects_tampering(tmp_path: Path) -> None:
    predecessor = {"artifact_path": "old.json", "artifact_sha256": "a" * 64, "audit_path": "audit.json", "audit_sha256": "b" * 64}
    request = {"request_id": "m10request_" + "1" * 64, "target_milestone": "M7", "predecessor": predecessor}
    finding_batch = {"batch_id": "m10findings_" + "2" * 64}
    run = build_governance_run(finding_batch=finding_batch, request=request, predecessor=predecessor, maximum_attempts=1, policy_version="v1", created_at="2026-09-05T10:00:00Z")
    capture = build_capture(run=run, attempt_number=1, prompt="repair", raw_response={"body": "new"}, capture={"capture_mode": "SESSION_CAPTURED", "provider": "UNKNOWN", "model": "UNKNOWN", "execution_id": "UNKNOWN"}, captured_at="2026-09-05T10:01:00Z")
    attempt = build_attempt(run=run, request=request, attempt_number=1, predecessor=predecessor, artifact={"body": "new"}, audit={"ok": True}, capture=capture, parent_rejection=None, created_at="2026-09-05T10:01:00Z")
    receipts = build_receipts(run=run, attempt=attempt, stage_issues={"REPAIR_SCOPE": [RevisionIssue("SCOPE", "/", "bad")]}, reviewed_at="2026-09-05T10:02:00Z")
    rejection = build_rejection(run=run, attempt=attempt, receipts=receipts, rejected_at="2026-09-05T10:02:00Z")
    payloads = {attempt["attempt_id"]: {"prompt": "repair", "raw_response": {"body": "new"}, "artifact": {"body": "new"}, "audit": {"ok": True}, "closure": []}}
    destination = publish_governance_run(tmp_path / "run", run=run, attempts=[attempt], captures=[capture], receipts=receipts, rejections=[rejection], terminal_manifest=_manifest(run=run, request=request), payloads=payloads)
    assert verify_governance_run(destination)["receipt_count"] == 6
    with pytest.raises(FileExistsError):
        publish_governance_run(destination, run=run, attempts=[attempt], captures=[capture], receipts=receipts, rejections=[rejection], terminal_manifest=_manifest(run=run, request=request), payloads=payloads)
    path = next((destination / "receipts").glob("*.json"))
    path.write_text(json.dumps({"tampered": True}), encoding="utf-8")
    with pytest.raises(ValueError):
        verify_governance_run(destination)


def test_closed_governance_run_rejects_unexpected_root_directory(tmp_path: Path) -> None:
    predecessor = {"artifact_path": "old.json", "artifact_sha256": "a" * 64, "audit_path": "audit.json", "audit_sha256": "b" * 64}
    request = {"request_id": "m10request_" + "1" * 64, "target_milestone": "M7", "predecessor": predecessor}
    finding_batch = {"batch_id": "m10findings_" + "2" * 64}
    run = build_governance_run(finding_batch=finding_batch, request=request, predecessor=predecessor, maximum_attempts=1, policy_version="v1", created_at="2026-09-05T10:00:00Z")
    capture = build_capture(run=run, attempt_number=1, prompt="repair", raw_response={"body": "new"}, capture={"capture_mode": "SESSION_CAPTURED", "provider": "UNKNOWN", "model": "UNKNOWN", "execution_id": "UNKNOWN"}, captured_at="2026-09-05T10:01:00Z")
    attempt = build_attempt(run=run, request=request, attempt_number=1, predecessor=predecessor, artifact={"body": "new"}, audit={"ok": True}, capture=capture, parent_rejection=None, created_at="2026-09-05T10:01:00Z")
    receipts = build_receipts(run=run, attempt=attempt, stage_issues={"REPAIR_SCOPE": [RevisionIssue("SCOPE", "/", "bad")]}, reviewed_at="2026-09-05T10:02:00Z")
    rejection = build_rejection(run=run, attempt=attempt, receipts=receipts, rejected_at="2026-09-05T10:02:00Z")
    payloads = {attempt["attempt_id"]: {"prompt": "repair", "raw_response": {"body": "new"}, "artifact": {"body": "new"}, "audit": {"ok": True}, "closure": []}}
    destination = publish_governance_run(tmp_path / "run", run=run, attempts=[attempt], captures=[capture], receipts=receipts, rejections=[rejection], terminal_manifest=_manifest(run=run, request=request), payloads=payloads)
    (destination / "unexpected").mkdir()
    with pytest.raises(ValueError, match="root entry"):
        verify_governance_run(destination)
