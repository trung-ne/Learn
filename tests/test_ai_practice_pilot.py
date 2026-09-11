from __future__ import annotations

import copy
import json
from pathlib import Path

import pytest

from english_master.ai_practice.authority import MODALITIES, VerifiedM6PracticeAuthority
from english_master.ai_practice.cli import main as cli_main
from english_master.ai_practice.generation import _render, audit_artifact, build_pilot
from english_master.ai_practice.verification import verify_pilot
from english_master.lesson_generation.canonical import identity, sha256_json, sha256_text
from english_master.schema_validation import load_document, validate_instance

ROOT = Path(__file__).resolve().parents[1]
PILOT = ROOT / "curriculum" / "ai-practice" / "pilot-batches" / "20260905-v13"


def _authority() -> VerifiedM6PracticeAuthority:
    return VerifiedM6PracticeAuthority.from_files(
        structure_path=ROOT / "curriculum" / "structure.json",
        snapshot_directory=ROOT / "data" / "reviews" / "m5" / "development-20260903-062008",
        source_registry_path=ROOT / "sources" / "registry.yaml",
        m6_batch_path=ROOT / "data" / "generated" / "m6" / "development-batches" / "20260903-v6" / "development-batch.json",
        m6_root=ROOT / "data" / "generated" / "m6" / "development-candidates" / "20260903-v6-selected",
    )


@pytest.fixture(scope="module")
def authority() -> VerifiedM6PracticeAuthority:
    return _authority()


def test_committed_real_pilot_has_full_lesson_specific_matrix(authority: VerifiedM6PracticeAuthority) -> None:
    result = verify_pilot(PILOT, authority)
    assert result["artifact_count"] == 40
    assert result["lesson_count"] == 10
    assert result["approval_tier"] == "MACHINE_VALIDATED"
    assert result["content_lifecycle_status"] == "UNREVIEWED"

    prompts = [json.loads(path.read_text(encoding="utf-8")) for path in sorted((PILOT / "prompts").glob("*.json"))]
    assert {(item["lesson_id"], item["modality"]) for item in prompts} == {
        (lesson_id, modality) for lesson_id in authority.lesson_ids for modality in MODALITIES
    }
    assert len({item["prompt_artifact_id"] for item in prompts}) == 40
    assert all(item["human_reviewed"] is False and item["release_approved"] is False for item in prompts)



def test_every_committed_record_is_schema_valid_and_scope_is_previous_knowledge(authority: VerifiedM6PracticeAuthority) -> None:
    validate_instance(load_document(PILOT / "authorization.json"), "ai-practice-authorization")
    validate_instance(load_document(PILOT / "batch-manifest.json"), "ai-practice-pilot-manifest")
    for path in (PILOT / "requests").glob("*.json"):
        request = load_document(path)
        validate_instance(request, "ai-practice-request")
        assert len(request["prerequisite_context"]) == len(set(request["prerequisite_context"]))
    for path in (PILOT / "prompts").glob("*.json"):
        validate_instance(load_document(path), "ai-practice-prompt-artifact")
    for path in (PILOT / "audits").glob("*.json"):
        validate_instance(load_document(path), "ai-practice-audit")

    request = load_document(PILOT / "requests" / "a1-u02-l01--speaking.json")
    assert "concept_present_simple" in request["known_grammar"]


    authorization = load_document(PILOT / "authorization.json")
    prompts = [json.loads(path.read_text(encoding="utf-8")) for path in (PILOT / "prompts").glob("*.json")]
    for prompt in prompts:
        request = load_document(PILOT / "requests" / f"{prompt['lesson_id'].lower()}--{prompt['modality'].lower()}.json")
        assert audit_artifact(prompt, authority=authority, request=request, authorization=authorization)["result"] == "PASS"
        payload = prompt["payload"]
        if prompt["modality"] == "LISTENING":
            assert payload["transcript_release"]["initially_hidden"] is True
            assert payload["turn_policy"]["maximum_questions_per_turn"] == 1
        elif prompt["modality"] == "SPEAKING":
            assert payload["learner_role"] and payload["assistant_role"]
            assert payload["turn_policy"]["maximum_questions_per_turn"] == 1
        elif prompt["modality"] == "PRONUNCIATION":
            assert payload["assessment_policy"]["without_audio_result"] == "NOT_ASSESSED"
        else:
            assert payload["states"][0] == "AWAIT_DRAFT"
            assert payload["feedback_policy"]["full_replacement_forbidden"] is True


def test_real_artifact_tampering_is_rejected(authority: VerifiedM6PracticeAuthority, tmp_path: Path) -> None:
    destination = tmp_path / "pilot"
    import shutil
    shutil.copytree(PILOT, destination)
    path = next((destination / "prompts").glob("*--listening.json"))
    prompt = json.loads(path.read_text(encoding="utf-8"))
    prompt["messages"]["initial_learner_visible"] = prompt["payload"]["private_transcript"]
    path.write_text(json.dumps(prompt), encoding="utf-8")
    with pytest.raises(ValueError, match="reconstructable"):
        verify_pilot(destination, authority)


def test_audit_detects_unsafe_pronunciation_and_writing_contracts(authority: VerifiedM6PracticeAuthority) -> None:
    authorization = load_document(PILOT / "authorization.json")
    pronunciation = json.loads(next((PILOT / "prompts").glob("*--pronunciation.json")).read_text(encoding="utf-8"))
    pronunciation_request = load_document(PILOT / "requests" / f"{pronunciation['lesson_id'].lower()}--pronunciation.json")
    pronunciation = copy.deepcopy(pronunciation)
    pronunciation["payload"]["assessment_policy"]["without_audio_result"] = "PASS"
    assert "PRONUNCIATION_ASSESSMENT_POLICY" in {issue["code"] for issue in audit_artifact(pronunciation, authority=authority, request=pronunciation_request, authorization=authorization)["issues"]}

    writing = json.loads(next((PILOT / "prompts").glob("*--writing.json")).read_text(encoding="utf-8"))
    writing_request = load_document(PILOT / "requests" / f"{writing['lesson_id'].lower()}--writing.json")
    writing = copy.deepcopy(writing)
    writing["payload"]["draft_required_before_feedback"] = False
    assert "WRITING_FEEDBACK_POLICY" in {issue["code"] for issue in audit_artifact(writing, authority=authority, request=writing_request, authorization=authorization)["issues"]}

    malformed = json.loads(next((PILOT / "prompts").glob("*--writing.json")).read_text(encoding="utf-8"))
    del malformed["payload"]["states"]
    assert "MALFORMED_MODALITY_PAYLOAD" in {issue["code"] for issue in audit_artifact(malformed, authority=authority, request=writing_request, authorization=authorization)["issues"]}

    invalid_payload = copy.deepcopy(pronunciation)
    invalid_payload["payload"] = {"junk": True}
    with pytest.raises(ValueError):
        validate_instance(invalid_payload, "ai-practice-prompt-artifact")



def test_builder_rejects_invalid_timestamp_and_rendered_system_contains_protocol(authority: VerifiedM6PracticeAuthority, tmp_path: Path) -> None:
    with pytest.raises(ValueError):
        build_pilot(authority, tmp_path / "invalid", created_at="not-a-timestamp")
    prompt = load_document(PILOT / "prompts" / "a1-u01-l01--listening.json")
    assert prompt["payload"]["private_transcript"] in prompt["messages"]["system"]
    assert prompt["payload"]["question_queue"][0]["expected_answer"] == prompt["payload"]["private_answer"]


    with pytest.raises(ValueError):
        build_pilot(authority, tmp_path / "future", created_at="9999-01-01T00:00:00Z")
    output = tmp_path / "pilot"
    build_pilot(authority, output, created_at="2026-09-04T10:00:00Z")
    assert verify_pilot(output, authority)["artifact_count"] == 40
    assert cli_main(["verify-pilot", "--pilot-dir", str(output)]) == 0
    with pytest.raises(FileExistsError):
        build_pilot(authority, output, created_at="2026-09-04T10:00:00Z")


def test_builder_rejects_destinations_nested_in_immutable_evidence(
    authority: VerifiedM6PracticeAuthority,
) -> None:
    for destination in (
        PILOT / "attempted-child",
        authority.snapshot_directory / "attempted-child",
        authority.m6_root / "attempted-child",
        authority.m6_batch_path.parent / "attempted-child",
    ):
        with pytest.raises(ValueError, match="nested.*immutable"):
            build_pilot(authority, destination, created_at="2026-09-04T10:00:00Z")
        assert not destination.exists()


def test_audit_rejects_self_consistent_unauthorized_protocol(authority: VerifiedM6PracticeAuthority) -> None:
    authorization = load_document(PILOT / "authorization.json")
    artifact = copy.deepcopy(load_document(PILOT / "prompts" / "a1-u01-l01--speaking.json"))
    request = load_document(PILOT / "requests" / "a1-u01-l01--speaking.json")
    artifact["payload"]["scenario"] = "Use an unauthorized advanced debate scenario."
    system, opening = _render(request, artifact["payload"])
    artifact["messages"] = {"system": system, "initial_learner_visible": opening}
    artifact["rendered_system_sha256"] = sha256_text(system)
    artifact["rendered_initial_sha256"] = sha256_text(opening)
    artifact["prompt_artifact_id"] = identity(
        "aipprompt",
        {key: value for key, value in artifact.items() if key not in {"prompt_artifact_id", "artifact_sha256"}},
        "prompt_artifact_id",
    )
    artifact["artifact_sha256"] = sha256_json({key: value for key, value in artifact.items() if key != "artifact_sha256"})
    result = audit_artifact(artifact, authority=authority, request=request, authorization=authorization)
    assert "ARTIFACT_RECONSTRUCTION_DRIFT" in {issue["code"] for issue in result["issues"]}


def test_review_only_lesson_uses_its_taxonomy_context(authority: VerifiedM6PracticeAuthority) -> None:
    prompt = load_document(PILOT / "prompts" / "a2-u04-l01--speaking.json")
    assert prompt["payload"]["feedback_policy"]["target_references"] == [
        "concept_collocation_make_decision",
        "concept_narrative_sequence",
    ]
    assert "lesson dialogue" not in prompt["payload"]["scenario"].casefold()
    request_help = load_document(PILOT / "prompts" / "a1-u02-l01--speaking.json")
    assert request_help["payload"]["opening_turn"].startswith("Your partner is ready.")
    vowel_practice = load_document(PILOT / "prompts" / "a1-u01-l02--pronunciation.json")
    assert vowel_practice["payload"]["target_utterance"] == "I live here. Did you say leave? No, live."
    advanced_writing = load_document(PILOT / "prompts" / "b1-u05-l02--writing.json")
    assert advanced_writing["payload"]["rubric_targets"] == [
        "vocab_en_run_002",
        "concept_past_perfect",
    ]
    assert "connected speech" not in advanced_writing["payload"]["communicative_goal"].casefold()


def test_v10_speaking_feedback_keeps_pronunciation_scope(authority: VerifiedM6PracticeAuthority, tmp_path: Path) -> None:
    successor = tmp_path / "v10-pilot"
    build_pilot(authority, successor, created_at="2026-09-11T08:00:00Z")
    assert verify_pilot(successor, authority)["artifact_count"] == 40
    prompt = load_document(successor / "prompts" / "b1-u05-l02--speaking.json")
    assert prompt["prompt_version"] == "M8_2_AI_PRACTICE_v10"
    assert prompt["payload"]["feedback_policy"]["target_references"] == [
        "vocab_en_run_002",
        "concept_past_perfect",
        "concept_pronunciation_linking",
        "concept_pronunciation_weak_forms",
    ]
    assert prompt["payload"]["pronunciation_feedback_policy"] == {
        "when_targets_present": "AUDIO_ONLY",
        "without_audio_result": "NOT_ASSESSED",
        "forbidden_without_audio": ["score", "phonetic_correctness_judgment", "accent_inference"],
    }



def test_mutated_reused_m6_authority_cannot_publish(tmp_path: Path) -> None:
    authority = _authority()
    with pytest.raises(TypeError):
        authority.m6_lesson_sha256["A1-U01-L01"] = "0" * 64
    authority.m6.lessons["A1-U01-L01"]["objectives"][0] = "tampered"
    with pytest.raises(ValueError, match="trusted M6 lesson mutated"):
        build_pilot(authority, tmp_path / "pilot", created_at="2026-09-04T10:00:00Z")
