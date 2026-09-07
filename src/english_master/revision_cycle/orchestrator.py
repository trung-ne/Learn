"""Bounded M10 successor orchestration; it never performs M9 or approval."""
from __future__ import annotations

from collections.abc import Callable, Mapping
from typing import Any

from .governance import build_attempt, build_capture, build_receipts, build_rejection
from .models import RegenerationCapture, RevisionBackend, RevisionIssue, RevisionTargetAdapter

JsonObject = dict[str, Any]


class RevisionOrchestrator:
    """Run one static successor attempt against immutable M10 authority."""

    def __init__(self, *, backend: RevisionBackend, adapter: RevisionTargetAdapter, closure_issues: Callable[[Mapping[str, Any], Mapping[str, Any]], tuple[RevisionIssue, ...]]) -> None:
        self._backend = backend
        self._adapter = adapter
        self._closure_issues = closure_issues

    def attempt(
        self, *, run: Mapping[str, Any], request: Mapping[str, Any], attempt_number: int,
        prompt: str, parameters: Mapping[str, Any], seed: int | None, parent_rejection: Mapping[str, Any] | None,
        created_at: str, reviewed_at: str,
    ) -> tuple[JsonObject, tuple[JsonObject, ...], JsonObject | None]:
        """Create a successor attempt, full receipts, and rejection when static QA fails."""
        if attempt_number > int(run["maximum_attempts"]):
            raise ValueError("M10 retry budget is exhausted")
        if self._adapter.target_milestone != request["target_milestone"]:
            raise ValueError("M10 target adapter does not match revision request")
        captured: RegenerationCapture = self._backend.regenerate(prompt, parameters=parameters, seed=seed)
        capture = build_capture(
            run=run, attempt_number=attempt_number, prompt=prompt, raw_response=captured.content,
            capture={"capture_mode": captured.capture_mode, "provider": captured.provider, "model": captured.model,
                     "execution_id": captured.execution_id, "parameters": captured.parameters or parameters, "seed": captured.seed},
            captured_at=created_at,
        )
        successor = self._adapter.assemble_successor(request, captured.content)
        artifact = successor.get("artifact")
        audit = successor.get("audit")
        if not isinstance(artifact, Mapping) or not isinstance(audit, Mapping):
            raise ValueError("M10 target adapter must return artifact and audit mappings")
        attempt = build_attempt(run=run, request=request, attempt_number=attempt_number, predecessor=request["predecessor"], artifact=artifact, audit=audit, capture=capture, parent_rejection=parent_rejection, created_at=created_at)
        capture_issues: tuple[RevisionIssue, ...] = ()
        is_test_labelled = any(str(capture[key]).upper().startswith("TEST") for key in ("provider", "model", "execution_id"))
        if capture["capture_mode"] in {"TEST_ONLY", "REPLAY_ONLY"} or is_test_labelled:
            capture_issues = (RevisionIssue("CAPTURE_INTEGRITY", "/capture", "Test, replay-only, or test-labelled capture cannot establish M10 readiness."),)
        stage_issues = {
            "CAPTURE_INTEGRITY": capture_issues,
            "SUCCESSOR_SCHEMA": self._adapter.validate_successor(request, successor),
            "AUTHORITY_BINDING": tuple(successor.get("authority_issues", ())),
            "REPAIR_SCOPE": tuple(successor.get("repair_scope_issues", ())),
            "DEPENDENCY_REBUILD": self._closure_issues(request, successor),
            "CLOSED_INVENTORY": tuple(successor.get("inventory_issues", ())),
        }
        receipts = build_receipts(run=run, attempt=attempt, stage_issues=stage_issues, reviewed_at=reviewed_at)
        rejection = build_rejection(run=run, attempt=attempt, receipts=receipts, rejected_at=reviewed_at) if any(item["outcome"] in {"FAIL", "ERROR"} for item in receipts) else None
        return attempt, receipts, rejection
