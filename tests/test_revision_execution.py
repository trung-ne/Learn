from __future__ import annotations

import copy
import json
from pathlib import Path

import pytest

from english_master.lesson_generation.canonical import identity, sha256_json, sha256_text
from english_master.revision_cycle.__main__ import main
from english_master.revision_cycle.execution import execute_supplied_successor
from english_master.revision_cycle.run_storage import verify_governance_run

ROOT = Path(__file__).resolve().parents[1]
NOW = "2026-09-10T10:00:00Z"
LATER = "2026-09-10T10:01:00Z"


def _authority() -> tuple[dict[str, object], dict[str, object]]:
    batch: dict[str, object] = {
        "schema_version": "1.0",
        "record_type": "m10_finding_batch",
        "batch_id": "PENDING",
        "source_milestone": "M9",
        "evidence_purpose": "M10_REVISION_INPUT",
        "promotion_status": "NON_PROMOTABLE",
        "selection_id": "m9select_" + "1" * 64,
        "selection_sha256": "2" * 64,
        "machine_reports": [{"path": "machine/report.json", "sha256": "3" * 64}],
        "review_inputs": [{"path": "inputs/input.json", "sha256": "4" * 64}],
        "inventory": [
            {"path": "selection.json", "sha256": "2" * 64},
            {"path": "machine/report.json", "sha256": "3" * 64},
            {"path": "inputs/input.json", "sha256": "4" * 64},
        ],
        "imported_at": NOW,
        "content_lifecycle_status": "UNREVIEWED",
        "provider_authenticated": False,
    }
    batch["batch_id"] = identity("m10findings", batch, "batch_id")
    input_id = "m10input_" + "5" * 64
    closure = [
        {
            "target_milestone": "M7",
            "artifact_kind": "EXERCISE_SET",
            "scope": "SUBJECT_LESSON",
            "lesson_id": "A1-U01-L01",
        }
    ]
    request: dict[str, object] = {
        "schema_version": "1.0",
        "record_type": "m10_revision_request",
        "request_id": "PENDING",
        "source_milestone": "M9",
        "target_milestone": "M7",
        "revision_number": 2,
        "subject_id": "m9sub_" + "6" * 64,
        "content_type": "EXERCISE_SET",
        "lesson_id": "A1-U01-L01",
        "predecessor": {
            "artifact_path": "old.json",
            "artifact_sha256": "7" * 64,
            "audit_path": "old-audit.json",
            "audit_sha256": "8" * 64,
        },
        "source_inputs": [
            {"input_id": input_id, "input_sha256": "9" * 64, "review_role": "LINGUISTIC_AI_REVIEWER"}
        ],
        "findings": [
            {
                "source_input_id": input_id,
                "source_input_sha256": "9" * 64,
                "review_role": "LINGUISTIC_AI_REVIEWER",
                "finding_index": 0,
                "finding": {"severity": "MAJOR", "category": "ANSWER", "description": "Repair answer."},
            }
        ],
        "repair_constraints": [
            {"source_input_id": input_id, "finding_index": 0, "requirement": "Repair answer.", "scope_boundary": "Only this set."}
        ],
        "acceptance_checks": [{"check_code": "ANSWER", "requirement": "Answer passes."}],
        "rebuild_closure": closure,
        "planning_only": True,
        "successor_created": False,
        "lifecycle_transition_authorized": False,
        "approval_claim_authorized": False,
        "content_lifecycle_status": "UNREVIEWED",
        "development_approved": False,
    }
    request["request_id"] = identity("m10request", request, "request_id")
    return batch, request


def _successor(request: dict[str, object]) -> dict[str, object]:
    exercise_path = "curriculum/exercises/development-20260911-m10-r2/A1-U01-L01/exercise-set.json"
    audit_path = "curriculum/exercises/development-20260911-m10-r2/A1-U01-L01/audit.json"
    artifact = json.loads((ROOT / exercise_path).read_text(encoding="utf-8"))
    audit = json.loads((ROOT / audit_path).read_text(encoding="utf-8"))
    return {
        "artifact": artifact,
        "audit": audit,
        "closure": request["rebuild_closure"],
        "successor_evidence": [
            {
                "kind": "M7_SUCCESSOR_BATCH",
                "exercise_set_path": exercise_path,
                "exercise_set_sha256": sha256_json(artifact),
                "audit_path": audit_path,
                "audit_sha256": sha256_json(audit),
            }
        ],
    }


def _capture(prompt: str, successor: dict[str, object]) -> dict[str, object]:
    return {
        "capture_mode": "SESSION_CAPTURED",
        "provider": "UNKNOWN",
        "model": "UNKNOWN",
        "execution_id": "external-session-123",
        "parameters": {},
        "seed": None,
        "provider_authenticated": False,
        "prompt_sha256": sha256_text(prompt),
        "raw_response_sha256": sha256_json(successor),
        "captured_at": NOW,
    }


def test_executes_only_supplied_factual_successor_and_publishes_closed_run(tmp_path: Path) -> None:
    batch, request = _authority()
    prompt = "Repair only the frozen request scope."
    successor = _successor(request)
    result = execute_supplied_successor(
        finding_batch=batch,
        request=request,
        prompt=prompt,
        successor=successor,
        capture_facts=_capture(prompt, successor),
        output_directory=tmp_path / "run",
        maximum_attempts=1,
        policy_version="phase-2-v1",
        created_at=NOW,
        reviewed_at=LATER,
        repository_root=ROOT,
    )
    assert result["terminal_manifest"]["terminal_state"] == "READY_FOR_FRESH_M9"
    assert result["attempt_count"] == 1
    assert result["capture_count"] == 1
    assert result["receipt_count"] == 6
    assert verify_governance_run(tmp_path / "run", repository_root=ROOT)["terminal_manifest"]["development_approved"] is False
    closure_path = next((tmp_path / "run" / "payloads").glob("*/closure.json"))
    closure_path.write_text("[]", encoding="utf-8")
    with pytest.raises(ValueError, match="captured raw response"):
        verify_governance_run(tmp_path / "run", repository_root=ROOT)


@pytest.mark.parametrize("mutation", ["hash", "test", "closure"])
def test_invalid_supplied_facts_or_closure_publish_nothing(tmp_path: Path, mutation: str) -> None:
    batch, request = _authority()
    prompt = "Repair only the frozen request scope."
    successor = _successor(request)
    capture = _capture(prompt, successor)
    if mutation == "hash":
        capture["raw_response_sha256"] = "f" * 64
    elif mutation == "test":
        capture["capture_mode"] = "TEST_ONLY"
    else:
        successor["closure"] = []
        capture["raw_response_sha256"] = sha256_json(successor)
    destination = tmp_path / "must-not-exist"
    with pytest.raises(ValueError):
        execute_supplied_successor(
            finding_batch=batch,
            request=request,
            prompt=prompt,
            successor=successor,
            capture_facts=capture,
            output_directory=destination,
            maximum_attempts=1,
            policy_version="phase-2-v1",
            created_at=NOW,
            reviewed_at=LATER,
            repository_root=ROOT,
        )
    assert not destination.exists()


def test_evidence_path_escape_or_hash_drift_publish_nothing(tmp_path: Path) -> None:
    batch, request = _authority()
    prompt = "Repair only the frozen request scope."
    successor = _successor(request)
    for path, digest in (("../outside.json", None), (None, "0" * 64)):
        candidate = copy.deepcopy(successor)
        if path is not None:
            candidate["successor_evidence"][0]["exercise_set_path"] = path
        if digest is not None:
            candidate["successor_evidence"][0]["audit_sha256"] = digest
        with pytest.raises(ValueError, match="successor evidence"):
            execute_supplied_successor(
                finding_batch=batch,
                request=request,
                prompt=prompt,
                successor=candidate,
                capture_facts=_capture(prompt, candidate),
                output_directory=tmp_path / f"invalid-{path is not None}",
                maximum_attempts=1,
                policy_version="phase-2-v1",
                created_at=NOW,
                reviewed_at=LATER,
                repository_root=ROOT,
            )
    assert not any(tmp_path.iterdir())



def test_m8_successor_requires_a_dereferenced_full_pilot(tmp_path: Path) -> None:
    batch, request = _authority()
    request = copy.deepcopy(request)
    request.update({
        "target_milestone": "M8_2",
        "content_type": "AI_PRACTICE_PROMPT",
        "lesson_id": "B1-U05-L02",
        "modality": "SPEAKING",
        "rebuild_closure": [{"target_milestone": "M8_2", "artifact_kind": "AI_PRACTICE_PILOT", "scope": "FULL_CLOSED_PILOT"}],
        "acceptance_checks": [{"check_code": "M8_2_FULL_PILOT_REBUILT", "requirement": "Full pilot passes."}],
    })
    request["request_id"] = "PENDING"
    request["request_id"] = identity("m10request", request, "request_id")
    pilot = "curriculum/ai-practice/pilot-batches/20260911-v14-m10"
    artifact_path = f"{pilot}/prompts/b1-u05-l02--speaking.json"
    audit_path = f"{pilot}/audits/b1-u05-l02--speaking.json"
    manifest_path = f"{pilot}/batch-manifest.json"
    artifact = json.loads((ROOT / artifact_path).read_text(encoding="utf-8"))
    audit = json.loads((ROOT / audit_path).read_text(encoding="utf-8"))
    manifest = json.loads((ROOT / manifest_path).read_text(encoding="utf-8"))
    successor = {
        "artifact": artifact,
        "audit": audit,
        "closure": request["rebuild_closure"],
        "pilot_artifact_count": 40,
        "successor_evidence": [{
            "kind": "M8_2_SUCCESSOR_PILOT",
            "pilot_directory": pilot,
            "batch_manifest_path": manifest_path,
            "batch_manifest_sha256": sha256_json(manifest),
            "artifact_path": artifact_path,
            "artifact_sha256": sha256_json(artifact),
            "audit_path": audit_path,
            "audit_sha256": sha256_json(audit),
        }],
    }
    result = execute_supplied_successor(
        finding_batch=batch,
        request=request,
        prompt="Repair the frozen speaking protocol.",
        successor=successor,
        capture_facts=_capture("Repair the frozen speaking protocol.", successor),
        output_directory=tmp_path / "m8-run",
        maximum_attempts=1,
        policy_version="phase-2-v1",
        created_at=NOW,
        reviewed_at=LATER,
        repository_root=ROOT,
    )
    assert result["terminal_manifest"]["terminal_state"] == "READY_FOR_FRESH_M9"

    batch, request = _authority()
    result = execute_supplied_successor(
        finding_batch=batch,
        request=request,
        prompt="Frozen prompt; not executed.",
        successor=None,
        capture_facts=None,
        output_directory=tmp_path / "failure",
        maximum_attempts=1,
        policy_version="phase-2-v1",
        created_at=NOW,
        reviewed_at=LATER,
        repository_root=ROOT,
    )
    assert result["terminal_manifest"]["terminal_state"] == "OPERATIONAL_FAILURE"
    assert result["attempt_count"] == 0
    assert result["operational_failure_count"] == 1


def test_execute_successor_cli_dispatches_without_loading_m9_authority(tmp_path: Path) -> None:
    batch, request = _authority()
    prompt = "Frozen prompt; no configured capture."
    batch_path = tmp_path / "batch.json"
    request_path = tmp_path / "request.json"
    prompt_path = tmp_path / "prompt.txt"
    batch_path.write_text(json.dumps(batch), encoding="utf-8")
    request_path.write_text(json.dumps(request), encoding="utf-8")
    prompt_path.write_text(prompt, encoding="utf-8")
    destination = tmp_path / "cli-run"
    assert main(
        [
            "execute-successor",
            "--finding-batch",
            str(batch_path),
            "--revision-request",
            str(request_path),
            "--prompt",
            str(prompt_path),
            "--output-dir",
            str(destination),
            "--created-at",
            NOW,
            "--reviewed-at",
            LATER,
        ]
    ) == 0
    assert verify_governance_run(destination)["terminal_manifest"]["terminal_state"] == "OPERATIONAL_FAILURE"
