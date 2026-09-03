"""Prompt-bound captured-response M6 backends for tests and replay."""

from __future__ import annotations

import copy
import json
from pathlib import Path
from typing import Any, Mapping

from .canonical import sha256_json, sha256_text
from .models import CapturedLessonResponse, JsonObject


class MockLessonBackend:
    """Test-only backend that records a deterministic local response."""

    byte_identical_output = True

    def __init__(
        self,
        response: Mapping[str, Any],
        *,
        observed_at: str = "2026-09-03T00:00:00Z",
    ) -> None:
        self._response = copy.deepcopy(dict(response))
        self._observed_at = observed_at
        self.calls = 0
        self.last_prompt: str | None = None

    def generate(
        self,
        prompt: str,
        *,
        parameters: Mapping[str, Any],
        seed: int | None,
    ) -> CapturedLessonResponse:
        self.calls += 1
        self.last_prompt = prompt
        content = copy.deepcopy(self._response)
        return CapturedLessonResponse(
            content=content,
            prompt_sha256=sha256_text(prompt),
            response_sha256=sha256_json(content),
            provider="TEST_ONLY_MOCK",
            model=None,
            parameters=copy.deepcopy(dict(parameters)),
            seed=seed,
            observed_at=self._observed_at,
            deterministic=True,
            replayable_from_capture=True,
        )


class CapturedResponseLessonBackend:
    """Replay a response capture only when its exact prompt and facts match."""

    byte_identical_output = True

    def __init__(self, capture: Mapping[str, Any]) -> None:
        self._capture = copy.deepcopy(dict(capture))
        self.calls = 0
        self.last_prompt: str | None = None

    @classmethod
    def from_file(cls, path: Path) -> "CapturedResponseLessonBackend":
        with path.open("r", encoding="utf-8") as handle:
            value = json.load(handle)
        if not isinstance(value, dict):
            raise ValueError(f"Captured response must be a JSON object: {path}")
        return cls(value)

    def generate(
        self,
        prompt: str,
        *,
        parameters: Mapping[str, Any],
        seed: int | None,
    ) -> CapturedLessonResponse:
        self.calls += 1
        self.last_prompt = prompt
        capture = self._capture
        content = capture.get("content")
        if not isinstance(content, dict):
            raise ValueError("capture.content must be a JSON object")
        prompt_sha256 = capture.get("prompt_sha256")
        if prompt_sha256 != sha256_text(prompt):
            raise ValueError("captured response does not bind the generated prompt")
        if capture.get("response_sha256") != sha256_json(content):
            raise ValueError("captured response hash does not match its content")
        if capture.get("parameters") != dict(parameters) or capture.get("seed") != seed:
            raise ValueError("captured response parameters or seed do not match the request")
        provider = capture.get("provider")
        model = capture.get("model")
        observed_at = capture.get("observed_at")
        deterministic = capture.get("deterministic")
        replayable = capture.get("replayable_from_capture")
        if not isinstance(provider, (str, type(None))) or not isinstance(model, (str, type(None))):
            raise ValueError("capture provider and model must be strings or null")
        if not isinstance(observed_at, str) or not isinstance(deterministic, bool) or not isinstance(replayable, bool):
            raise ValueError("capture execution facts are incomplete")
        return CapturedLessonResponse(
            content=copy.deepcopy(content),
            prompt_sha256=prompt_sha256,
            response_sha256=capture["response_sha256"],
            provider=provider,
            model=model,
            parameters=copy.deepcopy(dict(parameters)),
            seed=seed,
            observed_at=observed_at,
            deterministic=deterministic,
            replayable_from_capture=replayable,
        )


class FileMockLessonBackend(MockLessonBackend):
    """Deprecated test-only JSON response loader retained for offline fixtures."""

    def __init__(self, path: Path, *, observed_at: str = "2026-09-03T00:00:00Z") -> None:
        with path.open("r", encoding="utf-8") as handle:
            value = json.load(handle)
        if not isinstance(value, dict):
            raise ValueError(f"Mock backend response must be a JSON object: {path}")
        super().__init__(value, observed_at=observed_at)
