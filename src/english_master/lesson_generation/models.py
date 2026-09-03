"""Typed public models for constrained M6 lesson generation."""

from __future__ import annotations

import copy
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping, Protocol

JsonObject = dict[str, Any]


@dataclass(frozen=True)
class LessonGenerationRequest:
    """A validated-at-boundary, snapshot-derived generation request."""

    data: Mapping[str, Any]

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "LessonGenerationRequest":
        return cls(data=copy.deepcopy(dict(value)))

    def as_dict(self) -> JsonObject:
        return copy.deepcopy(dict(self.data))


@dataclass(frozen=True)
class CapturedLessonResponse:
    """A response whose provider execution facts are bound to its exact prompt."""

    content: JsonObject
    prompt_sha256: str
    response_sha256: str
    provider: str | None
    model: str | None
    parameters: Mapping[str, Any]
    seed: int | None
    observed_at: str
    deterministic: bool
    replayable_from_capture: bool

    def provenance(self) -> JsonObject:
        return {
            "prompt_sha256": self.prompt_sha256,
            "response_sha256": self.response_sha256,
            "provider": self.provider,
            "model": self.model,
            "parameters": copy.deepcopy(dict(self.parameters)),
            "seed": self.seed,
            "observed_at": self.observed_at,
            "deterministic": self.deterministic,
            "replayable_from_capture": self.replayable_from_capture,
        }


@dataclass(frozen=True, order=True)
class GenerationIssue:
    """A stable rejection issue sorted by code, path, then message."""

    code: str
    path: str
    message: str

    def as_dict(self) -> JsonObject:
        return {"code": self.code, "path": self.path, "message": self.message}


@dataclass(frozen=True)
class LessonGenerationResult:
    """Accepted lesson and audit, or a fail-closed rejection."""

    accepted: bool
    lesson: JsonObject | None
    audit: JsonObject
    rejection: JsonObject | None
    published_paths: tuple[Path, ...] = ()


class LessonBackend(Protocol):
    """Provider-neutral boundary returning a prompt-bound captured response."""

    byte_identical_output: bool

    def generate(
        self,
        prompt: str,
        *,
        parameters: Mapping[str, Any],
        seed: int | None,
    ) -> CapturedLessonResponse:
        ...
