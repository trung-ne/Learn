"""Offline deterministic M7 backend adapters."""
from __future__ import annotations

import copy
from typing import Any, Mapping

from english_master.lesson_generation.canonical import sha256_json, sha256_text

from .models import CapturedExerciseResponse, JsonObject


class MockExerciseBackend:
    byte_identical_output = True
    def __init__(self, content: Mapping[str, Any], *, observed_at: str = "2026-09-03T09:00:00Z") -> None:
        self.content = copy.deepcopy(dict(content)); self.observed_at = observed_at; self.calls = 0
    def generate(self, prompt: str, *, parameters: Mapping[str, Any], seed: int | None) -> CapturedExerciseResponse:
        self.calls += 1; value=copy.deepcopy(self.content)
        return CapturedExerciseResponse(value,sha256_text(prompt),sha256_json(value),dict(parameters),seed,self.observed_at,"TEST_ONLY_MOCK","TEST_ONLY_MOCK",None,True,True,"TEST_ONLY")


class CapturedResponseExerciseBackend:
    byte_identical_output = True
    def __init__(self, capture: Mapping[str, Any]) -> None: self.capture=copy.deepcopy(dict(capture)); self.calls=0
    def generate(self, prompt: str, *, parameters: Mapping[str, Any], seed: int | None) -> CapturedExerciseResponse:
        self.calls += 1
        value=copy.deepcopy(self.capture["content"])
        return CapturedExerciseResponse(value,sha256_text(prompt),sha256_json(value),dict(parameters),seed,str(self.capture["observed_at"]),self.capture.get("provider"),self.capture.get("model"),self.capture.get("run_id"),bool(self.capture.get("deterministic",True)),True,str(self.capture.get("provenance_mode","SESSION_CAPTURED")))
