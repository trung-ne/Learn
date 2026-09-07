"""Typed boundaries and fixed state contract for M10 regeneration governance."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping, Protocol

JsonObject = dict[str, Any]

STAGE_CONTRACT = (
    ("CAPTURE_INTEGRITY", 1),
    ("SUCCESSOR_SCHEMA", 2),
    ("AUTHORITY_BINDING", 3),
    ("REPAIR_SCOPE", 4),
    ("DEPENDENCY_REBUILD", 5),
    ("CLOSED_INVENTORY", 6),
)
STAGES = tuple(stage for stage, _ in STAGE_CONTRACT)
TERMINAL_STATES = (
    "READY_FOR_FRESH_M9",
    "RETRY_EXHAUSTED",
    "ESCALATED",
    "OPERATIONAL_FAILURE",
)
NON_RETRYABLE_CODES = frozenset(
    {
        "AUTHORITY_CONFLICT",
        "AUTHORITY_DRIFT",
        "CAPTURE_INTEGRITY",
        "IDENTITY_DRIFT",
        "PATH_SAFETY",
        "PROVENANCE_POLICY",
        "REQUEST_BINDING",
    }
)


@dataclass(frozen=True, order=True)
class RevisionIssue:
    """A deterministic M10 governance issue, never an approval decision."""

    code: str
    path: str
    message: str
    severity: str = "MAJOR"

    def as_dict(self) -> JsonObject:
        return {
            "code": self.code,
            "path": self.path,
            "message": self.message,
            "severity": self.severity,
        }


@dataclass(frozen=True)
class RegenerationCapture:
    """Untrusted narrow authored response and observed runtime facts."""

    content: Mapping[str, Any]
    capture_mode: str
    provider: str
    model: str
    execution_id: str
    parameters: Mapping[str, Any] | None = None
    seed: int | None = None
    provider_authenticated: bool = False


class RevisionBackend(Protocol):
    """Backend may author payload only; host constructs governance evidence."""

    def regenerate(
        self,
        prompt: str,
        *,
        parameters: Mapping[str, Any],
        seed: int | None,
    ) -> RegenerationCapture: ...


class RevisionTargetAdapter(Protocol):
    """Target-specific successor construction and static validation boundary."""

    target_milestone: str

    def assemble_successor(
        self,
        request: Mapping[str, Any],
        response: Mapping[str, Any],
    ) -> Mapping[str, Any]: ...

    def validate_successor(
        self,
        request: Mapping[str, Any],
        successor: Mapping[str, Any],
    ) -> tuple[RevisionIssue, ...]: ...
