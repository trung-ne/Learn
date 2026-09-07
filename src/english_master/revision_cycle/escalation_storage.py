"""Atomic publication and offline verification for no-attempt M10 escalations."""
from __future__ import annotations

import json
import os
import shutil
import uuid
from collections.abc import Mapping
from pathlib import Path
from typing import Any

from english_master.curriculum_review.loading import load_strict_document
from english_master.independent_review.storage import _write
from english_master.lesson_generation.canonical import identity, sha256_json
from english_master.lesson_generation.storage import _fsync_directory, _rename_directory_noreplace
from english_master.schema_validation import _unique_json_object, validate_instance

from .escalation import build_authority_conflict_escalation, validate_authority_conflict_escalation
from .governance import build_governance_run
from .terminal import build_revision_manifest, validate_revision_manifest
from .verification import verify_finding_batch

JsonObject = dict[str, Any]


def _load_object(path: Path) -> JsonObject:
    value = load_strict_document(path)
    if not isinstance(value, dict):
        raise ValueError(f"M10 escalation record must be an object: {path}")
    return value


def _read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"), object_pairs_hook=_unique_json_object)


def _copy_finding_batch(source: Path, destination: Path) -> None:
    if source.is_symlink() or not source.is_dir():
        raise ValueError("M10 escalation finding batch must be a real directory")
    shutil.copytree(source, destination)


def publish_escalated_run(
    directory: Path,
    *,
    finding_directory: Path,
    selection: Mapping[str, Any],
    subjects: Mapping[str, Any],
    request: Mapping[str, Any],
    source_input: Mapping[str, Any],
    predecessor_lesson: Mapping[str, Any],
    authority_source: str,
    authority_record: Mapping[str, Any],
    maximum_attempts: int,
    policy_version: str,
    created_at: str,
) -> Path:
    """Publish an immutable escalation before any forbidden successor attempt."""
    finding_batch = verify_finding_batch(finding_directory, selection=selection, subjects=subjects)
    run = build_governance_run(
        finding_batch=finding_batch,
        request=request,
        predecessor=request["predecessor"],
        maximum_attempts=maximum_attempts,
        policy_version=policy_version,
        created_at=created_at,
    )
    escalation = build_authority_conflict_escalation(
        run=run,
        finding_batch=finding_batch,
        request=request,
        source_input=source_input,
        predecessor_lesson=predecessor_lesson,
        authority_source=authority_source,
        authority_record=authority_record,
        created_at=created_at,
    )
    manifest = build_revision_manifest(
        finding_batch=finding_batch,
        finding_batch_path="finding/finding-batch.json",
        revision_requests={str(request["request_id"]): request},
        review_inputs={str(source_input["input_id"]): source_input},
        dispositions=(
            {
                "request_id": request["request_id"],
                "request_sha256": sha256_json(request),
                "status": "ESCALATED",
                "unresolved_issues": [
                    "AUTHORITY_CONFLICT at /title: the mandatory title repair requires an M5 curriculum amendment outside M10 authority."
                ],
            },
        ),
        terminal_state="ESCALATED",
        created_at=created_at,
    )
    destination = directory.absolute()
    if destination.exists() or destination.is_symlink():
        raise FileExistsError(f"immutable M10 escalation directory already exists: {destination}")
    if any(parent.is_symlink() for parent in destination.parents):
        raise ValueError("M10 escalation destination has a link-like ancestor")
    stage = destination.parent / f".{destination.name}.staging-{uuid.uuid4().hex}"
    try:
        stage.mkdir(parents=True, exist_ok=False)
        _copy_finding_batch(finding_directory, stage / "finding")
        _write(stage / "requests" / f"{str(request['request_id']).split('_', 1)[1][:16]}.json", request)
        _write(stage / "run.json", run)
        _write(stage / "authority-record.json", authority_record)
        _write(stage / "predecessor-lesson.json", predecessor_lesson)
        _write(stage / "escalation.json", escalation)
        _write(stage / "terminal-manifest.json", manifest)
        verify_escalated_run(stage)
        for child in (stage / "finding", stage / "requests", stage):
            _fsync_directory(child)
        _rename_directory_noreplace(stage, destination)
        _fsync_directory(destination.parent)
        return destination
    except BaseException:
        if stage.exists() or stage.is_symlink():
            shutil.rmtree(stage, ignore_errors=True)
        raise


def verify_escalated_run(directory: Path) -> JsonObject:
    """Verify the closed no-attempt `ESCALATED` M10 state from stored bytes."""
    root = directory.absolute()
    if root.is_symlink() or not root.is_dir():
        raise ValueError("M10 escalation run must be a real directory")
    expected_root_files = {"run.json", "authority-record.json", "predecessor-lesson.json", "escalation.json", "terminal-manifest.json"}
    actual_root_files = {path.name for path in root.iterdir() if path.is_file()}
    if actual_root_files != expected_root_files:
        raise ValueError("M10 escalation root file inventory is not closed")
    if {path.name for path in root.iterdir() if path.is_dir()} != {"finding", "requests"}:
        raise ValueError("M10 escalation root directory inventory is not closed")
    for path in root.rglob("*"):
        if path.is_symlink() or (path.exists() and not path.is_dir() and not path.is_file()):
            raise ValueError(f"M10 escalation contains unsafe path: {path}")
    finding_root = root / "finding"
    finding_batch = _load_object(finding_root / "finding-batch.json")
    validate_instance(finding_batch, "m10-finding-batch")
    if finding_batch.get("batch_id") != identity("m10findings", finding_batch, "batch_id"):
        raise ValueError("M10 escalation finding-batch identity drift")
    expected_finding_paths = {"finding-batch.json"}
    inventory = finding_batch.get("inventory")
    if not isinstance(inventory, list):
        raise ValueError("M10 escalation finding batch inventory is invalid")
    for reference in inventory:
        if not isinstance(reference, Mapping):
            raise ValueError("M10 escalation finding batch inventory entry is invalid")
        path = str(reference.get("path", ""))
        value = _read_json(finding_root / path)
        if sha256_json(value) != reference.get("sha256"):
            raise ValueError("M10 escalation finding batch inventory hash drift")
        expected_finding_paths.add(path)
    actual_finding_paths = {path.relative_to(finding_root).as_posix() for path in finding_root.rglob("*") if path.is_file()}
    if actual_finding_paths != expected_finding_paths:
        raise ValueError("M10 escalation finding batch file inventory is not closed")
    request_paths = list((root / "requests").glob("*.json"))
    if len(request_paths) != 1:
        raise ValueError("M10 escalation must retain exactly one revision request")
    request = _load_object(request_paths[0])
    validate_instance(request, "m10-revision-request")
    if request.get("request_id") != identity("m10request", request, "request_id"):
        raise ValueError("M10 escalation revision-request identity drift")
    input_refs = finding_batch.get("review_inputs")
    if not isinstance(input_refs, list) or len(input_refs) != 1:
        raise ValueError("M10 escalation must retain exactly one actionable review input")
    source_path = finding_root / str(input_refs[0].get("path"))
    source_input = _load_object(source_path)
    if sha256_json(source_input) != input_refs[0].get("sha256"):
        raise ValueError("M10 escalation review-input hash drift")
    validate_instance(source_input, "m10-review-input")
    if source_input.get("input_id") != input_refs[0].get("path", "").split("/")[-1].split(".")[0] and source_input.get("input_id", "").split("_", 1)[-1][:16] not in source_path.name:
        raise ValueError("M10 escalation review-input path binding drift")
    run = _load_object(root / "run.json")
    validate_instance(run, "m10-governance-run")
    if run.get("run_id") != identity("m10run", run, "run_id"):
        raise ValueError("M10 escalation governance-run identity drift")
    if run.get("finding_batch_id") != finding_batch.get("batch_id") or run.get("finding_batch_sha256") != sha256_json(finding_batch):
        raise ValueError("M10 escalation governance finding-batch binding drift")
    if run.get("revision_request_id") != request.get("request_id") or run.get("revision_request_sha256") != sha256_json(request):
        raise ValueError("M10 escalation governance request binding drift")
    authority_record = _load_object(root / "authority-record.json")
    predecessor_lesson = _load_object(root / "predecessor-lesson.json")
    if request.get("predecessor", {}).get("artifact_sha256") != sha256_json(predecessor_lesson):
        raise ValueError("M10 escalation predecessor lesson hash drift")
    if predecessor_lesson.get("title") != authority_record.get("title"):
        raise ValueError("M10 escalation predecessor title does not match stored M5 authority record")
    escalation = _load_object(root / "escalation.json")
    issues = validate_authority_conflict_escalation(
        escalation,
        run=run,
        finding_batch=finding_batch,
        request=request,
        source_input=source_input,
        predecessor_lesson=predecessor_lesson,
        authority_record=authority_record,
    )
    if issues:
        raise ValueError("M10 escalation validation failed: " + "; ".join(issues))
    manifest = _load_object(root / "terminal-manifest.json")
    issues = validate_revision_manifest(
        manifest,
        finding_batch=finding_batch,
        revision_requests={str(request["request_id"]): request},
        review_inputs={str(source_input["input_id"]): source_input},
    )
    if issues:
        raise ValueError("M10 terminal manifest validation failed: " + "; ".join(issues))
    if manifest.get("terminal_state") != "ESCALATED":
        raise ValueError("M10 escalation must have ESCALATED terminal state")
    return {
        "terminal_state": "ESCALATED",
        "run_id": run["run_id"],
        "escalation_id": escalation["escalation_id"],
        "request_id": request["request_id"],
        "attempt_count": 0,
    }
