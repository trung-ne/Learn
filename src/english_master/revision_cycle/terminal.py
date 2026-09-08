"""M10 terminal-manifest construction and strict readiness boundaries."""
from __future__ import annotations

from collections.abc import Iterable, Mapping
from typing import Any

from english_master.lesson_generation.canonical import identity, sha256_json
from english_master.schema_validation import validate_instance

JsonObject = dict[str, Any]


def _as_map(values: Mapping[str, Mapping[str, Any]] | Iterable[Mapping[str, Any]], key: str) -> dict[str, Mapping[str, Any]]:
    if isinstance(values, Mapping):
        return dict(values)
    return {str(value[key]): value for value in values}


def _is_test_capture(value: Mapping[str, Any]) -> bool:
    capture = value.get("capture")
    if not isinstance(capture, Mapping):
        return True
    if capture.get("capture_mode") == "TEST_ONLY":
        return True
    for key in ("provider", "model", "execution_id"):
        item = capture.get(key)
        if isinstance(item, str) and item.upper().startswith("TEST_"):
            return True
    return False


def _request_reference(request: Mapping[str, Any]) -> JsonObject:
    request_id = str(request["request_id"])
    return {
        "request_id": request_id,
        "path": f"requests/{request_id.split('_', 1)[1][:16]}.json",
        "sha256": sha256_json(request),
    }


def _required_kinds(request: Mapping[str, Any]) -> set[str]:
    target = request.get("target_milestone")
    if target == "M6":
        return {"M6_SUCCESSOR_BATCH", "M7_SUCCESSOR_BATCH", "M8_2_SUCCESSOR_PILOT"}
    if target == "M7":
        return {"M7_SUCCESSOR_BATCH"}
    if target == "M8_2":
        return {"M8_2_SUCCESSOR_PILOT"}
    raise ValueError(f"unsupported M10 revision target: {target!r}")


def build_revision_manifest(
    *,
    finding_batch: Mapping[str, Any],
    finding_batch_path: str,
    revision_requests: Mapping[str, Mapping[str, Any]] | Iterable[Mapping[str, Any]],
    review_inputs: Mapping[str, Mapping[str, Any]] | Iterable[Mapping[str, Any]],
    dispositions: Iterable[Mapping[str, Any]],
    terminal_state: str,
    created_at: str,
) -> JsonObject:
    """Build a non-promotable M10 terminal manifest.

    A ``READY_FOR_FRESH_M9`` result requires non-test failure evidence and
    resolved successor bindings; this function does not run M9 or approve content.
    """
    validate_instance(dict(finding_batch), "m10-finding-batch")
    if finding_batch.get("batch_id") != identity("m10findings", finding_batch, "batch_id"):
        raise ValueError("M10 finding-batch identity does not reconstruct")
    requests = _as_map(revision_requests, "request_id")
    inputs = _as_map(review_inputs, "input_id")
    if not requests or not inputs:
        raise ValueError("M10 terminal manifest requires requests and imported inputs")
    for request_id, request in requests.items():
        validate_instance(dict(request), "m10-revision-request")
        if request_id != request.get("request_id") or request_id != identity("m10request", request, "request_id"):
            raise ValueError(f"M10 revision-request identity drift: {request_id}")
        for source in request.get("source_inputs", []):
            input_id = source.get("input_id") if isinstance(source, Mapping) else None
            item = inputs.get(str(input_id))
            if item is None or source.get("input_sha256") != sha256_json(item):
                raise ValueError(f"M10 revision request has unavailable input: {input_id}")
    ordered_dispositions = [dict(item) for item in dispositions]
    disposition_ids = [str(item.get("request_id")) for item in ordered_dispositions]
    if set(disposition_ids) != set(requests) or len(disposition_ids) != len(set(disposition_ids)):
        raise ValueError("M10 dispositions must cover each revision request exactly once")
    for item in ordered_dispositions:
        request = requests[str(item["request_id"])]
        if item.get("request_sha256") != sha256_json(request):
            raise ValueError("M10 disposition request hash does not match its immutable revision request")
    if terminal_state == "READY_FOR_FRESH_M9":
        if any(_is_test_capture(item) for item in inputs.values()):
            raise ValueError("TEST_ONLY evidence cannot establish READY_FOR_FRESH_M9")
        for item in ordered_dispositions:
            request = requests[str(item["request_id"])]
            if item.get("status") != "RESOLVED":
                raise ValueError("READY_FOR_FRESH_M9 requires every request resolved")
            evidence = item.get("successor_evidence")
            if not isinstance(evidence, list):
                raise ValueError("resolved M10 request requires successor evidence")
            kinds = {entry.get("kind") for entry in evidence if isinstance(entry, Mapping)}
            missing = _required_kinds(request) - kinds
            if missing:
                raise ValueError(f"resolved M10 request lacks successor evidence: {sorted(missing)}")
    elif terminal_state == "ESCALATED":
        if any(item.get("status") != "ESCALATED" for item in ordered_dispositions):
            raise ValueError("ESCALATED requires every request to be escalated")
        if any(item.get("successor_evidence") for item in ordered_dispositions):
            raise ValueError("ESCALATED must not claim successor evidence")
    elif terminal_state == "RETRY_EXHAUSTED":
        if any(item.get("status") != "RETRY_EXHAUSTED" for item in ordered_dispositions):
            raise ValueError("RETRY_EXHAUSTED requires every request to exhaust retries")
    value: JsonObject = {
        "schema_version": "1.0",
        "record_type": "m10_revision_manifest",
        "manifest_id": "PENDING",
        "terminal_state": terminal_state,
        "finding_batch": {"path": finding_batch_path, "sha256": sha256_json(finding_batch)},
        "revision_requests": [_request_reference(request) for _, request in sorted(requests.items())],
        "dispositions": sorted(ordered_dispositions, key=lambda item: str(item["request_id"])),
        "created_at": created_at,
        "fresh_m9_required": True,
        "content_lifecycle_status": "UNREVIEWED",
        "development_approved": False,
        "provider_authenticated": False,
        "limitations": [
            "M10 does not approve generated content, human review, release approval, or provider authentication.",
            "A new M9 selection, machine reports, and independent AI captures are required for successor hashes.",
        ],
    }
    value["manifest_id"] = identity("m10manifest", value, "manifest_id")
    validate_instance(value, "m10-revision-manifest")
    return value


def validate_revision_manifest(
    value: Mapping[str, Any], *, finding_batch: Mapping[str, Any], revision_requests: Mapping[str, Mapping[str, Any]] | Iterable[Mapping[str, Any]], review_inputs: Mapping[str, Mapping[str, Any]] | Iterable[Mapping[str, Any]],
) -> tuple[str, ...]:
    """Return deterministic errors without interpreting M10 as approval evidence."""
    try:
        rebuilt = build_revision_manifest(
            finding_batch=finding_batch,
            finding_batch_path=str(value.get("finding_batch", {}).get("path", "")) if isinstance(value.get("finding_batch"), Mapping) else "",
            revision_requests=revision_requests,
            review_inputs=review_inputs,
            dispositions=value.get("dispositions", []) if isinstance(value.get("dispositions"), list) else [],
            terminal_state=str(value.get("terminal_state", "")),
            created_at=str(value.get("created_at", "")),
        )
    except (ValueError, TypeError) as error:
        return (str(error),)
    if dict(value) != rebuilt:
        return ("M10 terminal manifest does not reconstruct canonically",)
    return ()
