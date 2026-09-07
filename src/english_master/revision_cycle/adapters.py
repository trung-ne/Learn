"""Strict M10 target-adapter boundaries and downstream rebuild closure checks."""
from __future__ import annotations

from collections.abc import Callable, Mapping
from typing import Any

from .models import RevisionIssue

JsonObject = dict[str, Any]
Assembler = Callable[[Mapping[str, Any], Mapping[str, Any]], Mapping[str, Any]]
Validator = Callable[[Mapping[str, Any], Mapping[str, Any]], tuple[RevisionIssue, ...]]


class StaticTargetAdapter:
    """Host-owned adapter that allows target builders but never trusts a backend."""

    def __init__(self, target_milestone: str, assembler: Assembler, validator: Validator) -> None:
        if target_milestone not in {"M6", "M7", "M8_2"}:
            raise ValueError(f"unsupported M10 target: {target_milestone}")
        self.target_milestone = target_milestone
        self._assembler = assembler
        self._validator = validator

    def assemble_successor(self, request: Mapping[str, Any], response: Mapping[str, Any]) -> Mapping[str, Any]:
        return self._assembler(request, response)

    def validate_successor(self, request: Mapping[str, Any], successor: Mapping[str, Any]) -> tuple[RevisionIssue, ...]:
        return self._validator(request, successor)


def required_closure_issues(request: Mapping[str, Any], successor: Mapping[str, Any]) -> tuple[RevisionIssue, ...]:
    """Require exact M10 closure evidence; stale partial rebuilds fail closed."""
    closure = successor.get("closure")
    if not isinstance(closure, list):
        return (RevisionIssue("DEPENDENCY_REBUILD", "/closure", "Missing successor closure evidence."),)
    actual = {(item.get("target_milestone"), item.get("artifact_kind"), item.get("scope"), item.get("lesson_id")) for item in closure if isinstance(item, Mapping)}
    expected = {(item.get("target_milestone"), item.get("artifact_kind"), item.get("scope"), item.get("lesson_id")) for item in request.get("rebuild_closure", []) if isinstance(item, Mapping)}
    if actual != expected:
        return (RevisionIssue("DEPENDENCY_REBUILD", "/closure", "Successor closure differs from the immutable revision request."),)
    if request.get("target_milestone") == "M8_2":
        pilot_count = successor.get("pilot_artifact_count")
        if pilot_count != 40:
            return (RevisionIssue("CLOSED_INVENTORY", "/pilot_artifact_count", "M8.2 successors require a complete 40-artifact pilot."),)
    return ()
