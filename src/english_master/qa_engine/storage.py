"""Atomic no-overwrite publication for complete M8 terminal runs."""
from __future__ import annotations

import copy
import shutil
import tempfile
from pathlib import Path
from typing import TYPE_CHECKING, Any, Mapping, Sequence

from english_master.lesson_generation.canonical import identity, sha256_json
from english_master.lesson_generation.storage import (
    _fsync_directory,
    _publish_bundle,
    _rename_directory_noreplace,
)
from english_master.schema_validation import validate_instance

if TYPE_CHECKING:
    from .authority import VerifiedM7QaAuthority


def _terminal_state(
    decision: Mapping[str, Any] | None,
    rejections: Sequence[Mapping[str, Any]],
    operational_failures: Sequence[Mapping[str, Any]],
) -> tuple[str, str]:
    if decision is not None:
        if operational_failures:
            raise ValueError("approved run cannot also contain operational failures")
        return "DEVELOPMENT_APPROVED", str(decision["decided_at"])
    if operational_failures:
        return "OPERATIONAL_FAILURE", str(operational_failures[-1]["occurred_at"])
    if rejections:
        return "REJECTED", str(rejections[-1]["rejected_at"])
    raise ValueError("run has no terminal decision, rejection, or operational failure")


def build_manifest(
    request: Mapping[str, Any],
    files: Mapping[str, Any],
    *,
    terminal_state: str,
    terminal_at: str,
) -> dict[str, Any]:
    value: dict[str, Any] = {
        "schema_version": "1.0",
        "record_type": "qa_engine_run_manifest",
        "run_manifest_id": "PENDING",
        "engine_run_id": request["engine_run_id"],
        "terminal_state": terminal_state,
        "request_sha256": sha256_json(request),
        "files": [
            {"path": path, "sha256": sha256_json(files[path])}
            for path in sorted(files)
        ],
        "terminal_at": terminal_at,
        "content_lifecycle_status": "UNREVIEWED",
        "human_reviewed": False,
        "release_approved": False,
        "limitations": [
            "This manifest inventories internally consistent M8 development evidence only.",
            "It does not authenticate a provider, establish human review, or authorize release.",
        ],
    }
    value["run_manifest_id"] = identity("qaemanifest", value, "run_manifest_id")
    validate_instance(value, "qa-engine-run-manifest")
    return value


def publish_run(
    output_directory: Path,
    *,
    authority: "VerifiedM7QaAuthority",
    request: Mapping[str, Any],
    attempts: Sequence[Mapping[str, Any]],
    receipts: Sequence[Sequence[Mapping[str, Any]]],
    rejections: Sequence[Mapping[str, Any]],
    decision: Mapping[str, Any] | None,
    invocations: Sequence[Mapping[str, Any]] = (),
    ai_reviews: Sequence[Mapping[str, Any]] = (),
    operational_failures: Sequence[Mapping[str, Any]] = (),
) -> tuple[Path, ...]:
    if len(attempts) != len(receipts):
        raise ValueError("every candidate attempt must have exactly one receipt group")
    files: dict[str, Any] = {"request.json": copy.deepcopy(dict(request))}
    for index, (attempt, attempt_receipts) in enumerate(zip(attempts, receipts), 1):
        if len(attempt_receipts) != 6:
            raise ValueError("every published candidate attempt requires six receipts")
        receipt_keys = {(item.get("sequence"), item.get("stage")) for item in attempt_receipts}
        if len(receipt_keys) != 6:
            raise ValueError("published receipt stages and sequences must be unique")
        prefix = f"attempt-{index:03d}"
        files[f"{prefix}-candidate-attempt.json"] = copy.deepcopy(dict(attempt))
        for receipt in attempt_receipts:
            files[
                f"{prefix}-receipt-{receipt['sequence']:02d}-{receipt['stage'].lower()}.json"
            ] = copy.deepcopy(dict(receipt))
    for index, rejection in enumerate(rejections, 1):
        files[f"rejection-{index:03d}.json"] = copy.deepcopy(dict(rejection))
    for invocation in invocations:
        invocation_id = invocation.get("invocation_id")
        if not isinstance(invocation_id, str):
            raise ValueError("published invocation requires invocation_id")
        files[f"invocation-{invocation_id}.json"] = copy.deepcopy(dict(invocation))
    for review in ai_reviews:
        review_id = review.get("ai_review_id")
        if not isinstance(review_id, str):
            raise ValueError("published AI review requires ai_review_id")
        files[f"ai-review-{review_id}.json"] = copy.deepcopy(dict(review))
    for failure in operational_failures:
        failure_id = failure.get("operational_failure_id")
        if not isinstance(failure_id, str):
            raise ValueError("published operational failure requires operational_failure_id")
        files[f"operational-failure-{failure_id}.json"] = copy.deepcopy(dict(failure))
    if decision is not None:
        files["decision.json"] = copy.deepcopy(dict(decision))
    state, terminal_at = _terminal_state(decision, rejections, operational_failures)
    files["run-manifest.json"] = build_manifest(
        request,
        files,
        terminal_state=state,
        terminal_at=terminal_at,
    )
    output_directory.parent.mkdir(parents=True, exist_ok=True)
    staging_root = Path(
        tempfile.mkdtemp(
            prefix=f".{output_directory.name}.verified.", dir=output_directory.parent
        )
    )
    staged_bundle = staging_root / "bundle"
    try:
        _publish_bundle(staged_bundle, files)
        from .verification import verify_run

        verify_run(staged_bundle, authority)
        _rename_directory_noreplace(staged_bundle, output_directory)
        try:
            _fsync_directory(output_directory.parent)
        except OSError:
            pass
    except BaseException:
        shutil.rmtree(staging_root, ignore_errors=True)
        raise
    shutil.rmtree(staging_root, ignore_errors=True)
    return tuple(output_directory / name for name in sorted(files))
