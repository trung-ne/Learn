from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping

from english_master.lesson_generation.canonical import sha256_json
from english_master.revision_cycle.models import RegenerationCapture
from english_master.revision_cycle.orchestrator import RevisionOrchestrator


@dataclass
class Backend:
    def regenerate(self, prompt: str, *, parameters: Mapping[str, Any], seed: int | None) -> RegenerationCapture:
        return RegenerationCapture(content={"body": "replacement"}, capture_mode="TEST_ONLY", provider="TEST", model="TEST", execution_id="test", parameters=parameters, seed=seed)


class Adapter:
    target_milestone = "M7"

    def assemble_successor(self, request: Mapping[str, Any], response: Mapping[str, Any]) -> Mapping[str, Any]:
        return {"artifact": dict(response), "audit": {"static": True}, "closure": []}

    def validate_successor(self, request: Mapping[str, Any], successor: Mapping[str, Any]) -> tuple[object, ...]:
        return ()


def test_orchestrator_short_circuits_after_capture_failure() -> None:
    request = {"request_id": "m10request_" + "1" * 64, "target_milestone": "M7", "predecessor": {"artifact_path": "old.json", "artifact_sha256": "a" * 64, "audit_path": "old-audit.json", "audit_sha256": "b" * 64}, "rebuild_closure": []}
    run = {"run_id": "m10run_" + "0" * 64, "maximum_attempts": 3, "revision_request_id": request["request_id"], "revision_request_sha256": sha256_json(request)}
    result = RevisionOrchestrator(backend=Backend(), adapter=Adapter(), closure_issues=lambda request, successor: ())
    _, receipts, rejection = result.attempt(run=run, request=request, attempt_number=1, prompt="repair", parameters={}, seed=None, parent_rejection=None, created_at="2026-09-05T10:00:00Z", reviewed_at="2026-09-05T10:01:00Z")
    assert [receipt["outcome"] for receipt in receipts] == ["FAIL", "NOT_RUN", "NOT_RUN", "NOT_RUN", "NOT_RUN", "NOT_RUN"]
    assert rejection is not None
    assert rejection["retryable"] is False
