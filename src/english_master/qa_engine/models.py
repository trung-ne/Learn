"""Typed boundaries and fixed stage contract for the M8 QA Engine."""
from __future__ import annotations

import copy
from dataclasses import dataclass
from typing import Any, Mapping, Protocol

JsonObject = dict[str, Any]
STAGE_CONTRACT = (
    ("SCHEMA", 1, "MACHINE"),
    ("ANSWER", 2, "MACHINE"),
    ("CEFR", 3, "MACHINE"),
    ("PREREQUISITE", 4, "MACHINE"),
    ("DUPLICATE", 5, "MACHINE"),
    ("LANGUAGE", 6, "AI"),
)
STAGES = tuple(item[0] for item in STAGE_CONTRACT)
REVIEW_CRITERIA = (
    "ANSWER_ACCURACY_AND_AMBIGUITY",
    "CEFR_SEMANTIC_ALIGNMENT",
    "PREREQUISITE_OBJECTIVE_ALIGNMENT",
    "LANGUAGE_QUALITY",
)


@dataclass(frozen=True, order=True)
class QaIssue:
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
class ModelCapture:
    """Narrow raw response plus observed runtime facts.

    The host, not the backend, supplies the observation timestamp and computes all
    hashes. Provider and model may truthfully be UNKNOWN. `provider_authenticated`
    is false until a separately verifiable provider receipt exists.
    """

    content: Mapping[str, Any]
    capture_mode: str
    provider: str
    model: str
    provider_run_id: str
    parameters: Mapping[str, Any] | None
    seed: int | None = None
    seed_observed: bool = False
    provider_authenticated: bool = False


class ModelBackend(Protocol):
    def generate(
        self,
        prompt: str,
        *,
        parameters: Mapping[str, Any],
        seed: int | None,
    ) -> ModelCapture: ...


@dataclass(frozen=True)
class ReviewEvidence:
    passed: bool
    issues: tuple[QaIssue, ...]
    evidence_kind: str
    review_id: str
    review_sha256: str
    review: Mapping[str, Any] | None = None
    invocation: Mapping[str, Any] | None = None

    def reference(self) -> JsonObject:
        return {
            "evidence_kind": self.evidence_kind,
            "review_id": self.review_id,
            "review_sha256": self.review_sha256,
        }


@dataclass(frozen=True)
class QaEngineResult:
    approved: bool
    decision: JsonObject | None
    rejections: tuple[JsonObject, ...]
    attempts: tuple[JsonObject, ...]
    receipts: tuple[tuple[JsonObject, ...], ...]
    invocations: tuple[JsonObject, ...] = ()
    ai_reviews: tuple[JsonObject, ...] = ()
    operational_failures: tuple[JsonObject, ...] = ()
    paths: tuple[Any, ...] = ()

    def copy(self) -> "QaEngineResult":
        return QaEngineResult(
            self.approved,
            copy.deepcopy(self.decision),
            tuple(copy.deepcopy(value) for value in self.rejections),
            tuple(copy.deepcopy(value) for value in self.attempts),
            tuple(
                tuple(copy.deepcopy(item) for item in values)
                for values in self.receipts
            ),
            tuple(copy.deepcopy(value) for value in self.invocations),
            tuple(copy.deepcopy(value) for value in self.ai_reviews),
            tuple(copy.deepcopy(value) for value in self.operational_failures),
            self.paths,
        )
