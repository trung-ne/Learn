"""Deterministic M8.2 prompt construction and audit."""
from __future__ import annotations

import copy
import re
import unicodedata
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping

from english_master.lesson_generation.canonical import canonical_json, identity, sha256_json, sha256_text
from english_master.schema_validation import validate_instance

from .authority import MODALITIES, VerifiedM6PracticeAuthority
from .storage import publish_pilot

JsonObject = dict[str, Any]
SCOPE_FIELDS = (
    "known_vocabulary", "target_vocabulary", "review_vocabulary", "known_grammar", "target_grammar", "review_grammar",
    "known_functions", "target_functions", "review_functions", "known_pronunciation", "target_pronunciation", "review_pronunciation",
    "prerequisite_context", "taxonomy_context", "source_section_ids",
)
PRACTICE_SEEDS = {
    "A1-U01-L01": "I live in Hue.",
    "A1-U01-L02": "Live has /ɪ/; leave has /iː/.",
    "A1-U02-L01": "I ran home yesterday.",
    "A1-U02-L02": "Yesterday, I ran to the bus stop.",
    "A2-U03-L01": "At four, I was reading the timetable.",
    "A2-U03-L02": "Bus 12 leaves at 5:20 from Gate 4.",
    "A2-U04-L01": "I was walking to class.",
    "A2-U04-L02": "Mai was running home when it began to rain.",
    "B1-U05-L01": "Mina had packed before she left.",
    "B1-U05-L02": "Before then, Lan had run an event at school.",
}
MODALITY_PRACTICE_SEEDS = {
    ("A1-U01-L01", "SPEAKING"): "Where do you live?",
    ("A1-U01-L01", "WRITING"): "Where do you live?",
    ("A1-U01-L02", "LISTENING"): "I live here.",
    ("A1-U01-L02", "PRONUNCIATION"): "I live here. Did you say leave? No, live.",
    ("A1-U01-L02", "SPEAKING"): "Did you say leave?",
    ("A1-U01-L02", "WRITING"): "Did you say leave?",
    ("A1-U02-L01", "LISTENING"): "Mai ran to the station because she was late.",
    ("A1-U02-L01", "SPEAKING"): "Please help me.",
    ("A1-U02-L01", "WRITING"): "Please help me.",
    ("A1-U02-L02", "SPEAKING"): "Please help me write my address on this form.",
    ("A1-U02-L02", "WRITING"): "Please help me write my address on this form.",
}
PRACTICE_SEED_SOURCE_FRAGMENTS = {
    ("A1-U01-L02", "PRONUNCIATION"): ("I live here", "Did you say leave", "No, live"),
}


def _scope_projection(request: Mapping[str, Any]) -> JsonObject:
    return {key: copy.deepcopy(request[key]) for key in SCOPE_FIELDS}


def _normalized(value: str) -> str:
    return " ".join(unicodedata.normalize("NFKC", value).casefold().split())


def _compact(value: str) -> str:
    return "".join(character for character in _normalized(value) if character.isalnum())


def _timestamp(value: str | None) -> str:
    if value is not None:
        return value
    return datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def _lesson_context(authority: VerifiedM6PracticeAuthority, request: Mapping[str, Any]) -> tuple[Mapping[str, Any], str, str]:
    lesson = authority.m6.lesson(request["lesson_id"])
    source_text = " ".join(section["body_text"] for section in lesson["content_sections"])
    utterance = MODALITY_PRACTICE_SEEDS.get((request["lesson_id"], request["modality"]), PRACTICE_SEEDS.get(request["lesson_id"]))
    fragments = PRACTICE_SEED_SOURCE_FRAGMENTS.get(
        (request["lesson_id"], request["modality"]),
        (utterance,) if utterance is not None else (),
    )
    if utterance is None or any(_compact(fragment) not in _compact(source_text) for fragment in fragments):
        raise ValueError(f"M8.2 practice seed is absent from trusted lesson content: {request['lesson_id']}")
    return lesson, utterance, source_text


def _references(request: Mapping[str, Any], *fields: str) -> list[str]:
    return list(dict.fromkeys(identifier for field in fields for identifier in request[field]))


def _active_language_targets(request: Mapping[str, Any]) -> list[str]:
    """Use introduced targets when present, then relevant outline context.

    Review-only lessons may introduce no grammar/function/vocabulary directly.
    Their taxonomy context supplies the lesson-specific capability focus rather
    than silently redirecting feedback to an unrelated earlier lesson.
    """
    active = _references(
        request,
        "target_vocabulary", "target_grammar", "target_functions",
        "review_vocabulary", "review_grammar", "review_functions",
    )
    if not active:
        active = _references(request, "taxonomy_context")
    if not active:
        active = _references(request, "known_vocabulary", "known_grammar", "known_functions")
    return active


def _payload(request: Mapping[str, Any], lesson: Mapping[str, Any], utterance: str) -> JsonObject:
    modality = request["modality"]
    objective = request["objectives"][0]
    language_targets = _active_language_targets(request)
    writing_targets = language_targets
    if modality == "LISTENING":
        transcript = f"Speaker: {utterance}"
        return {
            "system_role": "lesson-bound listening tutor",
            "learner_visible_opening": f"Listen to a short {request['cefr_level']} exchange from {lesson['title']}. Do not read a transcript yet. Reply READY for audio.",
            "private_transcript": transcript,
            "private_answer": utterance,
            "delivery": {"required_mode": "AUDIO_OR_SPEECH", "text_only_completion": "NOT_COMPLETED"},
            "transcript_release": {"allowed_after": "LEARNER_ATTEMPT_OR_EXPLICIT_REQUEST", "initially_hidden": True},
            "question_queue": [{"question_id": "q1", "text": "What did the speaker say? Write the utterance; accept equivalent word-form or numeral formatting.", "expected_answer": utterance}],
            "answer_evaluation": {"accept_equivalent_spelling_and_number_formatting": True, "require_exact_punctuation": False},
            "turn_policy": {"one_question_at_a_time": True, "maximum_questions_per_turn": 1},
            "completion_criteria": ["audio_or_speech_delivered", "learner_attempted_q1"],
        }
    if modality == "SPEAKING":
        if request["target_functions"]:
            scenario_scope = "the declared communicative function"
        elif request["target_vocabulary"] or request["target_grammar"]:
            scenario_scope = "the declared vocabulary and grammar scope"
        elif request["taxonomy_context"]:
            scenario_scope = "the declared lesson taxonomy context"
        else:
            scenario_scope = "the declared previously learned scope"
        return {
            "system_role": "lesson-bound roleplay partner",
            "learner_role": f"learner as the speaker working toward: {objective}",
            "assistant_role": "conversation partner in a lesson-bound practice situation",
            "scenario": f"Use the lesson example from {lesson['title']} as a starting point and practise {scenario_scope}.",
            "communicative_goal": objective,
            "success_condition": "The learner completes the declared communicative goal with a lesson-scoped response before the turn cap.",
            "stop_condition": "Stop after the communicative goal is completed or six roleplay turns occur.",
            "turn_policy": {"one_question_at_a_time": True, "maximum_questions_per_turn": 1, "maximum_roleplay_turns": 6},
            "feedback_policy": {"timing": "AFTER_ROLEPLAY", "maximum_priorities": 2, "target_references": language_targets},
            "opening_turn": f"Your partner is ready. In your own words, work toward the stated goal using this lesson example as a model: {utterance}",
        }
    if modality == "PRONUNCIATION":
        practice_targets = _references(request, "target_pronunciation", "review_pronunciation") or _references(request, "known_pronunciation")
        return {
            "system_role": "lesson-bound pronunciation practice tutor",
            "learner_visible_opening": f"Say or record this exact lesson utterance for audio-based practice: {utterance}",
            "practice_targets": practice_targets,
            "target_utterance": utterance,
            "feature_guidance": f"Use the lesson pronunciation references: {', '.join(practice_targets) if practice_targets else 'review only; no new feature is authorized'}.",
            "assessment_policy": {"required_input": "AUDIO", "without_audio_result": "NOT_ASSESSED", "forbidden_without_audio": ["score", "phonetic_correctness_judgment", "accent_inference"]},
            "external_audio_included": False,
            "turn_policy": {"one_question_at_a_time": True, "maximum_questions_per_turn": 1},
        }
    return {
        "system_role": "lesson-bound writing feedback tutor",
        "writing_task": f"Write two short lesson-scoped sentences based on this example: {utterance}",
        "communicative_goal": "Write clear sentences that demonstrate the authorized written language targets.",
        "states": ["AWAIT_DRAFT", "FEEDBACK", "REVISION"],
        "draft_required_before_feedback": True,
        "feedback_policy": {"maximum_priorities": 3, "preserve_learner_meaning": True, "full_replacement_forbidden": True, "model_answer_label_required": True},
        "rubric_targets": writing_targets,
        "turn_policy": {"maximum_clarification_or_revision_questions_per_turn": 1},
    }


def _render(request: Mapping[str, Any], payload: Mapping[str, Any]) -> tuple[str, str]:
    executable_scope = _scope_projection(request)
    system = (
        "You must follow this immutable M8.2 lesson-bound protocol exactly. "
        f"Lesson={request['lesson_id']}; CEFR band={request['cefr_level'][:2]}; internal curriculum tier={request['cefr_level']}; lesson_hash={request['lesson_sha256']}; modality={request['modality']}. "
        "Use only declared lesson scope. Do not claim human review, release approval, provider authentication, or external-source checking. "
        f"Trusted scope={canonical_json(executable_scope)}. Executable protocol={canonical_json(dict(payload))}."
    )
    opening = str(payload.get("learner_visible_opening") or payload.get("opening_turn") or payload.get("writing_task") or payload.get("target_utterance"))
    return system, opening


def build_artifact(authority: VerifiedM6PracticeAuthority, authorization: Mapping[str, Any], request: Mapping[str, Any], *, generated_at: str) -> JsonObject:
    expected_request = authority.request(request["lesson_id"], request["modality"], authorization)
    if dict(request) != expected_request:
        raise ValueError("M8.2 artifact requires a reconstructable authority-derived request")
    lesson, utterance, _ = _lesson_context(authority, request)
    payload = _payload(request, lesson, utterance)
    system, opening = _render(request, payload)
    artifact: JsonObject = {
        "schema_version": "1.0", "record_type": "ai_practice_prompt_artifact", "prompt_artifact_id": "PENDING",
        "authorization_id": authorization["authorization_id"], "authorization_sha256": sha256_json(authorization),
        "request_id": request["request_id"], "request_sha256": sha256_json(request),
        "lesson_id": request["lesson_id"], "lesson_sha256": request["lesson_sha256"], "lesson_audit_sha256": request["lesson_audit_sha256"],
        "cefr_level": request["cefr_level"], "modality": request["modality"],
        "scope": _scope_projection(request),
        "prompt_version": request["prompt_version"], "messages": {"system": system, "initial_learner_visible": opening}, "payload": payload,
        "provenance": {"origin": "PROJECT_AUTHORED", "external_text": False, "external_media": False, "generator": "english_master.ai_practice", "generator_version": "2.0", "curriculum_version": authority.m6.m5.bundle.structure["curriculum_version"], "provider": "UNKNOWN", "model": "UNKNOWN", "provider_run_id": "UNKNOWN", "provider_authenticated": False, "generated_at": generated_at},
        "content_lifecycle_status": "UNREVIEWED", "human_reviewed": False, "release_approved": False,
        "rendered_system_sha256": sha256_text(system), "rendered_initial_sha256": sha256_text(opening), "artifact_sha256": "PENDING",
    }
    # Both identity fields are derived fields and excluded from their source projection.
    artifact["prompt_artifact_id"] = identity("aipprompt", {key: value for key, value in artifact.items() if key not in {"prompt_artifact_id", "artifact_sha256"}}, "prompt_artifact_id")
    artifact["artifact_sha256"] = sha256_json({key: value for key, value in artifact.items() if key != "artifact_sha256"})
    validate_instance(artifact, "ai-practice-prompt-artifact")
    return artifact


def audit_artifact(
    artifact: Mapping[str, Any],
    *,
    authority: VerifiedM6PracticeAuthority,
    request: Mapping[str, Any],
    authorization: Mapping[str, Any],
    audited_at: str | None = None,
) -> JsonObject:
    """Audit an artifact against independently reconstructed M6 authority."""
    issues: list[JsonObject] = []
    try:
        expected_artifact = build_artifact(
            authority,
            authorization,
            request,
            generated_at=artifact["provenance"]["generated_at"],
        )
        if dict(artifact) != expected_artifact:
            issues.append({"code": "ARTIFACT_RECONSTRUCTION_DRIFT", "path": "$", "message": "artifact differs from the authority-derived modality protocol"})
    except (KeyError, TypeError, ValueError):
        issues.append({"code": "ARTIFACT_RECONSTRUCTION_DRIFT", "path": "$", "message": "artifact cannot be reconstructed from trusted authority"})
    payload = artifact["payload"]
    modality = artifact["modality"]
    if artifact["content_lifecycle_status"] != "UNREVIEWED" or artifact["human_reviewed"] or artifact["release_approved"]:
        issues.append({"code": "LIFECYCLE_ESCALATION", "path": "$", "message": "artifact claims disallowed approval"})
    provenance = artifact["provenance"]
    if provenance["origin"] != "PROJECT_AUTHORED" or provenance["external_text"] or provenance["external_media"] or provenance["provider_authenticated"]:
        issues.append({"code": "PROVENANCE_POLICY", "path": "$.provenance", "message": "artifact exceeds project-authored policy"})
    expected_hash = sha256_json({key: value for key, value in artifact.items() if key != "artifact_sha256"})
    expected_artifact_id = identity("aipprompt", {key: value for key, value in artifact.items() if key not in {"prompt_artifact_id", "artifact_sha256"}}, "prompt_artifact_id")
    if artifact["prompt_artifact_id"] != expected_artifact_id:
        issues.append({"code": "ARTIFACT_ID_DRIFT", "path": "$.prompt_artifact_id", "message": "artifact identity is not canonical"})
    if artifact["artifact_sha256"] != expected_hash or artifact["rendered_system_sha256"] != sha256_text(artifact["messages"]["system"]) or artifact["rendered_initial_sha256"] != sha256_text(artifact["messages"]["initial_learner_visible"]):
        issues.append({"code": "ARTIFACT_HASH_DRIFT", "path": "$", "message": "artifact or rendered message hash drift"})
    bindings = (artifact["authorization_id"] == authorization["authorization_id"] and artifact["authorization_sha256"] == sha256_json(authorization) and artifact["request_id"] == request["request_id"] and artifact["request_sha256"] == sha256_json(request) and artifact["lesson_id"] == request["lesson_id"] and artifact["lesson_sha256"] == request["lesson_sha256"] and artifact["lesson_audit_sha256"] == request["lesson_audit_sha256"] and artifact["cefr_level"] == request["cefr_level"] and artifact["modality"] == request["modality"])
    expected_scope = _scope_projection(request)
    if not bindings or artifact["scope"] != expected_scope:
        issues.append({"code": "AUTHORITY_SCOPE_DRIFT", "path": "$.scope", "message": "artifact binding or scope differs from request"})
    expected_system, expected_opening = _render(request, payload)
    if artifact["messages"] != {"system": expected_system, "initial_learner_visible": expected_opening}:
        issues.append({"code": "RENDERED_PROTOCOL_DRIFT", "path": "$.messages", "message": "rendered messages differ from the bound payload and scope"})
    try:
        if modality == "LISTENING":
            for private_key in ("private_transcript", "private_answer"):
                private = payload[private_key]
                protected_fragments = [_compact(private)] + [
                    _compact(fragment) for fragment in re.split(r"(?<=[.!?])\s+", private)
                    if len(_compact(fragment)) >= 6
                ]
                if any(fragment and fragment in _compact(artifact["messages"]["initial_learner_visible"]) for fragment in protected_fragments):
                    issues.append({"code": "LISTENING_PRIVATE_LEAK", "path": "$.messages.initial_learner_visible", "message": f"{private_key} or a substantive fragment is visible before attempt"})
            if payload["private_answer"] not in payload["private_transcript"] or payload["question_queue"][0]["expected_answer"] != payload["private_answer"] or not payload["turn_policy"]["one_question_at_a_time"] or payload["turn_policy"]["maximum_questions_per_turn"] != 1:
                issues.append({"code": "LISTENING_TURN_OR_ANSWER_POLICY", "path": "$.payload", "message": "listening must have one answerable queued question"})
        elif modality == "SPEAKING":
            policy = payload["turn_policy"]
            if not payload["learner_role"] or not payload["assistant_role"] or not payload["stop_condition"] or not policy["one_question_at_a_time"] or policy["maximum_questions_per_turn"] != 1:
                issues.append({"code": "SPEAKING_ROLEPLAY_POLICY", "path": "$.payload", "message": "speaking roleplay contract is incomplete"})
            expected_targets = _active_language_targets(request)
            if payload["feedback_policy"]["target_references"] != expected_targets:
                issues.append({"code": "SPEAKING_SCOPE_DRIFT", "path": "$.payload.feedback_policy.target_references", "message": "speaking feedback targets differ from the authorized active scope"})
        elif modality == "PRONUNCIATION":
            policy = payload["assessment_policy"]
            if not payload["target_utterance"] or policy["required_input"] != "AUDIO" or policy["without_audio_result"] != "NOT_ASSESSED" or not set(("score", "phonetic_correctness_judgment", "accent_inference")).issubset(policy["forbidden_without_audio"]):
                issues.append({"code": "PRONUNCIATION_ASSESSMENT_POLICY", "path": "$.payload.assessment_policy", "message": "pronunciation fallback is unsafe"})
            expected_targets = _references(request, "target_pronunciation", "review_pronunciation") or _references(request, "known_pronunciation")
            if payload["practice_targets"] != expected_targets:
                issues.append({"code": "PRONUNCIATION_SCOPE_DRIFT", "path": "$.payload.practice_targets", "message": "pronunciation targets differ from the authorized active scope"})
        elif modality == "WRITING":
            policy = payload["feedback_policy"]
            if not payload["draft_required_before_feedback"] or payload["states"][0] != "AWAIT_DRAFT" or policy["full_replacement_forbidden"] is not True or payload["turn_policy"]["maximum_clarification_or_revision_questions_per_turn"] != 1:
                issues.append({"code": "WRITING_FEEDBACK_POLICY", "path": "$.payload", "message": "writing must be draft-first and bounded"})
            expected_targets = _active_language_targets(request)
            if payload["rubric_targets"] != expected_targets:
                issues.append({"code": "WRITING_SCOPE_DRIFT", "path": "$.payload.rubric_targets", "message": "writing rubric targets differ from the authorized active scope"})
        else:
            issues.append({"code": "UNSUPPORTED_MODALITY", "path": "$.modality", "message": "unsupported prompt modality"})
    except (IndexError, KeyError, TypeError):
        issues.append({"code": "MALFORMED_MODALITY_PAYLOAD", "path": "$.payload", "message": "payload cannot satisfy the declared modality contract"})
    value: JsonObject = {"schema_version": "1.0", "record_type": "ai_practice_audit", "audit_id": "PENDING", "prompt_artifact_id": artifact["prompt_artifact_id"], "artifact_sha256": artifact["artifact_sha256"], "checks": ["AUTHORITY_SCOPE", "CEFR_SCOPE", "PREREQUISITE_SCOPE", "PROVENANCE", "RENDERED_MESSAGE_HASHES", "MODALITY_POLICY", "LIFECYCLE"], "issues": issues, "result": "PASS" if not issues else "FAIL", "qa_reviewer": "english_master.ai_practice.deterministic_audit", "qa_timestamp": audited_at or artifact["provenance"]["generated_at"], "limitations": ["Deterministic instruction-contract audit only; no live model behavior, human review, provider authentication, or Internet-wide search was performed."]}
    value["audit_id"] = identity("aipaudit", value, "audit_id")
    validate_instance(value, "ai-practice-audit")
    return value


def build_pilot(authority: VerifiedM6PracticeAuthority, output_directory: Path, *, created_at: str | None = None, prompt_version: str = "M8_2_AI_PRACTICE_v9") -> Path:
    created_at = _timestamp(created_at)
    authorization = authority.authorization(created_at=created_at, prompt_version=prompt_version)
    validate_instance(authorization, "ai-practice-authorization")
    entries: list[tuple[JsonObject, JsonObject, JsonObject]] = []
    for lesson_id in authority.lesson_ids:
        for modality in MODALITIES:
            request = authority.request(lesson_id, modality, authorization)
            validate_instance(request, "ai-practice-request")
            artifact = build_artifact(authority, authorization, request, generated_at=created_at)
            audit = audit_artifact(artifact, authority=authority, request=request, authorization=authorization, audited_at=created_at)
            if audit["result"] != "PASS":
                raise ValueError(f"M8.2 artifact audit failed: {lesson_id} {modality}: {audit['issues']}")
            entries.append((request, artifact, audit))
    return publish_pilot(output_directory, authority, authorization, entries, created_at=created_at)
