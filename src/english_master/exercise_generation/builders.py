"""Deterministic M7 authorization and request construction."""
from __future__ import annotations

import copy
from dataclasses import dataclass
from typing import Any, Mapping

from english_master.lesson_generation.canonical import identity, sha256_json
from english_master.schema_validation import validate_instance

from .authority import VerifiedM6DevelopmentAuthority
from .models import ExerciseGenerationRequest, JsonObject

EXERCISE_TYPES = ("multiple_choice","fill_blank","matching","ordering","error_correction","sentence_construction","translation","reading","listening","speaking","writing")
DEFAULT_MAXIMUMS = {"multiple_choice":8,"fill_blank":8,"matching":5,"ordering":5,"error_correction":5,"sentence_construction":5,"translation":5,"reading":1,"listening":1,"speaking":1,"writing":1}


@dataclass(frozen=True)
class ExerciseGenerationConfig:
    generator: str = "english_master.exercise_generation"
    generator_version: str = "1.0"
    prompt_version: str = "M7_EXERCISE_GENERATOR_v1"
    curriculum_version: str = "20260903"
    parameters: Mapping[str, Any] | None = None
    seed: int | None = 7
    revision: int = 1
    permitted_types: tuple[str, ...] = EXERCISE_TYPES


def build_authorization(authority: VerifiedM6DevelopmentAuthority, lesson_ids: tuple[str, ...] | list[str] | None = None) -> JsonObject:
    value = authority.authorization(lesson_ids)
    validate_instance(value, "exercise-generation-authorization")
    return value


def _references(lesson: Mapping[str, Any]) -> tuple[list[str], list[str]]:
    targets = sorted(set(lesson.get("grammar_introduced", []) + lesson.get("vocabulary_introduced", []) + lesson.get("functions_introduced", []) + lesson.get("pronunciation_introduced", []) + lesson.get("taxonomy_concepts", [])))
    reviews = sorted(set(lesson.get("grammar_reviewed", []) + lesson.get("vocabulary_reviewed", []) + lesson.get("functions_reviewed", []) + lesson.get("pronunciation_reviewed", [])))
    return targets, reviews


def build_request(authority: VerifiedM6DevelopmentAuthority, authorization: Mapping[str, Any], lesson_id: str, config: ExerciseGenerationConfig = ExerciseGenerationConfig()) -> ExerciseGenerationRequest:
    expected = build_authorization(authority, [item["lesson_id"] for item in authorization.get("lesson_bindings", [])] if isinstance(authorization.get("lesson_bindings"), list) else [])
    if dict(authorization) != expected:
        raise ValueError("authorization does not equal the independently derived M6 authority scope")
    if lesson_id not in {item["lesson_id"] for item in expected["lesson_bindings"]}:
        raise ValueError("lesson is outside authorization")
    if config.revision < 1 or not config.permitted_types or any(item not in EXERCISE_TYPES for item in config.permitted_types):
        raise ValueError("invalid M7 generation configuration")
    lesson = authority.lesson(lesson_id)
    binding = authority.binding(lesson_id)
    targets, reviews = _references(lesson)
    allowed = sorted(set(targets + reviews))
    if not allowed:
        raise ValueError("lesson contains no machine-authorized exercise references")
    maximum_counts = {name: DEFAULT_MAXIMUMS[name] for name in config.permitted_types}
    value: JsonObject = {"schema_version":"1.0","record_type":"exercise_generation_request","request_id":"PENDING","authorization_id":expected["authorization_id"],"authorization_sha256":sha256_json(expected),"m6_batch_id":authority.batch["batch_id"],"lesson_binding":{"lesson_id":lesson_id,"lesson_sha256":binding["lesson_sha256"],"audit_sha256":binding["audit_sha256"]},"lesson_spec":{"title":lesson["title"],"cefr_level":lesson["cefr_level"],"objectives":copy.deepcopy(lesson["objectives"]),"targets":targets,"review_references":reviews,"allowed_references":allowed,"skills":sorted(lesson.get("skills", []))},"constraints":{"permitted_types":list(config.permitted_types),"maximum_counts":maximum_counts,"max_prompt_chars":1000,"max_option_chars":160,"max_stimulus_chars":1800,"translation_directions":["vi_to_en","en_to_vi"],"forbidden_terms":["AI tutor","evaluate pronunciation","spaced repetition","placement test"],"external_stimuli":"FORBIDDEN","external_media":"FORBIDDEN","allow_m8_artifacts":False},"generation_config":{"generator":config.generator,"generator_version":config.generator_version,"prompt_version":config.prompt_version,"curriculum_version":config.curriculum_version,"exercise_schema_version":"1.0","parameters":dict(config.parameters or {}),"seed":config.seed,"revision":config.revision}}
    value["request_id"] = identity("m7req", value, "request_id")
    validate_instance(value, "exercise-generation-request")
    return ExerciseGenerationRequest(value)
