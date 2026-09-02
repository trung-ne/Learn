"""Typed public models for constrained M6 lesson generation."""

from __future__ import annotations

import copy
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping, Protocol

JsonObject = dict[str, Any]


@dataclass(frozen=True)
class LessonGenerationRequest:
    """A validated-at-boundary generation request payload."""

    data: Mapping[str, Any]

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "LessonGenerationRequest":
        return cls(data=copy.deepcopy(dict(value)))

    def as_dict(self) -> JsonObject:
        return copy.deepcopy(dict(self.data))


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
    """Provider-neutral backend boundary. Implementations return one JSON object."""

    byte_identical_output: bool

    def generate(self, prompt: str, *, parameters: Mapping[str, Any], seed: int | None) -> JsonObject:
        ...
