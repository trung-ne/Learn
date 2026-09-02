"""Provider-neutral and deterministic offline M6 backends."""

from __future__ import annotations

import copy
import json
from pathlib import Path
from typing import Any, Mapping

from .models import JsonObject


class MockLessonBackend:
    """Return an authored response without network or provider SDK access."""

    def __init__(self, response: Mapping[str, Any]) -> None:
        self._response = dict(response)
        self.calls = 0
        self.last_prompt: str | None = None

    def generate(self, prompt: str, *, parameters: Mapping[str, Any], seed: int | None) -> JsonObject:
        self.calls += 1
        self.last_prompt = prompt
        return copy.deepcopy(self._response)


class FileMockLessonBackend(MockLessonBackend):
    """Load an authored mock response from disk for the offline CLI."""

    def __init__(self, path: Path) -> None:
        with path.open("r", encoding="utf-8") as handle:
            value = json.load(handle)
        if not isinstance(value, dict):
            raise ValueError(f"Mock backend response must be a JSON object: {path}")
        super().__init__(value)
