"""Typed boundary models for M7."""
from __future__ import annotations

import copy
from dataclasses import dataclass
from typing import Any, Mapping, Protocol

from english_master.lesson_generation.canonical import sha256_json, sha256_text

JsonObject = dict[str, Any]


@dataclass(frozen=True, order=True)
class ExerciseIssue:
    code: str
    path: str
    message: str

    def as_dict(self) -> JsonObject:
        return {"code": self.code, "path": self.path, "message": self.message}


@dataclass(frozen=True)
class CapturedExerciseResponse:
    content: JsonObject
    prompt_sha256: str
    response_sha256: str
    parameters: Mapping[str, Any]
    seed: int | None
    observed_at: str
    provider: str | None = None
    model: str | None = None
    run_id: str | None = None
    deterministic: bool = False
    replayable_from_capture: bool = True
    provenance_mode: str = "SESSION_CAPTURED"

    def provenance(self) -> JsonObject:
        return {
            "capture_mode": self.provenance_mode,
            "prompt_sha256": self.prompt_sha256,
            "response_sha256": self.response_sha256,
            "parameters": copy.deepcopy(dict(self.parameters)),
            "seed": self.seed,
            "observed_at": self.observed_at,
            "provider": self.provider or "UNKNOWN",
            "model": self.model or "UNKNOWN",
            "run_id": self.run_id or "UNKNOWN",
            "deterministic": self.deterministic,
            "replayable_from_capture": self.replayable_from_capture,
        }


class ExerciseBackend(Protocol):
    byte_identical_output: bool

    def generate(self, prompt: str, *, parameters: Mapping[str, Any], seed: int | None) -> CapturedExerciseResponse: ...


@dataclass(frozen=True)
class ExerciseGenerationRequest:
    payload: Mapping[str, Any]

    def as_dict(self) -> JsonObject:
        return copy.deepcopy(dict(self.payload))


@dataclass(frozen=True)
class ExerciseGenerationResult:
    accepted: bool
    exercise_set: JsonObject | None
    audit: JsonObject
    rejection: JsonObject | None
    paths: tuple[Any, ...]


def captured_response(content: Mapping[str, Any], prompt: str, *, parameters: Mapping[str, Any], seed: int | None, observed_at: str, provider: str | None = None, model: str | None = None, run_id: str | None = None, provenance_mode: str = "SESSION_CAPTURED") -> CapturedExerciseResponse:
    value = copy.deepcopy(dict(content))
    return CapturedExerciseResponse(value, sha256_text(prompt), sha256_json(value), dict(parameters), seed, observed_at, provider, model, run_id, True, True, provenance_mode)
