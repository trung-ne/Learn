"""Fail-closed preflight and post-generation validation for M6."""

from __future__ import annotations

from collections import defaultdict
from typing import Any, Iterable, Mapping

from english_master.schema_validation import validation_issues

from .canonical import authorization_id, request_id
from .models import GenerationIssue, JsonObject

LEVELS = ("A1.1", "A1.2", "A2.1", "A2.2", "B1.1", "B1.2", "B2.1", "B2.2", "C1.1", "C1.2", "C2.1", "C2.2")
FAMILIES = ("grammar", "vocabulary", "functions", "pronunciation")
TYPE_BY_FAMILY = {
    "grammar": "GRAMMAR", "vocabulary": "VOCABULARY_SENSE",
    "functions": "COMMUNICATIVE_FUNCTION", "pronunciation": "PRONUNCIATION",
}


def _issue(code: str, path: str, message: str) -> GenerationIssue:
    return GenerationIssue(code, path, message)


def _schema_issues(value: JsonObject, schema: str, code: str) -> list[GenerationIssue]:
    return [_issue(code, item.instance_path, item.message) for item in validation_issues(value, schema)]


def _duplicates(values: Iterable[str]) -> set[str]:
    seen: set[str] = set()
    return {value for value in values if value in seen or seen.add(value) is not None}


def _cycle_nodes(edges: list[dict[str, Any]]) -> set[str]:
    adjacency: dict[str, list[str]] = defaultdict(list)
    nodes: set[str] = set()
    for edge in edges:
        source, target = edge.get("from"), edge.get("to")
        if isinstance(source, str) and isinstance(target, str):
            adjacency[source].append(target); nodes.update((source, target))
    visiting: set[str] = set(); visited: set[str] = set(); cyclic: set[str] = set()
    def visit(node: str) -> None:
        if node in visiting:
            cyclic.add(node); return
        if node in visited: return
        visiting.add(node)
        for child in adjacency[node]:
            if child in visiting: cyclic.update((node, child))
            visit(child)
        visiting.remove(node); visited.add(node)
    for node in sorted(nodes): visit(node)
    return cyclic


def preflight_issues(request: JsonObject) -> tuple[GenerationIssue, ...]:
    """Return every deterministic request violation before any backend call."""

    issues = _schema_issues(request, "lesson-generation-request", "REQUEST_SCHEMA")
    if issues:
        return tuple(sorted(issues))

    auth = request["authorization"]
    if request["request_id"] != request_id(request):
        issues.append(_issue("REQUEST_ID_MISMATCH", "$.request_id", "request_id is not the canonical request identity"))
    if auth["authorization_id"] != authorization_id(auth):
        issues.append(_issue("AUTHORIZATION_ID_MISMATCH", "$.authorization.authorization_id", "authorization_id is not the canonical snapshot identity"))

    spec, graph, previous, constraints, generation = (request[key] for key in ("lesson_spec", "graph", "previous_knowledge", "constraints", "generation"))
    if generation["curriculum_version"] != auth["curriculum_version"]:
        issues.append(_issue("VERSION_MISMATCH", "$.generation.curriculum_version", "curriculum version differs from authorization"))
    if generation["taxonomy_version"] != auth["taxonomy_version"]:
        issues.append(_issue("VERSION_MISMATCH", "$.generation.taxonomy_version", "taxonomy version differs from authorization"))
    if constraints["target_cefr"] != spec["cefr"]:
        issues.append(_issue("CEFR_MISMATCH", "$.constraints.target_cefr", "target CEFR differs from lesson specification"))
    if spec["id"] not in graph["lesson_order"]:
        issues.append(_issue("LESSON_NOT_IN_GRAPH", "$.graph.lesson_order", "target lesson is absent from lesson order"))

    order = {lesson_id: index for index, lesson_id in enumerate(graph["lesson_order"])}
    target_position = order.get(spec["id"], -1)
    expected_edges = {(item["from"], item["to"]) for item in graph["prerequisite_edges"]}
    for prerequisite in spec["prerequisites"]:
        if prerequisite not in previous["completed_lessons"]:
            issues.append(_issue("PREREQUISITE_NOT_COMPLETED", "$.previous_knowledge.completed_lessons", f"prerequisite {prerequisite!r} is not completed"))
        if prerequisite not in order or order[prerequisite] >= target_position:
            issues.append(_issue("PREREQUISITE_NOT_EARLIER", "$.lesson_spec.prerequisites", f"prerequisite {prerequisite!r} is not earlier"))
        if (prerequisite, spec["id"]) not in expected_edges:
            issues.append(_issue("PREREQUISITE_EDGE_MISSING", "$.graph.prerequisite_edges", f"edge {prerequisite!r} -> {spec['id']!r} is missing"))
    graph_prereqs = sorted(source for source, target in expected_edges if target == spec["id"])
    if graph_prereqs != sorted(spec["prerequisites"]):
        issues.append(_issue("PREREQUISITE_SET_MISMATCH", "$.graph.prerequisite_edges", "graph prerequisites differ from lesson specification"))
    cyclic = _cycle_nodes(graph["prerequisite_edges"])
    if cyclic:
        issues.append(_issue("GRAPH_CYCLE", "$.graph.prerequisite_edges", f"prerequisite graph is cyclic at {', '.join(sorted(cyclic))}"))

    records: dict[str, dict[str, Any]] = {}
    for index, record in enumerate(auth["records"]):
        record_id = record["id"]
        if record_id in records:
            issues.append(_issue("DUPLICATE_AUTHORIZED_ID", f"$.authorization.records[{index}].id", f"duplicate record {record_id!r}"))
        records[record_id] = record
        if LEVELS.index(record["cefr"]) > LEVELS.index(spec["cefr"]):
            issues.append(_issue("ABOVE_TARGET_CEFR", f"$.authorization.records[{index}].cefr", f"record {record_id!r} is above target tier"))

    forbidden = set(constraints["forbidden_ids"])
    all_allowed: set[str] = set()
    for family in FAMILIES:
        allowed = set(constraints[f"allowed_{family}"])
        introduced = set(spec[f"{family}_introduced"])
        reviewed = set(spec[f"{family}_reviewed"])
        known = set(previous[family])
        all_allowed.update(allowed)
        overlap = allowed & forbidden
        if overlap:
            issues.append(_issue("ALLOWED_FORBIDDEN_OVERLAP", f"$.constraints.allowed_{family}", f"allowed and forbidden overlap: {', '.join(sorted(overlap))}"))
        if allowed != introduced | reviewed:
            issues.append(_issue("ALLOWED_SCOPE_MISMATCH", f"$.constraints.allowed_{family}", f"allowed {family} must exactly equal introduced plus reviewed scope"))
        if introduced & reviewed:
            issues.append(_issue("INTRODUCTION_REVIEW_OVERLAP", f"$.lesson_spec.{family}_introduced", f"{family} cannot be introduced and reviewed together"))
        if not reviewed <= known:
            issues.append(_issue("REVIEW_NOT_PREVIOUSLY_INTRODUCED", f"$.lesson_spec.{family}_reviewed", f"unknown review IDs: {', '.join(sorted(reviewed - known))}"))
        if introduced & known:
            issues.append(_issue("INTRODUCTION_ALREADY_KNOWN", f"$.lesson_spec.{family}_introduced", f"introduced IDs already known: {', '.join(sorted(introduced & known))}"))
        for record_id in sorted(allowed):
            record = records.get(record_id)
            if record is None:
                issues.append(_issue("UNRESOLVED_REFERENCE", f"$.constraints.allowed_{family}", f"record {record_id!r} is not authorized"))
            elif record["record_type"] != TYPE_BY_FAMILY[family]:
                issues.append(_issue("WRONG_REFERENCE_TYPE", f"$.constraints.allowed_{family}", f"record {record_id!r} has type {record['record_type']!r}"))
    if len(spec["vocabulary_introduced"]) > constraints["max_target_vocabulary"]:
        issues.append(_issue("TARGET_VOCABULARY_LIMIT", "$.lesson_spec.vocabulary_introduced", "target vocabulary exceeds configured bound"))
    closure = set(graph["resolved_prerequisite_closure"])
    for record_id in sorted(all_allowed):
        record = records.get(record_id)
        if record:
            missing = set(record["prerequisites"]) - (all_allowed | closure | set().union(*(set(previous[f]) for f in FAMILIES)))
            if missing:
                issues.append(_issue("UNRESOLVED_PREREQUISITE_CLOSURE", "$.graph.resolved_prerequisite_closure", f"{record_id!r} has unresolved prerequisites: {', '.join(sorted(missing))}"))
    return tuple(sorted(set(issues)))


def postgeneration_issues(request: JsonObject, lesson: JsonObject) -> tuple[GenerationIssue, ...]:
    """Return all deterministic violations in a backend candidate."""

    issues = _schema_issues(lesson, "lesson", "LESSON_SCHEMA")
    spec, constraints = request["lesson_spec"], request["constraints"]
    exact = {"id": "id", "title": "title", "unit_id": "unit_id", "lesson_number": "lesson_number", "cefr_level": "cefr", "duration_minutes": "duration_minutes", "objectives": "objectives", "prerequisites": "prerequisites"}
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
        if isinstance(actual, list): referenced.update(value for value in actual if isinstance(value, str))
    expected_functions = sorted(spec["functions_introduced"] + spec["functions_reviewed"])
    if lesson.get("communicative_functions") != expected_functions:
        issues.append(_issue("REFERENCE_SCOPE_MISMATCH", "$.communicative_functions", "must equal introduced and reviewed function scope"))
    if lesson.get("exercises") != []:
        issues.append(_issue("M7_LEAKAGE", "$.exercises", "M6 lessons must contain an empty exercises array"))
    forbidden_keys = {"answer_key", "assessment", "assessments", "ai_prompt", "ai_practice_prompt", "media"}
    def scan(value: Any, path: str = "$") -> None:
        if isinstance(value, dict):
            for key, child in value.items():
                if key.casefold() in forbidden_keys:
                    issues.append(_issue("LATER_MILESTONE_LEAKAGE", f"{path}.{key}", f"field {key!r} is excluded from M6"))
                scan(child, f"{path}.{key}")
        elif isinstance(value, list):
            for index, child in enumerate(value): scan(child, f"{path}[{index}]")
    scan(lesson)
    sections = lesson.get("content_sections", [])
    if isinstance(sections, list):
        if len(sections) > constraints["max_sections"]:
            issues.append(_issue("SECTION_LIMIT", "$.content_sections", "section count exceeds configured bound"))
        total = 0
        section_ids: list[str] = []
        for index, section in enumerate(sections):
            if not isinstance(section, dict): continue
            body = section.get("body_text", "")
            if isinstance(body, str):
                total += len(body)
                if not body.strip(): issues.append(_issue("EMPTY_SECTION", f"$.content_sections[{index}].body_text", "section body must be nonempty"))
                if len(body) > constraints["max_section_characters"]: issues.append(_issue("SECTION_SIZE_LIMIT", f"$.content_sections[{index}].body_text", "section body exceeds configured bound"))
                folded = body.casefold()
                for term in constraints["forbidden_terms"]:
                    if term.casefold() in folded: issues.append(_issue("FORBIDDEN_TERM", f"$.content_sections[{index}].body_text", f"contains forbidden term {term!r}"))
            embedded = section.get("embedded_examples", [])
            if isinstance(embedded, list):
                unknown = set(value for value in embedded if isinstance(value, str)) - set().union(*(set(constraints[f"allowed_{f}"]) for f in FAMILIES))
                if unknown: issues.append(_issue("UNDECLARED_EMBEDDED_REFERENCE", f"$.content_sections[{index}].embedded_examples", f"undeclared IDs: {', '.join(sorted(unknown))}"))
            if isinstance(section.get("id"), str): section_ids.append(section["id"])
        if total > constraints["max_total_characters"]: issues.append(_issue("TOTAL_SIZE_LIMIT", "$.content_sections", "total section text exceeds configured bound"))
        if section_ids != sorted(section_ids): issues.append(_issue("NONCANONICAL_ORDER", "$.content_sections", "sections must be ordered by ID"))
    if referenced & set(constraints["forbidden_ids"]):
        issues.append(_issue("FORBIDDEN_REFERENCE", "$", f"forbidden references used: {', '.join(sorted(referenced & set(constraints['forbidden_ids'])))}"))
    metadata = lesson.get("generation_metadata")
    generation = request["generation"]
    if isinstance(metadata, dict):
        expected = {"generator": generation["generator"], "generator_version": generation["generator_version"], "model": generation["model"], "prompt_version": generation["prompt_version"], "curriculum_version": generation["curriculum_version"], "qa_status": "UNREVIEWED"}
        for key, value in expected.items():
            if metadata.get(key) != value: issues.append(_issue("GENERATION_METADATA_MISMATCH", f"$.generation_metadata.{key}", f"must equal {value!r}"))
    else:
        issues.append(_issue("GENERATION_METADATA_MISSING", "$.generation_metadata", "generation metadata is required"))
    return tuple(sorted(set(issues)))
