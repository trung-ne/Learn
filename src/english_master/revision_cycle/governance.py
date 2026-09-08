"""Canonical M10 attempt, receipt, rejection, and run evidence builders."""
from __future__ import annotations

from collections.abc import Iterable, Mapping
from typing import Any

from english_master.lesson_generation.canonical import identity, sha256_json, sha256_text
from english_master.schema_validation import validate_instance

from .models import NON_RETRYABLE_CODES, STAGE_CONTRACT, RevisionIssue

JsonObject = dict[str, Any]


def _reference(identifier: str, value: Mapping[str, Any]) -> JsonObject:
    return {"id": identifier, "sha256": sha256_json(value)}


def build_governance_run(*, finding_batch: Mapping[str, Any], request: Mapping[str, Any], predecessor: Mapping[str, Any], maximum_attempts: int, policy_version: str, created_at: str) -> JsonObject:
    """Freeze one bounded M10 run before any successor attempt exists."""
    if not 1 <= maximum_attempts <= 3:
        raise ValueError("M10 maximum_attempts must be between 1 and 3")
    if dict(predecessor) != request.get("predecessor"):
        raise ValueError("M10 governance predecessor must exactly match the revision request")
    value: JsonObject = {
        "schema_version": "1.0", "record_type": "m10_governance_run", "run_id": "PENDING",
        "finding_batch_id": finding_batch["batch_id"], "finding_batch_sha256": sha256_json(finding_batch),
        "revision_request_id": request["request_id"], "revision_request_sha256": sha256_json(request),
        "target_milestone": request["target_milestone"], "predecessor": dict(predecessor),
        "maximum_attempts": maximum_attempts, "policy_version": policy_version, "created_at": created_at,
        "content_lifecycle_status": "UNREVIEWED", "development_approved": False,
        "provider_authenticated": False,
    }
    value["run_id"] = identity("m10run", value, "run_id")
    validate_instance(value, "m10-governance-run")
    return value


def build_capture(*, run: Mapping[str, Any], attempt_number: int, prompt: str, raw_response: Mapping[str, Any], capture: Mapping[str, Any], captured_at: str) -> JsonObject:
    """Bind factual capture metadata and opaque prompt/response hashes."""
    value: JsonObject = {
        "schema_version": "1.0", "record_type": "m10_regeneration_capture", "capture_id": "PENDING",
        "run_id": run["run_id"], "attempt_number": attempt_number, "prompt_sha256": sha256_text(prompt),
        "raw_response_sha256": sha256_json(raw_response), "capture_mode": capture["capture_mode"],
        "provider": capture["provider"], "model": capture["model"], "execution_id": capture["execution_id"],
        "parameters": dict(capture.get("parameters", {})), "seed": capture.get("seed"),
        "provider_authenticated": False, "captured_at": captured_at,
    }
    value["capture_id"] = identity("m10capture", value, "capture_id")
    validate_instance(value, "m10-regeneration-capture")
    return value


def build_attempt(*, run: Mapping[str, Any], request: Mapping[str, Any], attempt_number: int, predecessor: Mapping[str, Any], artifact: Mapping[str, Any], audit: Mapping[str, Any], capture: Mapping[str, Any], parent_rejection: Mapping[str, Any] | None, created_at: str) -> JsonObject:
    """Create a new immutable candidate; retries require the prior rejection."""
    if attempt_number > 1 and parent_rejection is None:
        raise ValueError("M10 retry requires the complete parent rejection")
    if run.get("revision_request_id") != request.get("request_id") or run.get("revision_request_sha256") != sha256_json(request):
        raise ValueError("M10 attempt request does not match frozen governance authority")
    if parent_rejection is not None and parent_rejection.get("retryable") is not True:
        raise ValueError("M10 retry cannot follow a non-retryable rejection")
    if attempt_number == 1 and parent_rejection is not None:
        raise ValueError("M10 attempt one cannot have a parent rejection")
    if parent_rejection is not None and parent_rejection.get("rejected_content_sha256") == sha256_json(artifact):
        raise ValueError("M10 content-failure retry cannot reuse unchanged successor bytes")
    value: JsonObject = {
        "schema_version": "1.0", "record_type": "m10_candidate_attempt", "attempt_id": "PENDING",
        "run_id": run["run_id"], "attempt_number": attempt_number,
        "revision_request": _reference(str(request["request_id"]), request),
        "predecessor": {"id": f"predecessor_{sha256_json(predecessor)}", "sha256": sha256_json(predecessor)},
        "candidate": {"artifact_sha256": sha256_json(artifact), "audit_sha256": sha256_json(audit), "content_sha256": sha256_json(artifact)},
        "capture": _reference(str(capture["capture_id"]), capture), "content_lifecycle_status": "UNREVIEWED",
        "development_approved": False,
        "provider_authenticated": False, "created_at": created_at,
    }
    if parent_rejection is not None:
        value["parent_rejection"] = _reference(str(parent_rejection["rejection_id"]), parent_rejection)
    value["attempt_id"] = identity("m10attempt", value, "attempt_id")
    validate_instance(value, "m10-candidate-attempt")
    return value


def build_receipts(*, run: Mapping[str, Any], attempt: Mapping[str, Any], stage_issues: Mapping[str, Iterable[RevisionIssue]], reviewed_at: str) -> tuple[JsonObject, ...]:
    """Build all six ordered receipts and short-circuit after first failure."""
    failed = False
    receipts: list[JsonObject] = []
    for stage, order in STAGE_CONTRACT:
        issues = tuple(stage_issues.get(stage, ()))
        outcome = "NOT_RUN" if failed else ("FAIL" if issues else "PASS")
        value: JsonObject = {"schema_version": "1.0", "record_type": "m10_verification_receipt", "receipt_id": "PENDING", "run_id": run["run_id"], "attempt_id": attempt["attempt_id"], "attempt_number": attempt["attempt_number"], "stage": stage, "stage_order": order, "outcome": outcome, "issues": [issue.as_dict() for issue in issues] if not failed else [], "reviewer": "m10_static_validator", "reviewed_at": reviewed_at}
        value["receipt_id"] = identity("m10receipt", value, "receipt_id")
        validate_instance(value, "m10-verification-receipt")
        receipts.append(value)
        failed = failed or outcome in {"FAIL", "ERROR"}
    return tuple(receipts)


def build_rejection(*, run: Mapping[str, Any], attempt: Mapping[str, Any], receipts: Iterable[Mapping[str, Any]], rejected_at: str) -> JsonObject:
    """Publish complete failed-receipt binding and deterministic retry decision."""
    all_receipts = tuple(receipts)
    failed = [receipt for receipt in all_receipts if receipt.get("outcome") in {"FAIL", "ERROR"}]
    if not failed:
        raise ValueError("M10 rejection requires a failed receipt")
    issues = [issue for receipt in failed for issue in receipt["issues"]]
    codes = {str(issue["code"]) for issue in issues}
    constraints = sorted({f"Repair {issue['code']} at {issue['path']}: {issue['message']}" for issue in issues})
    remaining = int(run["maximum_attempts"]) - int(attempt["attempt_number"])
    retryable = remaining > 0 and not bool(codes & NON_RETRYABLE_CODES)
    value: JsonObject = {"schema_version": "1.0", "record_type": "m10_rejection", "rejection_id": "PENDING", "run_id": run["run_id"], "attempt": _reference(str(attempt["attempt_id"]), attempt), "rejected_content_sha256": attempt["candidate"]["content_sha256"], "receipt_hashes": [sha256_json(receipt) for receipt in all_receipts], "blocking_issues": issues, "repair_constraints": constraints, "repair_constraints_sha256": sha256_json(constraints), "retryable": retryable, "remaining_attempts": remaining, "rejected_at": rejected_at, "content_lifecycle_status": "UNREVIEWED", "development_approved": False, "provider_authenticated": False}
    value["rejection_id"] = identity("m10reject", value, "rejection_id")
    validate_instance(value, "m10-rejection")
    return value


def build_operational_failure(*, run: Mapping[str, Any], stage: str, error_code: str, message: str, failed_at: str, attempt: Mapping[str, Any] | None = None) -> JsonObject:
    """Record a truthful terminal operational failure without an approval claim."""
    value: JsonObject = {"schema_version": "1.0", "record_type": "m10_operational_failure", "failure_id": "PENDING", "run_id": run["run_id"], "stage": stage, "error_code": error_code, "message": message, "failed_at": failed_at, "content_lifecycle_status": "UNREVIEWED", "development_approved": False, "provider_authenticated": False}
    if attempt is not None:
        value["attempt_id"] = attempt["attempt_id"]
    value["failure_id"] = identity("m10failure", value, "failure_id")
    validate_instance(value, "m10-operational-failure")
    return value
