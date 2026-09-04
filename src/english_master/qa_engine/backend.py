"""Narrow model backends for M8 regeneration and semantic review."""
from __future__ import annotations

import copy
from collections import deque
from collections.abc import Callable
from typing import Any, Mapping

from .models import ModelCapture


class ReplayModelBackend:
    """Consumes retained raw responses and always labels them non-promotable replay."""

    def __init__(self, captures: list[Mapping[str, Any]]) -> None:
        self._captures = deque(copy.deepcopy([dict(item) for item in captures]))

    def generate(
        self,
        prompt: str,
        *,
        parameters: Mapping[str, Any],
        seed: int | None,
    ) -> ModelCapture:
        del prompt, parameters, seed
        if not self._captures:
            raise ValueError("no retained response remains for this invocation")
        value = self._captures.popleft()
        content = value.get("response", value.get("candidate"))
        if not isinstance(content, Mapping):
            raise ValueError("retained response must be a JSON object")
        provenance = value.get("generation_provenance", value.get("provenance", {}))
        if not isinstance(provenance, Mapping):
            raise ValueError("retained response provenance must be an object")
        return ModelCapture(
            copy.deepcopy(dict(content)),
            "REPLAY_CAPTURED",
            str(provenance.get("provider", "UNKNOWN")),
            str(provenance.get("model", "UNKNOWN")),
            str(provenance.get("provider_run_id", provenance.get("run_id", "UNKNOWN"))),
            None,
        )


class SessionModelBackend:
    """Invoke a supplied live-session callback and retain its raw JSON response.

    This proves only that the callback was invoked in this process and returned
    a response. It cannot establish provider-applied parameters or seed, and it
    does not authenticate a provider; callers must not claim otherwise.
    """

    def __init__(
        self,
        callback: Callable[[str, Mapping[str, Any], int | None], Mapping[str, Any]],
        *,
        provider: str = "UNKNOWN",
        model: str = "UNKNOWN",
        provider_run_id: str = "UNKNOWN",
    ) -> None:
        self._callback = callback
        self._provider = provider or "UNKNOWN"
        self._model = model or "UNKNOWN"
        self._provider_run_id = provider_run_id or "UNKNOWN"

    def generate(
        self,
        prompt: str,
        *,
        parameters: Mapping[str, Any],
        seed: int | None,
    ) -> ModelCapture:
        content = self._callback(prompt, copy.deepcopy(dict(parameters)), seed)
        if not isinstance(content, Mapping):
            raise ValueError("session backend must return a JSON object")
        return ModelCapture(
            copy.deepcopy(dict(content)),
            "SESSION_CAPTURED",
            self._provider,
            self._model,
            self._provider_run_id,
            None,
        )


# Compatibility alias for the prior CLI name. Its evidence is always replay-only.
CapturedCandidateGenerator = ReplayModelBackend
