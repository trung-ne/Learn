"""Deterministic snapshot-derived M6 authorization and request builders."""

from __future__ import annotations

import copy
from dataclasses import dataclass, field
from typing import Any, Iterable, Mapping

from english_master.schema_validation import validate_instance

from .authority import _VerifiedM5Base
from .canonical import authorization_id, request_id, sha256_json
from .derivation import (
    FAMILIES,
    annotation_index,
    canonical_edges,
    derive_context,
    record_cefr,
    record_definition,
    record_type,
)
from .models import JsonObject

INPUT_POLICY = "REVIEWED_M2_M5_TAXONOMY_ONLY"


@dataclass(frozen=True)
class GenerationConfig:
    """Caller-selected bounded generation controls without provider claims."""

    duration_minutes: int = 35
    forbidden_terms: tuple[str, ...] = ("advanced idiom", "notwithstanding")
    max_target_vocabulary: int = 4
    max_sections: int = 4
    max_section_characters: int = 500
    max_total_characters: int = 1200
    generator: str = "english_master.lesson_generation"
    generator_version: str = "2.0"
    prompt_version: str = "M6_LESSON_GENERATOR_v3"
    parameters: Mapping[str, str | int | float | bool | None] = field(
        default_factory=lambda: {"temperature": 0}
    )
    seed: int | None = None


def _approved_snapshot_records(m5: _VerifiedM5Base) -> dict[str, Mapping[str, Any]]:
    values = m5.snapshot.get("approved_taxonomy_records", [])
    if not isinstance(values, list):
        return {}
    return {
        record["id"]: record
        for record in values
        if isinstance(record, Mapping) and isinstance(record.get("id"), str)
    }


def _reviewed_snapshot_annotations(m5: _VerifiedM5Base) -> dict[str, Mapping[str, Any]]:
    values = m5.snapshot.get("reviewed_annotation_records", [])
    if not isinstance(values, list):
        return {}
    return {
        record["id"]: record
        for record in values
        if isinstance(record, Mapping) and isinstance(record.get("id"), str)
    }


def _required_record_ids(m5: _VerifiedM5Base, lesson_ids: Iterable[str]) -> set[str]:
    required: set[str] = set()
    for lesson_id in lesson_ids:
        context = derive_context(m5.bundle, lesson_id)
        if context["lesson"] is None:
            raise ValueError(f"lesson {lesson_id!r} is absent from verified M5 structure")
        if context["unresolved_closure"]:
            raise ValueError(
                "unresolved taxonomy prerequisite closure: "
                + ", ".join(context["unresolved_closure"])
            )
        for family in FAMILIES:
            required.update(context["introduced"][family])
            required.update(context["reviewed"][family])
        required.update(context["supporting"])
        required.update(context["closure"])
    return required


def build_authorization(
    m5: _VerifiedM5Base,
    lesson_ids: Iterable[str],
) -> JsonObject:
    """Build an exact narrowing of a verified M5 approval snapshot."""

    requested = list(lesson_ids)
    if not requested or len(requested) != len(set(requested)):
        raise ValueError("authorization requires distinct lesson IDs")
    lesson_order = derive_context(m5.bundle, requested[0])["lesson_order"]
    positions = {lesson_id: index for index, lesson_id in enumerate(lesson_order)}
    if any(lesson_id not in positions for lesson_id in requested):
        missing = sorted(set(requested) - positions.keys())
        raise ValueError(f"lessons absent from verified M5 structure: {', '.join(missing)}")
    selected_lessons = sorted(requested, key=lambda lesson_id: positions[lesson_id])
    required_ids = _required_record_ids(m5, selected_lessons)
    taxonomy = derive_context(m5.bundle, selected_lessons[0])["taxonomy"]
    approved = _approved_snapshot_records(m5)
    missing_approval = sorted(required_ids - approved.keys())
    if missing_approval:
        raise ValueError(
            "verified snapshot does not approve required taxonomy records: "
            + ", ".join(missing_approval)
        )
    records: list[JsonObject] = []
    for record_id in sorted(required_ids):
        source = taxonomy[record_id]
        source_hash = sha256_json(source)
        if approved[record_id].get("sha256") != source_hash:
            raise ValueError(f"snapshot hash mismatch for taxonomy record {record_id!r}")
        records.append(
            {
                "id": record_id,
                "record_type": record_type(source),
                "cefr": record_cefr(source),
                "source_status": source.get("status"),
                "approval_basis": "M5_SNAPSHOT_OVERLAY",
                "taxonomy_record_hash": source_hash,
            }
        )
    payload: JsonObject = {
        "schema_version": "2.0",
        "record_type": "lesson_generation_authorization",
        "authority_source": (
            "VERIFIED_M5_DEVELOPMENT_SNAPSHOT"
            if m5.snapshot.get("record_type") == "curriculum_development_snapshot"
            else "VERIFIED_M5_APPROVAL_SNAPSHOT"
        ),
        "snapshot_binding": m5.snapshot_binding(),
        "curriculum_version": m5.bundle.structure.get("curriculum_version"),
        "taxonomy_version": m5.bundle.taxonomy.get("taxonomy_version"),
        "artifact_hashes": m5.artifact_hashes(),
        "approved_lesson_ids": selected_lessons,
        "records": records,
        "generation_policy": {
            "input_policy": INPUT_POLICY,
            "source_payloads_included": False,
            "content_generation_allowed": True,
        },
    }
    payload["authorization_id"] = authorization_id(payload)
    validate_instance(payload, "lesson-generation-authorization")
    return payload


def _teaching_record(source: Mapping[str, Any]) -> JsonObject:
    payload: JsonObject = {
        "id": source["id"],
        "record_type": record_type(source),
        "name": source.get("name", source.get("lemma")),
        "definition": record_definition(source),
        "cefr": record_cefr(source),
        "prerequisites": sorted(source.get("prerequisites", [])),
        "taxonomy_record_hash": sha256_json(source),
        "content_origin": "PROJECT_AUTHORED",
    }
    optional_fields = (
        "subtype",
        "language",
        "lemma",
        "part_of_speech",
        "sense_number",
        "collocations",
        "chunks",
        "examples",
    )
    for field_name in optional_fields:
        if field_name in source:
            payload[field_name] = copy.deepcopy(source[field_name])
    return payload


def _annotation_context(
    m5: _VerifiedM5Base,
    required_ids: set[str],
) -> list[JsonObject]:
    annotations = annotation_index(m5.bundle)
    reviewed = _reviewed_snapshot_annotations(m5)
    result: list[JsonObject] = []
    for annotation_id in sorted(annotations):
        source = annotations[annotation_id]
        if source.get("target_id") not in required_ids:
            continue
        source_hash = sha256_json(source)
        authority = reviewed.get(annotation_id)
        if authority is None or authority.get("sha256") != source_hash:
            raise ValueError(
                f"annotation {annotation_id!r} is not hash-bound in the verified snapshot"
            )
        result.append(
            {
                "id": annotation_id,
                "target_id": source["target_id"],
                "annotation_kind": source["annotation_kind"],
                "difficulty": source["difficulty"],
                "description": source["description"],
                "teaching_response": source["teaching_response"],
                "context_only": True,
                "taxonomy_record_hash": source_hash,
                "content_origin": "PROJECT_AUTHORED",
            }
        )
    return result


def build_request(
    m5: _VerifiedM5Base,
    authorization: Mapping[str, Any],
    lesson_id: str,
    *,
    config: GenerationConfig = GenerationConfig(),
) -> JsonObject:
    """Build one request from verified graph, taxonomy, and snapshot state."""

    expected_authorization = build_authorization(
        m5,
        authorization.get("approved_lesson_ids", [])
        if isinstance(authorization.get("approved_lesson_ids"), list)
        else [],
    )
    if dict(authorization) != expected_authorization:
        raise ValueError("authorization is not the deterministic snapshot-derived value")
    if lesson_id not in expected_authorization["approved_lesson_ids"]:
        raise ValueError(f"lesson {lesson_id!r} is not in the narrow authorization")
    context = derive_context(m5.bundle, lesson_id)
    lesson = context["lesson"]
    assert isinstance(lesson, dict)
    direct_ids = set(context["supporting"])
    for family in FAMILIES:
        direct_ids.update(context["introduced"][family])
        direct_ids.update(context["reviewed"][family])
    closure_ids = set(context["closure"]) - direct_ids
    required_ids = direct_ids | closure_ids
    taxonomy = context["taxonomy"]
    approved_ids = set(_approved_snapshot_records(m5))
    teaching_records = [_teaching_record(taxonomy[record_id]) for record_id in sorted(required_ids)]
    annotations = _annotation_context(m5, required_ids)
    teaching_payload: JsonObject = {
        "input_policy": INPUT_POLICY,
        "external_source_payloads_included": False,
        "records": teaching_records,
        "vietnamese_learner_context": annotations,
    }
    teaching_payload["payload_sha256"] = sha256_json(teaching_payload)
    request: JsonObject = {
        "schema_version": "2.0",
        "record_type": "lesson_generation_request",
        "authorization_id": authorization["authorization_id"],
        "authorization_sha256": sha256_json(authorization),
        "snapshot_binding": m5.snapshot_binding(),
        "artifact_hashes": m5.artifact_hashes(),
        "lesson_spec": {
            "id": lesson["id"],
            "title": lesson["title"],
            "unit_id": lesson["unit_id"],
            "lesson_number": lesson["lesson_number"],
            "cefr": lesson["cefr"],
            "duration_minutes": config.duration_minutes,
            "objectives": copy.deepcopy(lesson["objectives"]),
            "grammar_introduced": context["introduced"]["grammar"],
            "grammar_reviewed": context["reviewed"]["grammar"],
            "vocabulary_introduced": context["introduced"]["vocabulary"],
            "vocabulary_reviewed": context["reviewed"]["vocabulary"],
            "functions_introduced": context["introduced"]["functions"],
            "functions_reviewed": context["reviewed"]["functions"],
            "pronunciation_introduced": context["introduced"]["pronunciation"],
            "pronunciation_reviewed": context["reviewed"]["pronunciation"],
            "taxonomy_concepts": context["supporting"],
            "skills": sorted(lesson.get("skills", [])),
            "dimensions": sorted(lesson.get("dimensions", [])),
            "prerequisites": context["direct_prerequisites"],
            "review_of": sorted(lesson.get("review_of", [])),
            "lesson_kind": lesson["lesson_kind"],
        },
        "graph": {
            "lesson_order": context["lesson_order"],
            "prerequisite_edges": canonical_edges(context["prerequisite_pairs"]),
            "introduction_edges": canonical_edges(context["introduction_pairs"]),
            "review_edges": canonical_edges(context["review_pairs"]),
            "resolved_prerequisite_closure": context["closure"],
        },
        "previous_knowledge": context["previous"],
        "constraints": {
            "target_cefr": lesson["cefr"],
            "allowed_grammar": sorted(
                set(context["introduced"]["grammar"])
                | set(context["reviewed"]["grammar"])
            ),
            "allowed_vocabulary": sorted(
                set(context["introduced"]["vocabulary"])
                | set(context["reviewed"]["vocabulary"])
            ),
            "allowed_functions": sorted(
                set(context["introduced"]["functions"])
                | set(context["reviewed"]["functions"])
            ),
            "allowed_pronunciation": sorted(
                set(context["introduced"]["pronunciation"])
                | set(context["reviewed"]["pronunciation"])
            ),
            "allowed_supporting": context["supporting"],
            "context_only_prerequisites": sorted(closure_ids),
            "forbidden_ids": sorted(approved_ids - required_ids),
            "forbidden_terms": sorted(set(config.forbidden_terms)),
            "max_target_vocabulary": config.max_target_vocabulary,
            "max_sections": config.max_sections,
            "max_section_characters": config.max_section_characters,
            "max_total_characters": config.max_total_characters,
        },
        "teaching_payload": teaching_payload,
        "generation_config": {
            "generator": config.generator,
            "generator_version": config.generator_version,
            "prompt_version": config.prompt_version,
            "curriculum_version": m5.bundle.structure["curriculum_version"],
            "taxonomy_version": m5.bundle.taxonomy["taxonomy_version"],
            "lesson_schema_version": "1.0",
            "parameters": copy.deepcopy(dict(config.parameters)),
            "seed": config.seed,
        },
        "requested_outputs": ["lesson"],
    }
    request["request_id"] = request_id(request)
    validate_instance(request, "lesson-generation-request")
    return request
