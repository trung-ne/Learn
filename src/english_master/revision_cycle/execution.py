"""Production-facing execution of one supplied M10 successor attempt.

This module never invokes a model or authors successor content.  It freezes an
immutable revision request, accepts an externally captured response, and uses
the existing M10 governance, adapter, and storage boundaries to validate and
publish a closed run.
"""
from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from english_master.lesson_generation.canonical import identity, sha256_json, sha256_text
from english_master.qa_engine.time import ensure_not_after
from english_master.schema_validation import validate_instance

from .adapters import StaticTargetAdapter, required_closure_issues
from .governance import build_governance_run, build_operational_failure
from .models import RegenerationCapture, RevisionIssue
from .orchestrator import RevisionOrchestrator
from .run_storage import publish_governance_run, verify_governance_run
from .successor_evidence import verify_successor_evidence

JsonObject = dict[str, Any]
_CAPTURE_KEYS = frozenset(
    {
        "capture_mode",
        "provider",
        "model",
        "execution_id",
        "parameters",
        "seed",
        "provider_authenticated",
        "prompt_sha256",
        "raw_response_sha256",
        "captured_at",
    }
)


@dataclass(frozen=True)
class SuppliedCaptureBackend:
    """One-shot backend over caller-supplied, already captured bytes and facts."""

    response: Mapping[str, Any]
    facts: Mapping[str, Any]

    def regenerate(
        self,
        prompt: str,
        *,
        parameters: Mapping[str, Any],
        seed: int | None,
    ) -> RegenerationCapture:
        if dict(parameters) != self.facts["parameters"] or seed != self.facts.get("seed"):
            raise ValueError("supplied M10 capture parameters or seed drift")
        return RegenerationCapture(
            content=self.response,
            capture_mode=str(self.facts["capture_mode"]),
            provider=str(self.facts["provider"]),
            model=str(self.facts["model"]),
            execution_id=str(self.facts["execution_id"]),
            parameters=dict(parameters),
            seed=seed,
            provider_authenticated=False,
        )


def _validate_authority(finding_batch: Mapping[str, Any], request: Mapping[str, Any]) -> None:
    validate_instance(dict(finding_batch), "m10-finding-batch")
    validate_instance(dict(request), "m10-revision-request")
    if finding_batch.get("batch_id") != identity("m10findings", finding_batch, "batch_id"):
        raise ValueError("M10 finding-batch identity drift")
    if request.get("request_id") != identity("m10request", request, "request_id"):
        raise ValueError("M10 revision-request identity drift")


def _validate_capture_facts(
    facts: Mapping[str, Any], *, prompt: str, response: Mapping[str, Any]
) -> None:
    if set(facts) != _CAPTURE_KEYS:
        raise ValueError("M10 supplied capture fact inventory is not closed")
    if facts.get("capture_mode") not in {"SESSION_CAPTURED", "PROVIDER_CAPTURED"}:
        raise ValueError("M10 execution requires a non-test factual capture mode")
    for key in ("provider", "model", "execution_id", "captured_at"):
        if not isinstance(facts.get(key), str) or not facts[key]:
            raise ValueError(f"M10 supplied capture {key} must be a non-empty string")
    if any(str(facts[key]).upper().startswith("TEST") for key in ("provider", "model", "execution_id")):
        raise ValueError("M10 execution rejects test-labelled capture facts")
    if not isinstance(facts.get("parameters"), dict):
        raise ValueError("M10 supplied capture parameters must be an object")
    if facts.get("seed") is not None and (
        isinstance(facts["seed"], bool) or not isinstance(facts["seed"], int)
    ):
        raise ValueError("M10 supplied capture seed must be an integer or null")
    if facts.get("provider_authenticated") is not False:
        raise ValueError("M10 capture input cannot claim provider authentication")
    if facts.get("prompt_sha256") != sha256_text(prompt):
        raise ValueError("M10 supplied capture prompt hash drift")
    if facts.get("raw_response_sha256") != sha256_json(response):
        raise ValueError("M10 supplied capture response hash drift")


def _successor_schema_issues(
    request: Mapping[str, Any], successor: Mapping[str, Any]
) -> tuple[RevisionIssue, ...]:
    issues: list[RevisionIssue] = []
    permitted = {"artifact", "audit", "closure", "successor_evidence"}
    if request.get("target_milestone") == "M8_2":
        permitted.add("pilot_artifact_count")
    unexpected = sorted(set(successor) - permitted)
    if unexpected:
        issues.append(RevisionIssue("SUCCESSOR_SCHEMA", "/", f"Unexpected supplied successor fields: {unexpected}."))
    for key in ("artifact", "audit"):
        if not isinstance(successor.get(key), Mapping):
            issues.append(RevisionIssue("SUCCESSOR_SCHEMA", f"/{key}", f"Supplied successor {key} must be an object."))
    evidence = successor.get("successor_evidence")
    if not isinstance(evidence, list) or not evidence:
        issues.append(RevisionIssue("SUCCESSOR_SCHEMA", "/successor_evidence", "Supplied successor evidence must be a non-empty array."))
    else:
        expected = {
            "M6": {"M6_SUCCESSOR_BATCH", "M7_SUCCESSOR_BATCH", "M8_2_SUCCESSOR_PILOT"},
            "M7": {"M7_SUCCESSOR_BATCH"},
            "M8_2": {"M8_2_SUCCESSOR_PILOT"},
        }[str(request["target_milestone"])]
        actual = {item.get("kind") for item in evidence if isinstance(item, Mapping)}
        if actual != expected:
            issues.append(RevisionIssue("SUCCESSOR_SCHEMA", "/successor_evidence", "Successor evidence kinds do not exactly cover the target rebuild boundary."))
    return tuple(issues)


def _manifest(
    *,
    run: Mapping[str, Any],
    request: Mapping[str, Any],
    terminal_state: str,
    created_at: str,
    successor_evidence: list[Mapping[str, Any]] | None = None,
    unresolved_issue: str | None = None,
) -> JsonObject:
    status = "RESOLVED" if terminal_state == "READY_FOR_FRESH_M9" else "ESCALATED"
    disposition: JsonObject = {
        "request_id": request["request_id"],
        "request_sha256": sha256_json(request),
        "status": status,
    }
    if successor_evidence is not None:
        disposition["successor_evidence"] = [
            {
                "kind": item["kind"],
                "path": item.get("batch_manifest_path", item.get("exercise_set_path")),
                "sha256": item.get("batch_manifest_sha256", item.get("exercise_set_sha256")),
            }
            for item in successor_evidence
        ]
    if unresolved_issue is not None:
        disposition["unresolved_issues"] = [unresolved_issue]
    value: JsonObject = {
        "schema_version": "1.0",
        "record_type": "m10_revision_manifest",
        "manifest_id": "PENDING",
        "terminal_state": terminal_state,
        "finding_batch": {"path": "finding-batch.json", "sha256": run["finding_batch_sha256"]},
        "revision_requests": [
            {
                "request_id": request["request_id"],
                "path": f"requests/{str(request['request_id']).split('_', 1)[1][:16]}.json",
                "sha256": sha256_json(request),
            }
        ],
        "dispositions": [disposition],
        "created_at": created_at,
        "fresh_m9_required": True,
        "content_lifecycle_status": "UNREVIEWED",
        "development_approved": False,
        "provider_authenticated": False,
        "limitations": [
            "M10 validates supplied evidence only and does not generate content or run M9.",
            "Successor content remains UNREVIEWED and requires a fresh independent M9 pass.",
        ],
    }
    value["manifest_id"] = identity("m10manifest", value, "manifest_id")
    validate_instance(value, "m10-revision-manifest")
    return value


def execute_supplied_successor(
    *,
    finding_batch: Mapping[str, Any],
    request: Mapping[str, Any],
    prompt: str,
    successor: Mapping[str, Any] | None,
    capture_facts: Mapping[str, Any] | None,
    output_directory: Path,
    maximum_attempts: int,
    policy_version: str,
    created_at: str,
    reviewed_at: str,
    repository_root: Path | None = None,
) -> JsonObject:
    """Publish one immutable supplied-successor run or no-capture failure.

    Invalid supplied facts and invalid successors raise before filesystem
    publication.  An intentionally unconfigured capture (``capture_facts`` is
    ``None``) instead publishes a truthful terminal operational failure.
    """
    _validate_authority(finding_batch, request)
    if not isinstance(prompt, str) or not prompt:
        raise ValueError("M10 execution prompt must be non-empty")
    run = build_governance_run(
        finding_batch=finding_batch,
        request=request,
        predecessor=request["predecessor"],
        maximum_attempts=maximum_attempts,
        policy_version=policy_version,
        created_at=created_at,
    )
    if capture_facts is None:
        if successor is not None:
            raise ValueError("M10 successor cannot be supplied without capture facts")
        ensure_not_after(created_at, reviewed_at, "M10 operational failure must follow governance creation")
        failure = build_operational_failure(
            run=run,
            stage="CAPTURE_INTEGRITY",
            error_code="CAPTURE_NOT_CONFIGURED",
            message="No factual successor capture was configured; no generation was attempted.",
            failed_at=reviewed_at,
        )
        manifest = _manifest(
            run=run,
            request=request,
            terminal_state="OPERATIONAL_FAILURE",
            created_at=reviewed_at,
            unresolved_issue="No factual successor capture was configured.",
        )
        published = publish_governance_run(
            output_directory,
            run=run,
            attempts=(),
            captures=(),
            receipts=(),
            rejections=(),
            operational_failures=(failure,),
            terminal_manifest=manifest,
            payloads={},
            request=None,
            repository_root=repository_root,
        )
        return {"output": str(published), **verify_governance_run(published)}
    if not isinstance(successor, Mapping):
        raise ValueError("M10 supplied successor must be an object")
    _validate_capture_facts(capture_facts, prompt=prompt, response=successor)
    ensure_not_after(created_at, capture_facts["captured_at"], "M10 governance run must precede its capture")
    ensure_not_after(capture_facts["captured_at"], reviewed_at, "M10 capture must precede static review")
    evidence_root = (repository_root or Path.cwd()).resolve(strict=True)

    def validate_successor(
        frozen_request: Mapping[str, Any], supplied_successor: Mapping[str, Any]
    ) -> tuple[RevisionIssue, ...]:
        return _successor_schema_issues(frozen_request, supplied_successor) + verify_successor_evidence(
            request=frozen_request,
            successor=supplied_successor,
            repository_root=evidence_root,
        )

    adapter = StaticTargetAdapter(
        str(request["target_milestone"]),
        lambda _request, response: response,
        validate_successor,
    )
    orchestrator = RevisionOrchestrator(
        backend=SuppliedCaptureBackend(successor, capture_facts),
        adapter=adapter,
        closure_issues=required_closure_issues,
    )
    attempt, receipts, rejection = orchestrator.attempt(
        run=run,
        request=request,
        attempt_number=1,
        prompt=prompt,
        parameters=capture_facts["parameters"],
        seed=capture_facts.get("seed"),
        parent_rejection=None,
        created_at=str(capture_facts["captured_at"]),
        reviewed_at=reviewed_at,
    )
    if rejection is not None or any(receipt["outcome"] != "PASS" for receipt in receipts):
        messages = [issue["message"] for receipt in receipts for issue in receipt["issues"]]
        raise ValueError("M10 supplied successor failed validation: " + "; ".join(messages))
    evidence = successor["successor_evidence"]
    manifest = _manifest(
        run=run,
        request=request,
        terminal_state="READY_FOR_FRESH_M9",
        created_at=reviewed_at,
        successor_evidence=evidence,
    )
    captured = build_capture_from_attempt(run=run, attempt=attempt, prompt=prompt, response=successor, facts=capture_facts)
    payloads = {
        attempt["attempt_id"]: {
            "prompt": prompt,
            "raw_response": dict(successor),
            "artifact": successor["artifact"],
            "audit": successor["audit"],
            "closure": successor["closure"],
        }
    }
    published = publish_governance_run(
        output_directory,
        run=run,
        attempts=(attempt,),
        captures=(captured,),
        receipts=receipts,
        rejections=(),
        terminal_manifest=manifest,
        payloads=payloads,
        request=request,
        repository_root=evidence_root,
    )
    return {"output": str(published), **verify_governance_run(published, repository_root=evidence_root)}


def build_capture_from_attempt(
    *,
    run: Mapping[str, Any],
    attempt: Mapping[str, Any],
    prompt: str,
    response: Mapping[str, Any],
    facts: Mapping[str, Any],
) -> JsonObject:
    """Reconstruct the capture created by the orchestrator and verify its binding."""
    from .governance import build_capture

    capture = build_capture(
        run=run,
        attempt_number=int(attempt["attempt_number"]),
        prompt=prompt,
        raw_response=response,
        capture=facts,
        captured_at=str(facts["captured_at"]),
    )
    if attempt.get("capture") != {"id": capture["capture_id"], "sha256": sha256_json(capture)}:
        raise ValueError("M10 orchestrator capture reconstruction drift")
    return capture
