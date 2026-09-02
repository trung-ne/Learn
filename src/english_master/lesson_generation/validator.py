"""Fail-closed authority, graph, provenance, and lesson validation for M6."""

from __future__ import annotations

import hashlib
import re
from collections import defaultdict
from typing import Any, Iterable, Mapping

from english_master.curriculum_validation.validator import validate_bundle
from english_master.schema_validation import validation_issues

from .authority import LessonGenerationAuthority
from .canonical import authorization_id, sha256_json, request_id
from .models import GenerationIssue, JsonObject

LEVELS = ("A1.1", "A1.2", "A2.1", "A2.2", "B1.1", "B1.2", "B2.1", "B2.2", "C1.1", "C1.2", "C2.1", "C2.2")
FAMILIES = ("grammar", "vocabulary", "functions", "pronunciation")
TYPE_BY_FAMILY = {
    "grammar": "GRAMMAR",
    "vocabulary": "VOCABULARY_SENSE",
    "functions": "COMMUNICATIVE_FUNCTION",
    "pronunciation": "PRONUNCIATION",
}
TAXONOMY_TYPE_BY_FAMILY = {
    "grammar": "grammar",
    "vocabulary": "vocabulary_sense",
    "functions": "communicative_function",
    "pronunciation": "pronunciation",
}
LESSON_ID_RE = re.compile(r"^(A1|A2|B1|B2|C1|C2)-U([0-9]{2})-L([0-9]{2})$")
UNIT_ID_RE = re.compile(r"^(A1|A2|B1|B2|C1|C2)\.([12])-U([0-9]{2})$")


def _issue(code: str, path: str, message: str) -> GenerationIssue:
    return GenerationIssue(code, path, message)


def _schema_issues(value: JsonObject, schema: str, code: str) -> list[GenerationIssue]:
    return [_issue(code, item.instance_path, item.message) for item in validation_issues(value, schema)]


def _canonical_edges(edges: Iterable[tuple[str, str]]) -> list[JsonObject]:
    return [{"from": source, "to": target} for source, target in sorted(set(edges))]


def _cycle_nodes(edges: Iterable[tuple[str, str]]) -> set[str]:
    adjacency: dict[str, list[str]] = defaultdict(list)
    nodes: set[str] = set()
    for source, target in edges:
        adjacency[source].append(target)
        nodes.update((source, target))
    state: dict[str, int] = {}
    stack: list[str] = []
    cyclic: set[str] = set()

    def visit(node: str) -> None:
        marker = state.get(node, 0)
        if marker == 2:
            return
        if marker == 1:
            try:
                cyclic.update(stack[stack.index(node) :])
            except ValueError:
                cyclic.add(node)
            return
        state[node] = 1
        stack.append(node)
        for child in sorted(adjacency[node]):
            visit(child)
        stack.pop()
        state[node] = 2

    for node in sorted(nodes):
        visit(node)
    return cyclic


def _taxonomy_index(authority: LessonGenerationAuthority) -> dict[str, JsonObject]:
    taxonomy = authority.bundle.taxonomy
    records: dict[str, JsonObject] = {}
    for collection in ("concepts", "vocabulary_senses"):
        for record in taxonomy.get(collection, []) if isinstance(taxonomy.get(collection), list) else []:
            if isinstance(record, dict) and isinstance(record.get("id"), str):
                records[record["id"]] = record
    return records


def _record_family(record: Mapping[str, Any]) -> str | None:
    record_type = record.get("type")
    if record_type == "grammar":
        return "grammar"
    if record_type == "communicative_function":
        return "functions"
    if record_type == "pronunciation":
        return "pronunciation"
    if "word" in record and "sense_number" in record:
        return "vocabulary"
    return None


def _authorized_record_index(authorization: Mapping[str, Any]) -> dict[str, JsonObject]:
    records: dict[str, JsonObject] = {}
    values = authorization.get("records", [])
    if not isinstance(values, list):
        return records
    for record in values:
        if isinstance(record, dict) and isinstance(record.get("id"), str):
            records[record["id"]] = record
    return records


def _taxonomy_closure(target_ids: set[str], taxonomy: Mapping[str, JsonObject]) -> tuple[set[str], set[str]]:
    closure: set[str] = set()
    unresolved: set[str] = set()
    visiting: set[str] = set()

    def visit(record_id: str) -> None:
        if record_id in visiting:
            unresolved.add(record_id)
            return
        record = taxonomy.get(record_id)
        if record is None:
            unresolved.add(record_id)
            return
        visiting.add(record_id)
        prerequisites = record.get("prerequisites", [])
        if not isinstance(prerequisites, list):
            unresolved.add(record_id)
        else:
            for prerequisite in prerequisites:
                if not isinstance(prerequisite, str):
                    continue
                if prerequisite not in target_ids:
                    closure.add(prerequisite)
                visit(prerequisite)
        visiting.remove(record_id)

    for target_id in sorted(target_ids):
        visit(target_id)
    return closure, unresolved


def _derived_context(authority: LessonGenerationAuthority, lesson_id: str) -> JsonObject:
    structure = authority.bundle.structure
    graph = authority.bundle.graph
    lessons = {
        item["id"]: item
        for item in structure.get("lessons", [])
        if isinstance(item, dict) and isinstance(item.get("id"), str)
    }
    lesson = lessons.get(lesson_id)
    nodes = {
        item["id"]: item
        for item in graph.get("nodes", [])
        if isinstance(item, dict) and isinstance(item.get("id"), str)
    }
    lesson_order = [
        node_id
        for node_id, _ in sorted(
            ((node_id, node.get("sequence_key", "")) for node_id, node in nodes.items() if node.get("type") == "lesson"),
            key=lambda item: (item[1], item[0]),
        )
    ]
    edges = [edge for edge in graph.get("edges", []) if isinstance(edge, dict)]
    prerequisite_pairs = {
        (edge.get("from"), edge.get("to"))
        for edge in edges
        if edge.get("type") == "lesson_prerequisite"
        and isinstance(edge.get("from"), str)
        and isinstance(edge.get("to"), str)
    }
    introduction_pairs = {
        (edge.get("from"), edge.get("to"))
        for edge in edges
        if edge.get("type") == "introduction"
        and edge.get("from") == lesson_id
        and isinstance(edge.get("to"), str)
    }
    taxonomy = _taxonomy_index(authority)
    review_pairs = {
        (edge.get("from"), edge.get("to"))
        for edge in edges
        if edge.get("type") == "review"
        and edge.get("to") == lesson_id
        and isinstance(edge.get("from"), str)
        and nodes.get(edge.get("from"), {}).get("type") == "lesson"
    }
    direct_prerequisites = {source for source, target in prerequisite_pairs if target == lesson_id}
    transitive_lessons: set[str] = set()

    def add_lesson_predecessors(target: str) -> None:
        for source, edge_target in sorted(prerequisite_pairs):
            if edge_target == target and source not in transitive_lessons:
                transitive_lessons.add(source)
                add_lesson_predecessors(source)

    add_lesson_predecessors(lesson_id)
    outline_references: set[str] = set()
    supporting_references: set[str] = set()
    family_refs: dict[str, set[str]] = {family: set() for family in FAMILIES}
    if lesson is not None:
        for family, field in (("grammar", "grammar"), ("vocabulary", "vocabulary"), ("functions", "functions"), ("pronunciation", "pronunciation")):
            values = lesson.get(field, [])
            if isinstance(values, list):
                family_refs[family] = {value for value in values if isinstance(value, str)}
                outline_references.update(family_refs[family])
        taxonomy_concepts = lesson.get("taxonomy_concepts", [])
        if isinstance(taxonomy_concepts, list):
            supporting_references = {value for value in taxonomy_concepts if isinstance(value, str)}
            outline_references.update(supporting_references)
    introduction_targets = {target for _, target in introduction_pairs}
    introduced = {family: sorted(values & introduction_targets) for family, values in family_refs.items()}
    reviewed = {family: sorted(values - introduction_targets) for family, values in family_refs.items()}
    target_closure, unresolved = _taxonomy_closure(outline_references, taxonomy)

    previous: dict[str, Any] = {"completed_lessons": sorted(transitive_lessons)}
    target_position = lesson_order.index(lesson_id) if lesson_id in lesson_order else -1
    earlier_lessons = set(lesson_order[:target_position]) if target_position >= 0 else set()
    for family in FAMILIES:
        known: set[str] = set()
        for edge in edges:
            if (
                edge.get("type") == "introduction"
                and edge.get("from") in earlier_lessons
                and isinstance(edge.get("to"), str)
                and _record_family(taxonomy.get(edge["to"], {})) == family
            ):
                known.add(edge["to"])
        previous[family] = sorted(known)

    return {
        "lesson": lesson,
        "lesson_order": lesson_order,
        "prerequisite_pairs": prerequisite_pairs,
        "introduction_pairs": introduction_pairs,
        "review_pairs": review_pairs,
        "direct_prerequisites": sorted(direct_prerequisites),
        "previous": previous,
        "introduced": introduced,
        "reviewed": reviewed,
        "supporting": sorted(supporting_references),
        "closure": sorted(target_closure),
        "unresolved_closure": sorted(unresolved),
        "taxonomy": taxonomy,
    }


def _registry_issues(record: JsonObject, registry: Mapping[str, Any], path: str) -> list[GenerationIssue]:
    if record.get("content_origin") != "EXTERNAL_APPROVED":
        return []
    provenance = record.get("provenance")
    if not isinstance(provenance, dict):
        return [_issue("PROVENANCE_MISSING", f"{path}.provenance", "external record requires complete provenance")]
    source_id = provenance.get("source_id")
    sources = registry.get("sources", [])
    source = next((item for item in sources if isinstance(item, dict) and item.get("source_id") == source_id), None) if isinstance(sources, list) else None
    if source is None:
        return [_issue("SOURCE_NOT_REGISTERED", f"{path}.provenance.source_id", f"source {source_id!r} is not registered")]
    issues: list[GenerationIssue] = []
    if source.get("status") != "APPROVED":
        issues.append(_issue("SOURCE_NOT_APPROVED", f"{path}.provenance.source_id", f"source {source_id!r} is not APPROVED"))
    content_type = record.get("source_content_type")
    permissions = source.get("permissions", {})
    media = source.get("media_permissions", {}).get(content_type, {}) if isinstance(source.get("media_permissions"), dict) else {}
    required_permissions = (
        (permissions, "reference_allowed"),
        (permissions, "modify_allowed"),
        (permissions, "redistribute_allowed"),
        (media, "transform_allowed"),
        (media, "derived_redistribution_allowed"),
    )
    if any(not isinstance(container, dict) or container.get(key) is not True for container, key in required_permissions):
        issues.append(_issue("SOURCE_PERMISSION_DENIED", path, f"source {source_id!r} does not authorize derived lesson generation and redistribution"))
    expected = {
        "source_name": source.get("source_name"),
        "source_url": source.get("source_url"),
        "license": source.get("license", {}).get("name") if isinstance(source.get("license"), dict) else None,
        "license_url": source.get("license", {}).get("url") if isinstance(source.get("license"), dict) else None,
    }
    for key, expected_value in expected.items():
        if provenance.get(key) != expected_value:
            issues.append(_issue("PROVENANCE_REGISTRY_MISMATCH", f"{path}.provenance.{key}", f"must match registered {key}"))
    source_content = record.get("source_content")
    if isinstance(source_content, str):
        actual_hash = hashlib.sha256(source_content.encode("utf-8")).hexdigest()
        if str(provenance.get("content_hash", "")).casefold() != actual_hash:
            issues.append(_issue("PROVENANCE_CONTENT_HASH_MISMATCH", f"{path}.provenance.content_hash", "must be the SHA-256 of the authorized source_content UTF-8 bytes"))
    attribution = provenance.get("attribution")
    attribution_policy = source.get("attribution", {})
    if isinstance(attribution_policy, dict) and attribution_policy.get("required") is True and isinstance(attribution, str):
        required_fragments = (
            provenance.get("source_record_id"),
            provenance.get("license_url"),
        )
        missing = [fragment for fragment in required_fragments if isinstance(fragment, str) and fragment not in attribution]
        if missing:
            issues.append(_issue("ATTRIBUTION_INCOMPLETE", f"{path}.provenance.attribution", "required record ID and license URL must appear in attribution"))
    return issues


def preflight_issues(request: JsonObject, authority: LessonGenerationAuthority) -> tuple[GenerationIssue, ...]:
    """Return all deterministic violations before any backend call."""

    issues = _schema_issues(request, "lesson-generation-request", "REQUEST_SCHEMA")
    authorization = authority.authorization_dict()
    issues.extend(_schema_issues(authorization, "lesson-generation-authorization", "AUTHORIZATION_SCHEMA"))
    if issues:
        issues.append(_issue("M5_CONTENT_GENERATION_BLOCKED", "$.authority", "verified M5 approval gate is not satisfied"))
        return tuple(sorted(set(issues)))

    if request["request_id"] != request_id(request):
        issues.append(_issue("REQUEST_ID_MISMATCH", "$.request_id", "request_id is not the canonical request identity"))
    if authorization["authorization_id"] != authorization_id(authorization):
        issues.append(_issue("AUTHORIZATION_ID_MISMATCH", "$.authorization_id", "authorization_id is not the canonical independent authorization identity"))
    if request["authorization_id"] != authorization["authorization_id"]:
        issues.append(_issue("AUTHORIZATION_BINDING_MISMATCH", "$.authorization_id", "request does not name the independently loaded authorization"))

    artifact_hashes = authority.artifact_hashes()
    if request["artifact_hashes"] != artifact_hashes or authorization["artifact_hashes"] != artifact_hashes:
        issues.append(_issue("ARTIFACT_HASH_MISMATCH", "$.artifact_hashes", "request and authorization must match the loaded M5 and registry artifacts"))

    spec, graph, previous, constraints, generation = (request[key] for key in ("lesson_spec", "graph", "previous_knowledge", "constraints", "generation"))
    if generation["curriculum_version"] != authority.bundle.structure.get("curriculum_version") or generation["curriculum_version"] != authorization["curriculum_version"]:
        issues.append(_issue("VERSION_MISMATCH", "$.generation.curriculum_version", "curriculum version differs from verified authority"))
    taxonomy_version = authority.bundle.taxonomy.get("taxonomy_version")
    if generation["taxonomy_version"] != taxonomy_version or generation["taxonomy_version"] != authorization["taxonomy_version"]:
        issues.append(_issue("VERSION_MISMATCH", "$.generation.taxonomy_version", "taxonomy version differs from verified authority"))
    if spec["id"] not in authorization["approved_lesson_ids"]:
        issues.append(_issue("LESSON_NOT_AUTHORIZED", "$.lesson_spec.id", "lesson is absent from independent M6 approval"))

    derived = _derived_context(authority, spec["id"])
    target_ids = set().union(*(set(derived["introduced"][family]) | set(derived["reviewed"][family]) for family in FAMILIES))
    required_taxonomy_ids = target_ids | set(derived["supporting"]) | set(derived["closure"])
    approved_ids = set(_authorized_record_index(authorization))
    curriculum_result = validate_bundle(
        authority.bundle,
        require_approved_taxonomy=True,
        externally_approved_taxonomy_ids=approved_ids,
        required_taxonomy_ids=required_taxonomy_ids,
    )
    for item in curriculum_result.issues:
        issues.append(_issue("M5_BUNDLE_INVALID", item.path, f"{item.code}: {item.message}"))

    gate_lifted = (
        authorization.get("review_outcome") == "APPROVED_FOR_M6_GENERATION"
        and request["authorization_id"] == authorization.get("authorization_id")
        and request["artifact_hashes"] == artifact_hashes
        and authorization.get("artifact_hashes") == artifact_hashes
        and spec["id"] in authorization.get("approved_lesson_ids", [])
        and not any(issue.code in {"AUTHORIZATION_SCHEMA", "AUTHORIZATION_ID_MISMATCH", "AUTHORIZATION_BINDING_MISMATCH", "ARTIFACT_HASH_MISMATCH", "LESSON_NOT_AUTHORIZED", "M5_BUNDLE_INVALID"} for issue in issues)
    )
    if not gate_lifted:
        issues.append(_issue("M5_CONTENT_GENERATION_BLOCKED", "$.authority", "verified M5 approval gate is not satisfied"))

    outline = derived["lesson"]
    if not isinstance(outline, dict):
        issues.append(_issue("LESSON_NOT_IN_M5", "$.lesson_spec.id", "lesson is absent from the authoritative M5 structure"))
    else:
        for request_field, outline_field in (("id", "id"), ("title", "title"), ("unit_id", "unit_id"), ("lesson_number", "lesson_number"), ("cefr", "cefr"), ("objectives", "objectives")):
            if spec[request_field] != outline.get(outline_field):
                issues.append(_issue("M5_LESSON_MISMATCH", f"$.lesson_spec.{request_field}", f"must match authoritative M5 {outline_field}"))

    lesson_match = LESSON_ID_RE.fullmatch(spec["id"])
    unit_match = UNIT_ID_RE.fullmatch(spec["unit_id"])
    if not lesson_match or not unit_match or lesson_match.group(1) != spec["cefr"][:2] or unit_match.group(1) != spec["cefr"][:2] or unit_match.group(2) != spec["cefr"][-1] or lesson_match.group(2) != unit_match.group(3) or int(lesson_match.group(3)) != spec["lesson_number"]:
        issues.append(_issue("IDENTITY_CONTRACT_MISMATCH", "$.lesson_spec", "lesson ID, unit ID, lesson number, and CEFR tier are inconsistent"))

    expected_graph = {
        "lesson_order": derived["lesson_order"],
        "prerequisite_edges": _canonical_edges(derived["prerequisite_pairs"]),
        "introduction_edges": _canonical_edges(derived["introduction_pairs"]),
        "review_edges": _canonical_edges(derived["review_pairs"]),
        "resolved_prerequisite_closure": derived["closure"],
    }
    for key, expected in expected_graph.items():
        if graph[key] != expected:
            issues.append(_issue("AUTHORITATIVE_GRAPH_MISMATCH", f"$.graph.{key}", "declaration must equal the context derived from the verified M5 graph"))
    if derived["unresolved_closure"]:
        issues.append(_issue("UNRESOLVED_PREREQUISITE_CLOSURE", "$.graph.resolved_prerequisite_closure", f"unresolved taxonomy records: {', '.join(derived['unresolved_closure'])}"))
    cyclic = _cycle_nodes(derived["prerequisite_pairs"])
    if cyclic:
        issues.append(_issue("GRAPH_CYCLE", "$.graph.prerequisite_edges", f"authoritative prerequisite graph is cyclic at {', '.join(sorted(cyclic))}"))
    if previous != derived["previous"]:
        issues.append(_issue("PREVIOUS_KNOWLEDGE_MISMATCH", "$.previous_knowledge", "previous knowledge must be derived from authoritative introduction and prerequisite edges"))
    if spec["prerequisites"] != derived["direct_prerequisites"]:
        issues.append(_issue("PREREQUISITE_SET_MISMATCH", "$.lesson_spec.prerequisites", "lesson prerequisites must equal authoritative direct prerequisites"))

    records = _authorized_record_index(authorization)
    if len(records) != len(authorization["records"]):
        issues.append(_issue("DUPLICATE_AUTHORIZED_ID", "$.authorization.records", "authorization record IDs must be unique"))
    taxonomy = derived["taxonomy"]
    for record_id in sorted(required_taxonomy_ids):
        authorized = records.get(record_id)
        source = taxonomy.get(record_id)
        if authorized is None:
            issues.append(_issue("UNRESOLVED_REFERENCE", "$.authorization.records", f"required record {record_id!r} is not independently authorized"))
            continue
        if source is None:
            issues.append(_issue("UNRESOLVED_REFERENCE", "$.taxonomy", f"required record {record_id!r} is absent from the pinned taxonomy"))
            continue
        family = _record_family(source)
        expected_type = TYPE_BY_FAMILY.get(family or "", "SUPPORTING_CONCEPT")
        expected_definition = source.get("description", source.get("definition"))
        expected_cefr = source.get("minimum_cefr", source.get("cefr_level"))
        expected_prerequisites = sorted(source.get("prerequisites", [])) if isinstance(source.get("prerequisites"), list) else []
        expected_values = {
            "record_type": expected_type,
            "definition": expected_definition,
            "cefr": expected_cefr,
            "prerequisites": expected_prerequisites,
            "taxonomy_record_hash": sha256_json(source),
        }
        for key, expected in expected_values.items():
            actual = sorted(authorized[key]) if key == "prerequisites" else authorized[key]
            if actual != expected:
                issues.append(_issue("AUTHORIZED_RECORD_MISMATCH", f"$.authorization.records[{record_id}].{key}", "authorized record must match the pinned taxonomy record"))
        issues.extend(_registry_issues(authorized, authority.source_registry, f"$.authorization.records[{record_id}]"))
        if expected_cefr in LEVELS and LEVELS.index(expected_cefr) > LEVELS.index(spec["cefr"]):
            issues.append(_issue("ABOVE_TARGET_CEFR", f"$.authorization.records[{record_id}].cefr", f"record {record_id!r} is above target tier"))
    surplus = set(records) - required_taxonomy_ids
    if surplus:
        issues.append(_issue("SURPLUS_AUTHORIZED_RECORD", "$.authorization.records", f"authorization contains unused records: {', '.join(sorted(surplus))}"))

    if constraints["target_cefr"] != spec["cefr"]:
        issues.append(_issue("CEFR_MISMATCH", "$.constraints.target_cefr", "target CEFR differs from lesson specification"))
    forbidden = set(constraints["forbidden_ids"])
    for family in FAMILIES:
        expected_introduced = derived["introduced"][family]
        expected_reviewed = derived["reviewed"][family]
        if spec[f"{family}_introduced"] != expected_introduced or spec[f"{family}_reviewed"] != expected_reviewed:
            issues.append(_issue("M5_REFERENCE_SCOPE_MISMATCH", f"$.lesson_spec.{family}_introduced", f"{family} introduction/review scope must be derived from M5"))
        allowed = set(constraints[f"allowed_{family}"])
        expected_allowed = set(expected_introduced) | set(expected_reviewed)
        if allowed != expected_allowed:
            issues.append(_issue("ALLOWED_SCOPE_MISMATCH", f"$.constraints.allowed_{family}", f"allowed {family} must exactly equal authoritative introduced plus reviewed scope"))
        overlap = allowed & forbidden
        if overlap:
            issues.append(_issue("ALLOWED_FORBIDDEN_OVERLAP", f"$.constraints.allowed_{family}", f"allowed and forbidden overlap: {', '.join(sorted(overlap))}"))
        for record_id in sorted(allowed):
            record = records.get(record_id)
            if record is not None and record["record_type"] != TYPE_BY_FAMILY[family]:
                issues.append(_issue("WRONG_REFERENCE_TYPE", f"$.constraints.allowed_{family}", f"record {record_id!r} has type {record['record_type']!r}"))
    if len(spec["vocabulary_introduced"]) > constraints["max_target_vocabulary"]:
        issues.append(_issue("TARGET_VOCABULARY_LIMIT", "$.lesson_spec.vocabulary_introduced", "target vocabulary exceeds configured bound"))
    gate_failure_codes = {
        "AUTHORIZED_RECORD_MISMATCH", "UNRESOLVED_REFERENCE", "SURPLUS_AUTHORIZED_RECORD",
        "SOURCE_NOT_REGISTERED", "SOURCE_NOT_APPROVED", "SOURCE_PERMISSION_DENIED",
        "PROVENANCE_MISSING", "PROVENANCE_REGISTRY_MISMATCH", "PROVENANCE_CONTENT_HASH_MISMATCH",
        "ATTRIBUTION_INCOMPLETE",
    }
    if any(issue.code in gate_failure_codes for issue in issues) and not any(issue.code == "M5_CONTENT_GENERATION_BLOCKED" for issue in issues):
        issues.append(_issue("M5_CONTENT_GENERATION_BLOCKED", "$.authority", "verified M5 approval gate is not satisfied"))
    return tuple(sorted(set(issues)))


def backend_candidate_issues(candidate: Any) -> tuple[GenerationIssue, ...]:
    """Validate the intentionally narrow, untrusted backend response contract."""

    if not isinstance(candidate, dict):
        return (_issue("BACKEND_RESPONSE_INVALID", "$", "backend response must be a JSON object"),)
    issues: list[GenerationIssue] = []
    keys = set(candidate)
    if keys != {"content_sections"}:
        issues.append(_issue("BACKEND_SCOPE_VIOLATION", "$", "backend may return only content_sections; trusted lesson fields are injected by orchestration"))
    try:
        sha256_json(candidate)
    except (TypeError, ValueError, OverflowError):
        issues.append(_issue("BACKEND_RESPONSE_INVALID", "$", "backend response must be finite canonical JSON"))
    return tuple(sorted(set(issues)))


def postgeneration_issues(request: JsonObject, lesson: JsonObject) -> tuple[GenerationIssue, ...]:
    """Return all deterministic violations in an orchestration-assembled lesson."""

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
        if isinstance(actual, list):
            referenced.update(value for value in actual if isinstance(value, str))
    expected_functions = sorted(spec["functions_introduced"] + spec["functions_reviewed"])
    if lesson.get("communicative_functions") != expected_functions:
        issues.append(_issue("REFERENCE_SCOPE_MISMATCH", "$.communicative_functions", "must equal introduced and reviewed function scope"))
    if lesson.get("exercises") != []:
        issues.append(_issue("M7_LEAKAGE", "$.exercises", "M6 lessons must contain an empty exercises array"))
    forbidden_keys = {"answer_key", "assessment", "assessments", "ai_prompt", "ai_practice_prompt", "media"}

    def scan(value: Any, path: str = "$") -> None:
        if isinstance(value, dict):
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
        allowed_references = set().union(*(set(constraints[f"allowed_{family}"]) for family in FAMILIES))
        for index, section in enumerate(sections):
            if not isinstance(section, dict):
                continue
            title = section.get("title", "")
            body = section.get("body_text", "")
            textual_fields = (("title", title), ("body_text", body))
            section_size = sum(len(text) for _, text in textual_fields if isinstance(text, str))
            total += section_size
            if section_size > constraints["max_section_characters"]:
                issues.append(_issue("SECTION_SIZE_LIMIT", f"$.content_sections[{index}]", "section title and body exceed configured bound"))
            for field, text in textual_fields:
                if not isinstance(text, str):
                    continue
                if not text.strip():
                    issues.append(_issue("EMPTY_SECTION", f"$.content_sections[{index}].{field}", f"section {field} must be nonempty"))
                folded = text.casefold()
                for term in constraints["forbidden_terms"]:
                    if term.casefold() in folded:
                        issues.append(_issue("FORBIDDEN_TERM", f"$.content_sections[{index}].{field}", f"contains forbidden term {term!r}"))
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
    metadata = lesson.get("generation_metadata")
    generation = request["generation"]
    expected_metadata = {
        "generator": generation["generator"],
        "generator_version": generation["generator_version"],
        "model": generation["model"],
        "prompt_version": generation["prompt_version"],
        "generated_at": generation["generated_at"],
        "curriculum_version": generation["curriculum_version"],
        "qa_status": "UNREVIEWED",
        "qa_notes": "Automated M6 structural checks passed; independent review remains required.",
    }
    if metadata != expected_metadata:
        issues.append(_issue("GENERATION_METADATA_MISMATCH", "$.generation_metadata", "metadata must be injected from trusted request fields"))
    return tuple(sorted(set(issues)))
