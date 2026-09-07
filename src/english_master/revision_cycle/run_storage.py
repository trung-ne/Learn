"""Atomic storage and read-only verification for closed M10 governance runs."""
from __future__ import annotations

import json
import shutil
import uuid
from collections.abc import Iterable, Mapping
from pathlib import Path
from typing import Any

from english_master.curriculum_review.loading import load_strict_document
from english_master.independent_review.storage import _write
from english_master.lesson_generation.canonical import identity, sha256_json, sha256_text
from english_master.lesson_generation.storage import _fsync_directory, _rename_directory_noreplace
from english_master.schema_validation import _unique_json_object, validate_instance

from .models import NON_RETRYABLE_CODES, STAGE_CONTRACT

JsonObject = dict[str, Any]
_REQUIRED_PAYLOAD_KEYS = frozenset({"prompt", "raw_response", "artifact", "audit", "closure"})


def _token(value: str) -> str:
    return value.split("_", 1)[-1][:16]


def _verify_records(
    run: Mapping[str, Any],
    attempts: Iterable[Mapping[str, Any]],
    captures: Iterable[Mapping[str, Any]],
    receipts: Iterable[Mapping[str, Any]],
    rejections: Iterable[Mapping[str, Any]],
) -> None:
    validate_instance(dict(run), "m10-governance-run")
    if run.get("run_id") != identity("m10run", run, "run_id"):
        raise ValueError("M10 governance run identity drift")
    captures_by_id: dict[str, Mapping[str, Any]] = {}
    for capture in captures:
        validate_instance(dict(capture), "m10-regeneration-capture")
        capture_id = str(capture.get("capture_id"))
        if capture_id in captures_by_id:
            raise ValueError("M10 duplicate capture identity")
        if capture.get("run_id") != run.get("run_id") or capture.get("capture_id") != identity("m10capture", capture, "capture_id"):
            raise ValueError("M10 capture binding or identity drift")
        captures_by_id[str(capture["capture_id"])] = capture
    attempts_by_id: dict[str, Mapping[str, Any]] = {}
    attempt_numbers: set[int] = set()
    for attempt in attempts:
        validate_instance(dict(attempt), "m10-candidate-attempt")
        attempt_id = str(attempt.get("attempt_id"))
        if attempt_id in attempts_by_id:
            raise ValueError("M10 duplicate attempt identity")
        if attempt.get("run_id") != run.get("run_id") or attempt.get("attempt_id") != identity("m10attempt", attempt, "attempt_id"):
            raise ValueError("M10 attempt binding or identity drift")
        number = int(attempt["attempt_number"])
        if number > int(run["maximum_attempts"]) or number in attempt_numbers:
            raise ValueError("M10 attempt sequence drift")
        attempt_numbers.add(number)
        reference = attempt.get("capture")
        capture = captures_by_id.get(str(reference.get("id"))) if isinstance(reference, Mapping) else None
        if capture is None or reference.get("sha256") != sha256_json(capture):
            raise ValueError("M10 attempt does not bind a stored capture")
        if capture.get("attempt_number") != number:
            raise ValueError("M10 capture attempt number drift")
        attempts_by_id[str(attempt["attempt_id"])] = attempt
    if attempt_numbers and attempt_numbers != set(range(1, len(attempt_numbers) + 1)):
        raise ValueError("M10 attempt numbers must be contiguous from one")
    rejections_by_attempt: dict[str, Mapping[str, Any]] = {}
    for rejection in rejections:
        validate_instance(dict(rejection), "m10-rejection")
        if rejection.get("run_id") != run.get("run_id") or rejection.get("rejection_id") != identity("m10reject", rejection, "rejection_id"):
            raise ValueError("M10 rejection binding or identity drift")
        ref = rejection.get("attempt", {})
        attempt = attempts_by_id.get(str(ref.get("id"))) if isinstance(ref, Mapping) else None
        if attempt is None or ref.get("sha256") != sha256_json(attempt):
            raise ValueError("M10 rejection does not bind an attempt")
        attempt_id = str(attempt["attempt_id"])
        if attempt_id in rejections_by_attempt:
            raise ValueError("M10 attempt has duplicate rejections")
        rejections_by_attempt[attempt_id] = rejection
    by_attempt: dict[str, list[Mapping[str, Any]]] = {}
    receipt_ids: set[str] = set()
    for receipt in receipts:
        validate_instance(dict(receipt), "m10-verification-receipt")
        receipt_id = str(receipt.get("receipt_id"))
        if receipt_id in receipt_ids:
            raise ValueError("M10 duplicate receipt identity")
        receipt_ids.add(receipt_id)
        if receipt.get("run_id") != run.get("run_id") or receipt.get("receipt_id") != identity("m10receipt", receipt, "receipt_id"):
            raise ValueError("M10 receipt binding or identity drift")
        attempt = attempts_by_id.get(str(receipt.get("attempt_id")))
        if attempt is None or receipt.get("attempt_number") != attempt.get("attempt_number"):
            raise ValueError("M10 receipt attempt binding drift")
        by_attempt.setdefault(str(receipt["attempt_id"]), []).append(receipt)
    for attempt_id in attempts_by_id:
        if attempt_id not in by_attempt:
            raise ValueError("M10 attempt has no receipt group")
    for attempt_id, attempt_receipts in by_attempt.items():
        if attempt_id not in attempts_by_id or len(attempt_receipts) != len(STAGE_CONTRACT):
            raise ValueError("M10 receipt inventory is incomplete")
        ordered = sorted(attempt_receipts, key=lambda item: int(item["stage_order"]))
        if [(item["stage"], item["stage_order"]) for item in ordered] != list(STAGE_CONTRACT):
            raise ValueError("M10 receipt ordering drift")
        outcomes = [item["outcome"] for item in ordered]
        if "FAIL" in outcomes or "ERROR" in outcomes:
            first = next(index for index, outcome in enumerate(outcomes) if outcome in {"FAIL", "ERROR"})
        failed_receipts = [receipt for receipt in ordered if receipt["outcome"] in {"FAIL", "ERROR"}]
        rejection = rejections_by_attempt.get(attempt_id)
        if failed_receipts and rejection is None:
            raise ValueError("M10 failed attempt has no immutable rejection")
        if not failed_receipts and rejection is not None:
            raise ValueError("M10 passing attempt must not have a rejection")
        if rejection is not None:
            expected_hashes = [sha256_json(receipt) for receipt in ordered]
            expected_issues = [issue for receipt in failed_receipts for issue in receipt["issues"]]
            expected_constraints = sorted(
                {
                    f"Repair {issue['code']} at {issue['path']}: {issue['message']}"
                    for issue in expected_issues
                }
            )
            expected_remaining = int(run["maximum_attempts"]) - int(attempts_by_id[attempt_id]["attempt_number"])
            expected_retryable = expected_remaining > 0 and not any(
                issue["code"] in NON_RETRYABLE_CODES
                for issue in expected_issues
            )
            if (
                rejection.get("receipt_hashes") != expected_hashes
                or rejection.get("blocking_issues") != expected_issues
                or rejection.get("repair_constraints") != expected_constraints
                or rejection.get("repair_constraints_sha256") != sha256_json(expected_constraints)
                or rejection.get("rejected_content_sha256") != attempts_by_id[attempt_id]["candidate"]["content_sha256"]
                or rejection.get("remaining_attempts") != expected_remaining
                or rejection.get("retryable") is not expected_retryable
            ):
                raise ValueError("M10 rejection receipt or retry decision drift")
    if set(rejections_by_attempt) - set(by_attempt):
        raise ValueError("M10 rejection has no receipt inventory")
    for number in sorted(attempt_numbers):
        attempt = next(item for item in attempts_by_id.values() if item["attempt_number"] == number)
        if attempt.get("predecessor") != {
            "id": f"predecessor_{sha256_json(run['predecessor'])}",
            "sha256": sha256_json(run["predecessor"]),
        }:
            raise ValueError("M10 attempt predecessor drift")
        parent = attempt.get("parent_rejection")
        if number == 1:
            if parent is not None:
                raise ValueError("M10 attempt one cannot bind a parent rejection")
            continue
        prior = next(item for item in attempts_by_id.values() if item["attempt_number"] == number - 1)
        rejection = rejections_by_attempt.get(str(prior["attempt_id"]))
        if rejection is None or rejection.get("retryable") is not True:
            raise ValueError("M10 retry does not follow a retryable prior rejection")
        expected_parent = {"id": rejection["rejection_id"], "sha256": sha256_json(rejection)}
        if parent != expected_parent:
            raise ValueError("M10 retry parent-rejection lineage drift")
    referenced_captures = {str(attempt["capture"]["id"]) for attempt in attempts_by_id.values()}
    if referenced_captures != set(captures_by_id):
        raise ValueError("M10 capture inventory is not closed")


def _verify_payloads(
    attempts: Iterable[Mapping[str, Any]],
    captures: Iterable[Mapping[str, Any]],
    payloads: Mapping[str, Mapping[str, Any]],
) -> None:
    captures_by_id = {str(capture["capture_id"]): capture for capture in captures}
    for attempt in attempts:
        attempt_id = str(attempt["attempt_id"])
        payload = payloads.get(attempt_id)
        if not isinstance(payload, Mapping) or set(payload) != _REQUIRED_PAYLOAD_KEYS:
            raise ValueError("M10 attempt payload inventory is incomplete")
        prompt, response = payload["prompt"], payload["raw_response"]
        if not isinstance(prompt, str) or not isinstance(response, Mapping):
            raise ValueError("M10 prompt or raw response has invalid type")
        capture_ref = attempt["capture"]
        capture = captures_by_id[str(capture_ref["id"])]
        if capture["prompt_sha256"] != sha256_text(prompt) or capture["raw_response_sha256"] != sha256_json(response):
            raise ValueError("M10 stored prompt or raw response hash drift")
        candidate = attempt["candidate"]
        if candidate["artifact_sha256"] != sha256_json(payload["artifact"]) or candidate["audit_sha256"] != sha256_json(payload["audit"]):
            raise ValueError("M10 stored candidate payload hash drift")



def _verify_terminal_state(
    run: Mapping[str, Any],
    attempts: Iterable[Mapping[str, Any]],
    receipts: Iterable[Mapping[str, Any]],
    rejections: Iterable[Mapping[str, Any]],
    operational_failures: Iterable[Mapping[str, Any]],
    manifest: Mapping[str, Any],
) -> None:
    validate_instance(dict(manifest), "m10-revision-manifest")
    if manifest.get("manifest_id") != identity("m10manifest", manifest, "manifest_id"):
        raise ValueError("M10 terminal manifest identity drift")
    finding = manifest.get("finding_batch")
    requests = manifest.get("revision_requests")
    if not isinstance(finding, Mapping) or finding.get("sha256") != run.get("finding_batch_sha256"):
        raise ValueError("M10 terminal manifest finding-batch binding drift")
    if not isinstance(requests, list) or len(requests) != 1:
        raise ValueError("M10 governance terminal manifest must bind one frozen request")
    request = requests[0]
    if not isinstance(request, Mapping) or request.get("request_id") != run.get("revision_request_id") or request.get("sha256") != run.get("revision_request_sha256"):
        raise ValueError("M10 terminal manifest request binding drift")
    attempts = tuple(attempts)
    receipts = tuple(receipts)
    rejections = tuple(rejections)
    operational_failures = tuple(operational_failures)
    state = manifest.get("terminal_state")
    if state == "READY_FOR_FRESH_M9":
        if not attempts or rejections or operational_failures or any(receipt.get("outcome") != "PASS" for receipt in receipts):
            raise ValueError("M10 readiness terminal state does not match static evidence")
    elif state == "RETRY_EXHAUSTED":
        if operational_failures or len(attempts) != int(run["maximum_attempts"]) or len(rejections) != len(attempts):
            raise ValueError("M10 retry-exhausted terminal state does not match attempt evidence")
        final = max(attempts, key=lambda item: int(item["attempt_number"]))
        final_rejection = next(item for item in rejections if item["attempt"]["id"] == final["attempt_id"])
        if final_rejection.get("retryable") is not False or final_rejection.get("remaining_attempts") != 0:
            raise ValueError("M10 retry-exhausted terminal state lacks exhausted final rejection")
    elif state == "ESCALATED":
        if operational_failures or not rejections or not any(rejection.get("retryable") is False for rejection in rejections):
            raise ValueError("M10 escalated terminal state lacks non-retryable rejection")
    elif state == "OPERATIONAL_FAILURE":
        if not operational_failures:
            raise ValueError("M10 operational terminal state lacks failure evidence")
    else:
        raise ValueError("M10 terminal state is unsupported")

def publish_governance_run(
    directory: Path,
    *,
    run: Mapping[str, Any],
    attempts: Iterable[Mapping[str, Any]],
    captures: Iterable[Mapping[str, Any]],
    receipts: Iterable[Mapping[str, Any]],
    rejections: Iterable[Mapping[str, Any]],
    terminal_manifest: Mapping[str, Any],
    payloads: Mapping[str, Mapping[str, Any]],
    operational_failures: Iterable[Mapping[str, Any]] = (),
) -> Path:
    """Stage a fully evidenced run, reverify it, then atomically publish it."""
    attempts, captures, receipts = tuple(attempts), tuple(captures), tuple(receipts)
    rejections, operational_failures = tuple(rejections), tuple(operational_failures)
    _verify_records(run, attempts, captures, receipts, rejections)
    _verify_payloads(attempts, captures, payloads)
    for failure in operational_failures:
        validate_instance(dict(failure), "m10-operational-failure")
        if failure.get("run_id") != run.get("run_id") or failure.get("failure_id") != identity("m10failure", failure, "failure_id"):
            raise ValueError("M10 operational failure binding or identity drift")
    _verify_terminal_state(run, attempts, receipts, rejections, operational_failures, terminal_manifest)
    destination = directory.absolute()
    if destination.exists() or destination.is_symlink():
        raise FileExistsError(f"immutable M10 governance directory already exists: {destination}")
    if any(ancestor.is_symlink() for ancestor in destination.parents):
        raise ValueError("M10 governance destination has a link-like ancestor")
    stage = destination.parent / f".{destination.name}.staging-{uuid.uuid4().hex}"
    try:
        stage.mkdir(parents=True, exist_ok=False)
        _write(stage / "run.json", run)
        _write(stage / "terminal-manifest.json", terminal_manifest)
        for capture in captures:
            _write(stage / "captures" / f"{_token(str(capture['capture_id']))}.json", capture)
        for attempt in attempts:
            token = _token(str(attempt["attempt_id"]))
            _write(stage / "attempts" / f"{token}.json", attempt)
            payload = payloads[str(attempt["attempt_id"])]
            target = stage / "payloads" / token
            target.mkdir(parents=True, exist_ok=False)
            (target / "prompt.txt").write_text(str(payload["prompt"]), encoding="utf-8", newline="\n")
            for key in ("raw_response", "artifact", "audit", "closure"):
                _write(target / f"{key}.json", payload[key])
        for receipt in receipts:
            _write(stage / "receipts" / f"{_token(str(receipt['receipt_id']))}.json", receipt)
        for rejection in rejections:
            _write(stage / "rejections" / f"{_token(str(rejection['rejection_id']))}.json", rejection)
        for failure in operational_failures:
            _write(stage / "operational-failures" / f"{_token(str(failure['failure_id']))}.json", failure)
        verify_governance_run(stage)
        for child in (stage / "captures", stage / "attempts", stage / "payloads", stage / "receipts", stage / "rejections", stage / "operational-failures", stage):
            if child.exists():
                _fsync_directory(child)
        _rename_directory_noreplace(stage, destination)
        _fsync_directory(destination.parent)
        return destination
    except BaseException:
        if stage.exists() or stage.is_symlink():
            shutil.rmtree(stage, ignore_errors=True)
        raise


def verify_governance_run(directory: Path) -> JsonObject:
    """Read-only full inventory validation; reject links, extras, and hash drift."""
    if directory.is_symlink():
        raise ValueError("M10 governance run must not be a symlink")
    root = directory.resolve(strict=True)
    if not root.is_dir() or root.is_symlink():
        raise ValueError("M10 governance run must be a real directory")
    expected = {"run.json", "terminal-manifest.json"}
    record_directories = {"captures", "attempts", "receipts", "rejections", "operational-failures"}
    permitted_root_entries = expected | record_directories | {"payloads"}
    for child in root.iterdir():
        if child.name not in permitted_root_entries:
            raise ValueError(f"M10 governance run contains unexpected root entry: {child.name}")
    values: dict[str, list[Mapping[str, Any]]] = {"captures": [], "attempts": [], "receipts": [], "rejections": [], "operational-failures": []}
    for path in root.rglob("*"):
        if path.is_symlink() or (path.exists() and not path.is_dir() and not path.is_file()):
            raise ValueError(f"M10 governance run contains unsafe path: {path}")
        if path.is_file():
            relative = path.relative_to(root).as_posix()
            expected_payload = relative.startswith("payloads/") and relative.count("/") == 2 and relative.rsplit("/", 1)[-1] in {"prompt.txt", "raw_response.json", "artifact.json", "audit.json", "closure.json"}
            expected_record = (
                relative.count("/") == 1
                and relative.rsplit("/", 1)[0] in values
                and relative.endswith(".json")
            )
            if relative not in expected and not expected_payload and not expected_record:
                raise ValueError(f"M10 governance run contains orphan file: {relative}")
    run = load_strict_document(root / "run.json")
    if not isinstance(run, dict):
        raise ValueError("M10 run record must be an object")
    for name in values:
        for path in sorted((root / name).glob("*.json")) if (root / name).exists() else []:
            value = load_strict_document(path)
            if not isinstance(value, dict):
                raise ValueError(f"M10 {name} record must be an object")
            values[name].append(value)
    _verify_records(run, values["attempts"], values["captures"], values["receipts"], values["rejections"])
    payloads: dict[str, Mapping[str, Any]] = {}
    for attempt in values["attempts"]:
        token = _token(str(attempt["attempt_id"]))
        payload_root = root / "payloads" / token
        if not payload_root.is_dir():
            raise ValueError("M10 attempt payload directory is missing")
        files = {path.name for path in payload_root.iterdir() if path.is_file()}
        if files != {"prompt.txt", "raw_response.json", "artifact.json", "audit.json", "closure.json"}:
            raise ValueError("M10 attempt payload directory is not closed")
        payloads[str(attempt["attempt_id"])] = {
            "prompt": (payload_root / "prompt.txt").read_text(encoding="utf-8"),
            "raw_response": load_strict_document(payload_root / "raw_response.json"),
            "artifact": load_strict_document(payload_root / "artifact.json"),
            "audit": load_strict_document(payload_root / "audit.json"),
            "closure": json.loads((payload_root / "closure.json").read_text(encoding="utf-8"), object_pairs_hook=_unique_json_object),
        }
    payload_directory = root / "payloads"
    stored_payload_tokens = {path.name for path in payload_directory.iterdir()} if payload_directory.exists() else set()
    expected_payload_tokens = {_token(str(attempt["attempt_id"])) for attempt in values["attempts"]}
    if stored_payload_tokens != expected_payload_tokens:
        raise ValueError("M10 payload directory inventory is not closed")
    _verify_payloads(values["attempts"], values["captures"], payloads)
    for failure in values["operational-failures"]:
        validate_instance(dict(failure), "m10-operational-failure")
        if failure.get("run_id") != run.get("run_id") or failure.get("failure_id") != identity("m10failure", failure, "failure_id"):
            raise ValueError("M10 operational failure binding or identity drift")
    manifest = load_strict_document(root / "terminal-manifest.json")
    if not isinstance(manifest, dict):
        raise ValueError("M10 terminal manifest must be an object")
    _verify_terminal_state(run, values["attempts"], values["receipts"], values["rejections"], values["operational-failures"], manifest)
    return {"run": run, "terminal_manifest": manifest, "attempt_count": len(values["attempts"]), "capture_count": len(values["captures"]), "receipt_count": len(values["receipts"]), "rejection_count": len(values["rejections"]), "operational_failure_count": len(values["operational-failures"])}
