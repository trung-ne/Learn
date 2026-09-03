"""Fail-closed snapshot authority and assembled-lesson validation for M6."""

from __future__ import annotations

import copy
from typing import Any, Mapping

from english_master.curriculum_validation.validator import validate_bundle
from english_master.schema_validation import validation_issues

from .authority import LessonGenerationAuthority
from .builders import GenerationConfig, build_authorization, build_request
from .canonical import sha256_json
from .derivation import FAMILIES
from .models import GenerationIssue, JsonObject


def _issue(code: str, path: str, message: str) -> GenerationIssue:
    return GenerationIssue(code, path, message)


def _schema_issues(value: JsonObject, schema: str, code: str) -> list[GenerationIssue]:
    return [_issue(code, item.instance_path, item.message) for item in validation_issues(value, schema)]


def _config_from_request(request: Mapping[str, Any]) -> GenerationConfig:
    """Reconstruct bounded caller controls so request derivation can be repeated."""

    spec = request["lesson_spec"]
    constraints = request["constraints"]
    generation = request["generation_config"]
    return GenerationConfig(
        duration_minutes=spec["duration_minutes"],
        forbidden_terms=tuple(constraints["forbidden_terms"]),
        max_target_vocabulary=constraints["max_target_vocabulary"],
        max_sections=constraints["max_sections"],
        max_section_characters=constraints["max_section_characters"],
        max_total_characters=constraints["max_total_characters"],
        generator=generation["generator"],
        generator_version=generation["generator_version"],
        prompt_version=generation["prompt_version"],
        parameters=copy.deepcopy(generation["parameters"]),
        seed=generation["seed"],
    )


def _snapshot_approved_ids(authority: LessonGenerationAuthority) -> set[str]:
    values = authority.snapshot.get("approved_taxonomy_records", [])
    if not isinstance(values, list):
        return set()
    return {
        record["id"]
        for record in values
        if isinstance(record, Mapping) and isinstance(record.get("id"), str)
    }


def preflight_issues(request: JsonObject, authority: LessonGenerationAuthority) -> tuple[GenerationIssue, ...]:
    """Return all deterministic violations before any backend invocation."""

    issues = _schema_issues(request, "lesson-generation-request", "REQUEST_SCHEMA")
    authorization = authority.authorization_dict()
    issues.extend(_schema_issues(authorization, "lesson-generation-authorization", "AUTHORIZATION_SCHEMA"))
    if issues:
        return tuple(sorted(set(issues)))

    try:
        expected_authorization = build_authorization(
            authority.m5, authorization["approved_lesson_ids"]
        )
    except (KeyError, TypeError, ValueError) as error:
        issues.append(_issue("M5_CONTENT_GENERATION_BLOCKED", "$.authority", f"authorization cannot be derived from verified M5 authority: {error}"))
        return tuple(sorted(set(issues)))
    if authorization != expected_authorization:
        issues.append(_issue("AUTHORIZATION_BINDING_MISMATCH", "$.authorization", "authorization must exactly equal the narrow value derived from the verified M5 snapshot"))

    lesson_id = request.get("lesson_spec", {}).get("id") if isinstance(request.get("lesson_spec"), Mapping) else None
    if not isinstance(lesson_id, str):
        return tuple(sorted(set(issues)))
    try:
        expected_request = build_request(
            authority.m5,
            expected_authorization,
            lesson_id,
            config=_config_from_request(request),
        )
    except (KeyError, TypeError, ValueError) as error:
        issues.append(_issue("REQUEST_DERIVATION_MISMATCH", "$.request", f"request cannot be rebuilt from verified M5 authority: {error}"))
        return tuple(sorted(set(issues)))
    if request != expected_request:
        issues.append(_issue("REQUEST_DERIVATION_MISMATCH", "$.request", "request must exactly equal the deterministic snapshot-derived value"))

    snapshot_ids = _snapshot_approved_ids(authority)
    required_ids = {record["id"] for record in authorization["records"]}
    result = validate_bundle(
        authority.bundle,
        require_approved_taxonomy=True,
        externally_approved_taxonomy_ids=snapshot_ids,
        required_taxonomy_ids=required_ids,
    )
    for item in result.issues:
        issues.append(_issue("M5_BUNDLE_INVALID", item.path, f"{item.code}: {item.message}"))
    if result.issues:
        issues.append(_issue("M5_CONTENT_GENERATION_BLOCKED", "$.authority", "verified M5 approval overlay no longer validates against the independently loaded bundle"))
    return tuple(sorted(set(issues)))


def backend_candidate_issues(candidate: Any) -> tuple[GenerationIssue, ...]:
    """Validate the intentionally narrow, untrusted backend response contract."""

    if not isinstance(candidate, dict):
        return (_issue("BACKEND_RESPONSE_INVALID", "$", "backend response must be a JSON object"),)
    issues: list[GenerationIssue] = []
    if set(candidate) != {"content_sections"}:
        issues.append(_issue("BACKEND_SCOPE_VIOLATION", "$", "backend may return only content_sections; orchestration injects all trusted fields"))
    try:
        sha256_json(candidate)
    except (TypeError, ValueError, OverflowError):
        issues.append(_issue("BACKEND_RESPONSE_INVALID", "$", "backend response must be finite canonical JSON"))
    return tuple(sorted(set(issues)))


def postgeneration_issues(
    request: JsonObject,
    lesson: JsonObject,
    *,
    expected_generation_metadata: Mapping[str, Any] | None = None,
) -> tuple[GenerationIssue, ...]:
    """Return deterministic violations in an orchestration-assembled lesson."""

    issues = _schema_issues(lesson, "lesson", "LESSON_SCHEMA")
    spec, constraints = request["lesson_spec"], request["constraints"]
    exact = {
        "id": "id", "title": "title", "unit_id": "unit_id", "lesson_number": "lesson_number",
        "cefr_level": "cefr", "duration_minutes": "duration_minutes", "objectives": "objectives",
        "prerequisites": "prerequisites", "taxonomy_concepts": "taxonomy_concepts", "skills": "skills",
        "dimensions": "dimensions", "review_of": "review_of", "lesson_kind": "lesson_kind",
    }
    for output_field, spec_field in exact.items():
        if lesson.get(output_field) != spec[spec_field]:
            issues.append(_issue("LESSON_SPEC_MISMATCH", f"$.{output_field}", f"must exactly match lesson_spec.{spec_field}"))
    field_map = {
        "grammar_introduced": "grammar_introduced", "grammar_reviewed": "grammar_reviewed",
        "vocabulary_introduced": "vocabulary_introduced", "vocabulary_reviewed": "vocabulary_reviewed",
        "functions_introduced": "functions_introduced", "functions_reviewed": "functions_reviewed",
        "pronunciation_introduced": "pronunciation_introduced", "pronunciation_reviewed": "pronunciation_reviewed",
    }
    referenced: set[str] = set()
    for output_field, spec_field in field_map.items():
        actual = lesson.get(output_field)
        if actual != sorted(spec[spec_field]):
            issues.append(_issue("REFERENCE_SCOPE_MISMATCH", f"$.{output_field}", f"must be the canonical allocated {spec_field} set"))
        if isinstance(actual, list):
            referenced.update(value for value in actual if isinstance(value, str))
    expected_functions = sorted(spec["functions_introduced"] + spec["functions_reviewed"])
    if lesson.get("communicative_functions") != expected_functions:
        issues.append(_issue("REFERENCE_SCOPE_MISMATCH", "$.communicative_functions", "must equal introduced and reviewed function scope"))
    if lesson.get("exercises") != []:
        issues.append(_issue("M7_LEAKAGE", "$.exercises", "M6 lessons must contain an empty exercises array"))

    forbidden_keys = {"answer_key", "assessment", "assessments", "ai_prompt", "ai_practice_prompt", "media"}
    def scan(value: Any, path: str = "$") -> None:
        if isinstance(value, Mapping):
            for key, child in value.items():
                if str(key).casefold() in forbidden_keys:
                    issues.append(_issue("LATER_MILESTONE_LEAKAGE", f"{path}.{key}", f"field {key!r} is excluded from M6"))
                scan(child, f"{path}.{key}")
        elif isinstance(value, list):
            for index, child in enumerate(value):
                scan(child, f"{path}[{index}]")
    scan(lesson)

    sections = lesson.get("content_sections", [])
    if isinstance(sections, list):
        if len(sections) > constraints["max_sections"]:
            issues.append(_issue("SECTION_LIMIT", "$.content_sections", "section count exceeds configured bound"))
        total = 0
        section_ids: list[str] = []
        allowed_references = set().union(*(set(constraints[f"allowed_{family}"]) for family in FAMILIES)) | set(constraints["allowed_supporting"]) | set(constraints["context_only_prerequisites"])
        for index, section in enumerate(sections):
            if not isinstance(section, Mapping):
                continue
            title, body = section.get("title", ""), section.get("body_text", "")
            section_size = sum(len(text) for text in (title, body) if isinstance(text, str))
            total += section_size
            if section_size > constraints["max_section_characters"]:
                issues.append(_issue("SECTION_SIZE_LIMIT", f"$.content_sections[{index}]", "section title and body exceed configured bound"))
            for field, text in (("title", title), ("body_text", body)):
                if not isinstance(text, str) or not text.strip():
                    issues.append(_issue("EMPTY_SECTION", f"$.content_sections[{index}].{field}", f"section {field} must be nonempty"))
                elif any(term.casefold() in text.casefold() for term in constraints["forbidden_terms"]):
                    issues.append(_issue("FORBIDDEN_TERM", f"$.content_sections[{index}].{field}", "contains a forbidden term"))
            embedded = section.get("embedded_examples", [])
            if isinstance(embedded, list):
                unknown = {value for value in embedded if isinstance(value, str)} - allowed_references
                if unknown:
                    issues.append(_issue("UNDECLARED_EMBEDDED_REFERENCE", f"$.content_sections[{index}].embedded_examples", f"undeclared IDs: {', '.join(sorted(unknown))}"))
            if isinstance(section.get("id"), str):
                section_ids.append(section["id"])
        if total > constraints["max_total_characters"]:
            issues.append(_issue("TOTAL_SIZE_LIMIT", "$.content_sections", "total section text exceeds configured bound"))
        if section_ids != sorted(section_ids):
            issues.append(_issue("NONCANONICAL_ORDER", "$.content_sections", "sections must be ordered by ID"))
    if referenced & set(constraints["forbidden_ids"]):
        issues.append(_issue("FORBIDDEN_REFERENCE", "$", f"forbidden references used: {', '.join(sorted(referenced & set(constraints['forbidden_ids'])))}"))
    if expected_generation_metadata is not None and lesson.get("generation_metadata") != dict(expected_generation_metadata):
        issues.append(_issue("GENERATION_METADATA_MISMATCH", "$.generation_metadata", "metadata must be injected from runtime capture and trusted orchestration"))
    return tuple(sorted(set(issues)))
