"""Semantic validation for the M5 curriculum architecture."""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import AbstractSet, Any, Iterable

from english_master.schema_validation import (
    SchemaValidationError,
    load_document,
    validate_instance,
    validate_taxonomy_collection,
)

TIERS = ("A1.1", "A1.2", "A2.1", "A2.2", "B1.1", "B1.2", "B2.1", "B2.2", "C1.1", "C1.2", "C2.1", "C2.2")
LEVELS = ("A1", "A2", "B1", "B2", "C1", "C2")
DIMENSIONS = (
    "listening", "speaking", "spoken_interaction", "reading", "writing", "mediation",
    "grammar", "vocabulary_senses", "collocations", "lexical_chunks", "pronunciation",
    "communicative_functions", "topics", "discourse", "pragmatics", "assessment_capabilities",
)
ORDERING_EDGE_TYPES = frozenset({"lesson_prerequisite", "unit_ordering", "taxonomy_prerequisite"})
REFERENCE_FIELDS = ("grammar", "functions", "pronunciation", "taxonomy_concepts")
TYPE_BY_FIELD = {
    "grammar": "grammar",
    "functions": "communicative_function",
    "pronunciation": "pronunciation",
}


@dataclass(frozen=True, order=True)
class CurriculumIssue:
    """A stable curriculum validation issue."""

    path: str
    code: str
    message: str

    def as_dict(self) -> dict[str, str]:
        return {"code": self.code, "path": self.path, "message": self.message}


@dataclass(frozen=True)
class CurriculumBundle:
    """The four authoritative inputs used by M5 validation."""

    structure: dict[str, Any]
    graph: dict[str, Any]
    coverage: dict[str, Any]
    taxonomy: dict[str, Any]
    paths: tuple[Path, Path, Path, Path]


@dataclass(frozen=True)
class CurriculumValidationResult:
    """Deterministic validation output."""

    issues: tuple[CurriculumIssue, ...]
    topological_order: tuple[str, ...]
    report: dict[str, Any]

    @property
    def valid(self) -> bool:
        return not self.issues


def load_bundle(structure_path: Path, *, graph_path: Path | None = None, coverage_path: Path | None = None, taxonomy_path: Path | None = None) -> CurriculumBundle:
    """Load a curriculum bundle, resolving declared artifacts beside structure."""

    structure_path = structure_path.resolve()
    structure = load_document(structure_path)
    base = structure_path.parent
    artifacts = structure.get("artifacts", {})
    taxonomy_dependency = structure.get("taxonomy_dependency", {})
    resolved_graph = (graph_path or base / str(artifacts.get("graph", "prerequisite_graph.json"))).resolve()
    resolved_coverage = (coverage_path or base / str(artifacts.get("coverage", "coverage-roadmap.json"))).resolve()
    resolved_taxonomy = (taxonomy_path or base / str(taxonomy_dependency.get("path", "taxonomy/taxonomy.json"))).resolve()
    return CurriculumBundle(
        structure=structure,
        graph=load_document(resolved_graph),
        coverage=load_document(resolved_coverage),
        taxonomy=load_document(resolved_taxonomy),
        paths=(structure_path, resolved_graph, resolved_coverage, resolved_taxonomy),
    )


def _schema_issues(instance: dict[str, Any], schema_name: str, path: str) -> list[CurriculumIssue]:
    try:
        if schema_name == "taxonomy":
            validate_taxonomy_collection(instance)
        else:
            validate_instance(instance, schema_name)
    except SchemaValidationError as error:
        return [CurriculumIssue(f"{path}{issue.instance_path[1:]}", "SCHEMA_INVALID", issue.message) for issue in error.issues]
    return []


def _duplicates(records: Any, path: str) -> list[CurriculumIssue]:
    if not isinstance(records, list):
        return []
    first: dict[str, int] = {}
    issues: list[CurriculumIssue] = []
    for index, record in enumerate(records):
        if not isinstance(record, dict) or not isinstance(record.get("id"), str):
            continue
        record_id = record["id"]
        if record_id in first:
            issues.append(CurriculumIssue(f"{path}[{index}].id", "DUPLICATE_ID", f"duplicate ID {record_id!r}; first declared at {path}[{first[record_id]}].id"))
        else:
            first[record_id] = index
    return issues


def _tier_rank(tier: str) -> int:
    try:
        return TIERS.index(tier)
    except ValueError:
        return 10_000


def _record_indexes(structure: dict[str, Any]) -> tuple[dict[str, dict[str, Any]], dict[str, dict[str, Any]], dict[str, dict[str, Any]]]:
    def indexed(name: str) -> dict[str, dict[str, Any]]:
        records = structure.get(name, [])
        return {record["id"]: record for record in records if isinstance(record, dict) and isinstance(record.get("id"), str)} if isinstance(records, list) else {}
    return indexed("units"), indexed("lessons"), indexed("reviews")


def _taxonomy_indexes(taxonomy: dict[str, Any]) -> tuple[dict[str, dict[str, Any]], dict[str, dict[str, Any]]]:
    concepts = taxonomy.get("concepts", [])
    senses = taxonomy.get("vocabulary_senses", [])
    return (
        {record["id"]: record for record in concepts if isinstance(record, dict) and isinstance(record.get("id"), str)} if isinstance(concepts, list) else {},
        {record["id"]: record for record in senses if isinstance(record, dict) and isinstance(record.get("id"), str)} if isinstance(senses, list) else {},
    )


def _curriculum_position(lesson: dict[str, Any], units: dict[str, dict[str, Any]]) -> tuple[int, int]:
    unit = units.get(str(lesson.get("unit_id")), {})
    return (int(unit.get("global_unit_number", 10_000)), int(lesson.get("lesson_number", 10_000)))


def _hierarchy_issues(structure: dict[str, Any]) -> list[CurriculumIssue]:
    issues: list[CurriculumIssue] = []
    levels = structure.get("levels", [])
    units, lessons, reviews = _record_indexes(structure)
    issues.extend(_duplicates(structure.get("units"), "$.units"))
    issues.extend(_duplicates(structure.get("lessons"), "$.lessons"))
    issues.extend(_duplicates(structure.get("reviews"), "$.reviews"))

    actual_levels = [entry.get("level") for entry in levels if isinstance(entry, dict)] if isinstance(levels, list) else []
    if actual_levels != list(LEVELS):
        issues.append(CurriculumIssue("$.levels", "HIERARCHY_LEVELS", f"levels must appear exactly as {list(LEVELS)!r}"))
    actual_tiers: list[str] = []
    declared_unit_parent: dict[str, str] = {}
    if isinstance(levels, list):
        for level_index, level in enumerate(levels):
            if not isinstance(level, dict):
                continue
            expected_tiers = [f"{level.get('level')}.1", f"{level.get('level')}.2"]
            tiers = level.get("tiers", [])
            tier_ids = [tier.get("id") for tier in tiers if isinstance(tier, dict)] if isinstance(tiers, list) else []
            if tier_ids != expected_tiers:
                issues.append(CurriculumIssue(f"$.levels[{level_index}].tiers", "HIERARCHY_TIERS", f"tier IDs must be {expected_tiers!r}"))
            for tier in tiers if isinstance(tiers, list) else []:
                if not isinstance(tier, dict):
                    continue
                tier_id = tier.get("id")
                if isinstance(tier_id, str):
                    actual_tiers.append(tier_id)
                    expected_sequence = _tier_rank(tier_id) + 1
                    if tier.get("sequence") != expected_sequence:
                        issues.append(CurriculumIssue(f"$.levels[{level_index}].tiers", "TIER_SEQUENCE", f"tier {tier_id!r} must have sequence {expected_sequence}"))
                    for unit_id in tier.get("unit_ids", []):
                        if unit_id in declared_unit_parent:
                            issues.append(CurriculumIssue(f"$.levels[{level_index}].tiers", "MULTIPLE_UNIT_PARENTS", f"unit {unit_id!r} belongs to more than one tier"))
                        declared_unit_parent[unit_id] = tier_id
    if actual_tiers != list(TIERS):
        issues.append(CurriculumIssue("$.levels", "TWELVE_TIERS_REQUIRED", f"tiers must appear exactly as {list(TIERS)!r}"))

    ordered_units = structure.get("units", []) if isinstance(structure.get("units"), list) else []
    global_numbers = [unit.get("global_unit_number") for unit in ordered_units if isinstance(unit, dict)]
    if global_numbers != list(range(1, len(global_numbers) + 1)):
        issues.append(CurriculumIssue("$.units", "GLOBAL_UNIT_SEQUENCE", "global_unit_number values must be unique, consecutive, and serialized in ascending order"))

    lesson_parent_count: defaultdict[str, int] = defaultdict(int)
    review_parent_count: defaultdict[str, int] = defaultdict(int)
    previous_unit_id: str | None = None
    for unit_index, unit in enumerate(ordered_units):
        if not isinstance(unit, dict):
            continue
        unit_id = unit.get("id")
        tier = unit.get("tier")
        number = unit.get("global_unit_number")
        expected_id = f"{tier}-U{number:02d}" if isinstance(tier, str) and isinstance(number, int) else None
        if unit_id != expected_id:
            issues.append(CurriculumIssue(f"$.units[{unit_index}].id", "INVALID_UNIT_ID", f"unit ID must be {expected_id!r}"))
        if isinstance(tier, str) and unit.get("level") != tier[:2]:
            issues.append(CurriculumIssue(f"$.units[{unit_index}].level", "LEVEL_TIER_MISMATCH", "unit level must equal the official band of its tier"))
        if declared_unit_parent.get(str(unit_id)) != tier:
            issues.append(CurriculumIssue(f"$.units[{unit_index}].tier", "UNIT_PARENT_MISMATCH", f"unit {unit_id!r} is not declared exactly once under tier {tier!r}"))
        expected_prerequisites = [] if previous_unit_id is None else [previous_unit_id]
        if unit.get("prerequisite_units") != expected_prerequisites:
            issues.append(CurriculumIssue(f"$.units[{unit_index}].prerequisite_units", "UNIT_ORDERING", f"expected prerequisite units {expected_prerequisites!r}"))
        previous_unit_id = unit_id if isinstance(unit_id, str) else previous_unit_id
        lesson_ids = unit.get("lesson_ids", [])
        expected_lesson_ids = [
            lesson["id"]
            for lesson in sorted(
                (candidate for candidate in lessons.values() if candidate.get("unit_id") == unit_id),
                key=lambda candidate: int(candidate.get("lesson_number", 10_000)),
            )
        ]
        if lesson_ids != expected_lesson_ids:
            issues.append(CurriculumIssue(f"$.units[{unit_index}].lesson_ids", "UNIT_LESSON_ORDER", f"lesson_ids must match lesson-number order {expected_lesson_ids!r}"))
        for lesson_id in lesson_ids if isinstance(lesson_ids, list) else []:
            lesson_parent_count[lesson_id] += 1
            lesson = lessons.get(lesson_id)
            if lesson is None:
                issues.append(CurriculumIssue(f"$.units[{unit_index}].lesson_ids", "MISSING_LESSON", f"unknown lesson {lesson_id!r}"))
            elif lesson.get("unit_id") != unit_id:
                issues.append(CurriculumIssue(f"$.units[{unit_index}].lesson_ids", "LESSON_PARENT_MISMATCH", f"lesson {lesson_id!r} declares parent {lesson.get('unit_id')!r}"))
        review_id = unit.get("review_node_id")
        review_parent_count[str(review_id)] += 1
        if review_id not in reviews:
            issues.append(CurriculumIssue(f"$.units[{unit_index}].review_node_id", "MISSING_REVIEW", f"unknown review node {review_id!r}"))

    lesson_records = structure.get("lessons", []) if isinstance(structure.get("lessons"), list) else []
    lesson_positions = [
        _curriculum_position(lesson, units) for lesson in lesson_records if isinstance(lesson, dict)
    ]
    if lesson_positions != sorted(lesson_positions):
        issues.append(CurriculumIssue("$.lessons", "LESSON_SERIALIZATION", "lessons must be serialized by global unit number and lesson number"))
    previous_lesson_id: str | None = None
    for lesson_index, lesson in enumerate(lesson_records):
        if not isinstance(lesson, dict):
            continue
        lesson_id = lesson.get("id")
        unit = units.get(str(lesson.get("unit_id")))
        if unit is None:
            issues.append(CurriculumIssue(f"$.lessons[{lesson_index}].unit_id", "MISSING_UNIT", f"unknown unit {lesson.get('unit_id')!r}"))
            continue
        expected_id = f"{unit['level']}-U{unit['global_unit_number']:02d}-L{lesson.get('lesson_number', 0):02d}"
        if lesson_id != expected_id:
            issues.append(CurriculumIssue(f"$.lessons[{lesson_index}].id", "INVALID_LESSON_ID", f"lesson ID must be {expected_id!r}"))
        if lesson.get("cefr") != unit.get("tier"):
            issues.append(CurriculumIssue(f"$.lessons[{lesson_index}].cefr", "LESSON_TIER_MISMATCH", "lesson tier must match its parent unit"))
        if lesson_parent_count[str(lesson_id)] != 1:
            issues.append(CurriculumIssue(f"$.lessons[{lesson_index}].unit_id", "LESSON_PARENT_COUNT", f"lesson {lesson_id!r} must occur in exactly one unit lesson_ids list"))
        position = _curriculum_position(lesson, units)
        for prereq_index, prereq_id in enumerate(lesson.get("prerequisites", [])):
            prerequisite = lessons.get(prereq_id)
            if prerequisite is None:
                issues.append(CurriculumIssue(f"$.lessons[{lesson_index}].prerequisites[{prereq_index}]", "MISSING_PREREQUISITE", f"unknown lesson prerequisite {prereq_id!r}"))
            elif prereq_id == lesson_id:
                issues.append(CurriculumIssue(f"$.lessons[{lesson_index}].prerequisites[{prereq_index}]", "SELF_DEPENDENCY", "lesson cannot depend on itself"))
            elif _curriculum_position(prerequisite, units) >= position:
                issues.append(CurriculumIssue(f"$.lessons[{lesson_index}].prerequisites[{prereq_index}]", "PREREQUISITE_NOT_EARLIER", f"prerequisite {prereq_id!r} is not earlier than {lesson_id!r}"))
        prerequisites = lesson.get("prerequisites", [])
        if previous_lesson_id is None:
            if prerequisites:
                issues.append(CurriculumIssue(f"$.lessons[{lesson_index}].prerequisites", "CROSS_TIER_PROGRESSION", "the first lesson cannot skip before the curriculum start"))
        elif previous_lesson_id not in prerequisites:
            issues.append(CurriculumIssue(f"$.lessons[{lesson_index}].prerequisites", "CROSS_TIER_PROGRESSION", f"immediate predecessor {previous_lesson_id!r} is required"))
        if isinstance(lesson_id, str):
            previous_lesson_id = lesson_id

    lesson_counts = [len(unit.get("lesson_ids", [])) for unit in ordered_units if isinstance(unit, dict) and isinstance(unit.get("lesson_ids"), list)]
    if lesson_counts and max(lesson_counts) - min(lesson_counts) > 1:
        issues.append(CurriculumIssue("$.units", "UNBALANCED_UNIT_SCOPE", "unit lesson counts may differ by at most one in the architecture roadmap"))

    for review_index, review in enumerate(structure.get("reviews", []) if isinstance(structure.get("reviews"), list) else []):
        if not isinstance(review, dict):
            continue
        review_id = review.get("id")
        unit = units.get(str(review.get("unit_id")))
        if unit is None:
            issues.append(CurriculumIssue(f"$.reviews[{review_index}].unit_id", "MISSING_UNIT", f"unknown unit {review.get('unit_id')!r}"))
            continue
        expected_id = f"{unit['level']}-U{unit['global_unit_number']:02d}-REV"
        if review_id != expected_id:
            issues.append(CurriculumIssue(f"$.reviews[{review_index}].id", "INVALID_REVIEW_ID", f"review ID must be {expected_id!r}"))
        if review.get("cefr") != unit.get("tier"):
            issues.append(CurriculumIssue(f"$.reviews[{review_index}].cefr", "REVIEW_TIER_MISMATCH", "review tier must match its parent unit"))
        if review_parent_count[str(review_id)] != 1:
            issues.append(CurriculumIssue(f"$.reviews[{review_index}].unit_id", "REVIEW_PARENT_COUNT", f"review {review_id!r} must occur in exactly one unit"))
        unit_lesson_ids = unit.get("lesson_ids", [])
        if review.get("review_lessons") != unit_lesson_ids:
            issues.append(CurriculumIssue(f"$.reviews[{review_index}].review_lessons", "REVIEW_SCOPE", "review_lessons must equal the ordered lessons of its unit"))
        if unit_lesson_ids and review.get("sequence_after") != unit_lesson_ids[-1]:
            issues.append(CurriculumIssue(f"$.reviews[{review_index}].sequence_after", "REVIEW_ORDERING", "review must follow the final lesson in its unit"))
    return issues


def _reference_issues(structure: dict[str, Any], taxonomy: dict[str, Any]) -> tuple[list[CurriculumIssue], dict[str, str]]:
    issues: list[CurriculumIssue] = []
    units, lessons, reviews = _record_indexes(structure)
    concepts, senses = _taxonomy_indexes(taxonomy)
    gate = structure.get("taxonomy_dependency", {})
    accepted_statuses = set(gate.get("accepted_record_statuses", [])) if isinstance(gate, dict) else set()
    if any(record.get("status") == "DRAFT" for record in [*concepts.values(), *senses.values()]):
        gate_valid = bool(gate.get("approved_for_outline_planning_only") is True and gate.get("blocks_content_generation") is True and gate.get("gate_decision") == "CONDITIONAL_DRAFT_REFERENCE")
        if not gate_valid:
            issues.append(CurriculumIssue("$.taxonomy_dependency", "DRAFT_REVIEW_GATE", "DRAFT taxonomy references require the explicit outline-only review gate and must block content generation"))
    first_introduction: dict[str, str] = {}
    lesson_records = sorted(lessons.values(), key=lambda lesson: _curriculum_position(lesson, units))
    for lesson in lesson_records:
        lesson_id = str(lesson.get("id"))
        lesson_tier = str(lesson.get("cefr"))
        for field in REFERENCE_FIELDS:
            for index, target_id in enumerate(lesson.get(field, [])):
                record = concepts.get(target_id)
                path = f"$.lessons[{lesson_id}].{field}[{index}]"
                if record is None:
                    issues.append(CurriculumIssue(path, "UNKNOWN_TAXONOMY_REFERENCE", f"unknown taxonomy concept {target_id!r}"))
                    continue
                expected_type = TYPE_BY_FIELD.get(field)
                if expected_type and record.get("type") != expected_type:
                    issues.append(CurriculumIssue(path, "TAXONOMY_TYPE_MISMATCH", f"{target_id!r} has type {record.get('type')!r}, expected {expected_type!r}"))
                if record.get("status") not in accepted_statuses:
                    issues.append(CurriculumIssue(path, "UNAUTHORIZED_DEPENDENCY", f"taxonomy status {record.get('status')!r} is not accepted by the review gate"))
                if _tier_rank(str(record.get("minimum_cefr"))) > _tier_rank(lesson_tier):
                    issues.append(CurriculumIssue(path, "CEFR_REFERENCE_TOO_EARLY", f"{target_id!r} has minimum tier {record.get('minimum_cefr')!r}"))
                first_introduction.setdefault(target_id, lesson_id)
        for index, target_id in enumerate(lesson.get("vocabulary", [])):
            record = senses.get(target_id)
            path = f"$.lessons[{lesson_id}].vocabulary[{index}]"
            if record is None:
                issues.append(CurriculumIssue(path, "UNKNOWN_TAXONOMY_REFERENCE", f"unknown vocabulary sense {target_id!r}"))
                continue
            if record.get("status") not in accepted_statuses:
                issues.append(CurriculumIssue(path, "UNAUTHORIZED_DEPENDENCY", f"taxonomy status {record.get('status')!r} is not accepted by the review gate"))
            if _tier_rank(str(record.get("cefr"))) > _tier_rank(lesson_tier):
                issues.append(CurriculumIssue(path, "CEFR_REFERENCE_TOO_EARLY", f"{target_id!r} has minimum tier {record.get('cefr')!r}"))
            first_introduction.setdefault(target_id, lesson_id)

    for concept_id, lesson_id in first_introduction.items():
        record = concepts.get(concept_id)
        if record is None:
            continue
        current = lessons[lesson_id]
        for prerequisite_id in record.get("prerequisites", []):
            prerequisite_lesson_id = first_introduction.get(prerequisite_id)
            if prerequisite_lesson_id is None:
                issues.append(CurriculumIssue(f"$.taxonomy[{concept_id}].prerequisites", "UNINTRODUCED_TAXONOMY_PREREQUISITE", f"{prerequisite_id!r} is never introduced before dependent concept {concept_id!r}"))
            elif _curriculum_position(lessons[prerequisite_lesson_id], units) >= _curriculum_position(current, units):
                issues.append(CurriculumIssue(f"$.taxonomy[{concept_id}].prerequisites", "TAXONOMY_PREREQUISITE_NOT_EARLIER", f"{prerequisite_id!r} must be introduced before {concept_id!r}"))
    for sense_id, lesson_id in first_introduction.items():
        record = senses.get(sense_id)
        if record is None:
            continue
        current = lessons[lesson_id]
        for prerequisite_id in record.get("prerequisites", []):
            prerequisite_lesson_id = first_introduction.get(prerequisite_id)
            if prerequisite_lesson_id is None or _curriculum_position(lessons[prerequisite_lesson_id], units) >= _curriculum_position(current, units):
                issues.append(CurriculumIssue(f"$.taxonomy[{sense_id}].prerequisites", "VOCABULARY_PREREQUISITE_NOT_EARLIER", f"{prerequisite_id!r} must be introduced before vocabulary sense {sense_id!r}"))

    lesson_position = {lesson_id: _curriculum_position(lesson, units) for lesson_id, lesson in lessons.items()}
    known_review_targets = set(lessons) | set(concepts) | set(senses)
    for lesson_id, lesson in lessons.items():
        current_position = lesson_position[lesson_id]
        for index, target_id in enumerate(lesson.get("review_of", [])):
            path = f"$.lessons[{lesson_id}].review_of[{index}]"
            if target_id not in known_review_targets:
                issues.append(CurriculumIssue(path, "UNRESOLVED_REVIEW", f"unknown lesson review target {target_id!r}"))
            elif target_id in lessons and lesson_position[target_id] >= current_position:
                issues.append(CurriculumIssue(path, "REVIEW_BEFORE_INTRODUCTION", f"lesson {target_id!r} is not earlier than reviewing lesson {lesson_id!r}"))
            elif target_id not in lessons:
                introduced_in = first_introduction.get(target_id)
                if introduced_in is None or lesson_position[introduced_in] >= current_position:
                    issues.append(CurriculumIssue(path, "REVIEW_BEFORE_INTRODUCTION", f"taxonomy target {target_id!r} was not introduced before reviewing lesson {lesson_id!r}"))
    for review_id, review in reviews.items():
        review_unit = units.get(str(review.get("unit_id")), {})
        review_position = (int(review_unit.get("global_unit_number", 10_000)), 100)
        for field, known in (("review_lessons", lessons), ("review_concepts", concepts), ("review_vocabulary", senses)):
            for index, target_id in enumerate(review.get(field, [])):
                path = f"$.reviews[{review_id}].{field}[{index}]"
                if target_id not in known:
                    issues.append(CurriculumIssue(path, "UNRESOLVED_REVIEW", f"unknown review target {target_id!r}"))
                elif field == "review_lessons" and lesson_position[target_id] >= review_position:
                    issues.append(CurriculumIssue(path, "REVIEW_BEFORE_INTRODUCTION", f"lesson {target_id!r} is not earlier than review {review_id!r}"))
                elif field != "review_lessons":
                    introduced_in = first_introduction.get(target_id)
                    if introduced_in is None or lesson_position[introduced_in] >= review_position:
                        issues.append(CurriculumIssue(path, "REVIEW_BEFORE_INTRODUCTION", f"taxonomy target {target_id!r} was not introduced before review {review_id!r}"))
    return issues, first_introduction


def deterministic_topological_order(nodes: Iterable[dict[str, Any]], edges: Iterable[dict[str, Any]]) -> tuple[tuple[str, ...], tuple[str, ...]]:
    """Return stable topological order and nodes participating in a cycle."""

    node_map = {str(node["id"]): node for node in nodes if isinstance(node, dict) and isinstance(node.get("id"), str)}
    outgoing: defaultdict[str, set[str]] = defaultdict(set)
    indegree = {node_id: 0 for node_id in node_map}
    for edge in edges:
        if not isinstance(edge, dict) or edge.get("type") not in ORDERING_EDGE_TYPES:
            continue
        source, target = edge.get("from"), edge.get("to")
        if source in node_map and target in node_map and target not in outgoing[source]:
            outgoing[source].add(target)
            indegree[target] += 1
    key = lambda node_id: (str(node_map[node_id].get("sequence_key", "99")), node_id)
    available = sorted((node_id for node_id, degree in indegree.items() if degree == 0), key=key)
    result: list[str] = []
    while available:
        current = available.pop(0)
        result.append(current)
        for target in sorted(outgoing[current], key=key):
            indegree[target] -= 1
            if indegree[target] == 0:
                available.append(target)
                available.sort(key=key)
    cyclic = tuple(sorted((node_id for node_id, degree in indegree.items() if degree > 0), key=key))
    return tuple(result), cyclic


def _expected_edges(structure: dict[str, Any], taxonomy: dict[str, Any], first_introduction: dict[str, str]) -> set[tuple[str, str, str]]:
    units, lessons, reviews = _record_indexes(structure)
    concepts, senses = _taxonomy_indexes(taxonomy)
    expected: set[tuple[str, str, str]] = set()
    for unit in units.values():
        for prerequisite in unit.get("prerequisite_units", []):
            expected.add((prerequisite, unit["id"], "unit_ordering"))
    for lesson in lessons.values():
        for prerequisite in lesson.get("prerequisites", []):
            expected.add((prerequisite, lesson["id"], "lesson_prerequisite"))
        for target_id in lesson.get("review_of", []):
            expected.add((target_id, lesson["id"], "review"))
    for concept in concepts.values():
        for prerequisite in concept.get("prerequisites", []):
            expected.add((prerequisite, concept["id"], "taxonomy_prerequisite"))
        for relationship in concept.get("related_concepts", []):
            if isinstance(relationship, dict) and isinstance(relationship.get("target_id"), str):
                expected.add((concept["id"], relationship["target_id"], "related_non_ordering"))
    for sense in senses.values():
        for prerequisite in sense.get("prerequisites", []):
            expected.add((prerequisite, sense["id"], "taxonomy_prerequisite"))
    for target_id, lesson_id in first_introduction.items():
        expected.add((lesson_id, target_id, "introduction"))
    for review in reviews.values():
        for target_id in [*review.get("review_lessons", []), *review.get("review_concepts", []), *review.get("review_vocabulary", [])]:
            expected.add((target_id, review["id"], "review"))
    return expected


def _graph_issues(structure: dict[str, Any], graph: dict[str, Any], taxonomy: dict[str, Any], first_introduction: dict[str, str]) -> tuple[list[CurriculumIssue], tuple[str, ...]]:
    issues: list[CurriculumIssue] = []
    units, lessons, reviews = _record_indexes(structure)
    concepts, senses = _taxonomy_indexes(taxonomy)
    nodes = graph.get("nodes", []) if isinstance(graph.get("nodes"), list) else []
    edges = graph.get("edges", []) if isinstance(graph.get("edges"), list) else []
    node_serialization = [
        (str(node.get("sequence_key", "")), str(node.get("id", "")))
        for node in nodes if isinstance(node, dict)
    ]
    if node_serialization != sorted(node_serialization):
        issues.append(CurriculumIssue("$.graph.nodes", "NONDETERMINISTIC_SERIALIZATION", "graph nodes must be serialized by sequence_key and ID"))
    edge_serialization = [
        (str(edge.get("type", "")), str(edge.get("from", "")), str(edge.get("to", "")))
        for edge in edges if isinstance(edge, dict)
    ]
    if edge_serialization != sorted(edge_serialization):
        issues.append(CurriculumIssue("$.graph.edges", "NONDETERMINISTIC_SERIALIZATION", "graph edges must be serialized by type, source, and target"))
    issues.extend(_duplicates(nodes, "$.graph.nodes"))
    node_map = {node["id"]: node for node in nodes if isinstance(node, dict) and isinstance(node.get("id"), str)}
    expected_nodes = set(units) | set(lessons) | set(reviews) | set(concepts) | set(senses)
    actual_nodes = set(node_map)
    for missing in sorted(expected_nodes - actual_nodes):
        issues.append(CurriculumIssue("$.graph.nodes", "MISSING_GRAPH_NODE", f"missing graph node {missing!r}"))
    for extra in sorted(actual_nodes - expected_nodes):
        issues.append(CurriculumIssue("$.graph.nodes", "UNAUTHORIZED_GRAPH_NODE", f"graph node {extra!r} is not an approved curriculum or taxonomy record"))
    expected_types = {**{key: "unit" for key in units}, **{key: "lesson" for key in lessons}, **{key: "review" for key in reviews}, **{key: "taxonomy_concept" for key in concepts}, **{key: "vocabulary_sense" for key in senses}}
    for node_id, node in node_map.items():
        if node_id in expected_types and node.get("type") != expected_types[node_id]:
            issues.append(CurriculumIssue(f"$.graph.nodes[{node_id}].type", "GRAPH_NODE_TYPE", f"node type must be {expected_types[node_id]!r}"))
        if node.get("type") == "lesson" and node.get("parent_id") != lessons.get(node_id, {}).get("unit_id"):
            issues.append(CurriculumIssue(f"$.graph.nodes[{node_id}].parent_id", "GRAPH_PARENT", "lesson graph parent must match structure"))
        if node.get("type") == "review" and node.get("parent_id") != reviews.get(node_id, {}).get("unit_id"):
            issues.append(CurriculumIssue(f"$.graph.nodes[{node_id}].parent_id", "GRAPH_PARENT", "review graph parent must match structure"))
        if node.get("type") == "unit" and node.get("parent_id") != units.get(node_id, {}).get("tier"):
            issues.append(CurriculumIssue(f"$.graph.nodes[{node_id}].parent_id", "GRAPH_PARENT", "unit graph parent must match tier"))

    actual_edges: set[tuple[str, str, str]] = set()
    for index, edge in enumerate(edges):
        if not isinstance(edge, dict):
            continue
        key = (str(edge.get("from")), str(edge.get("to")), str(edge.get("type")))
        if key in actual_edges:
            issues.append(CurriculumIssue(f"$.graph.edges[{index}]", "DUPLICATE_EDGE", f"duplicate graph edge {key!r}"))
        actual_edges.add(key)
        if key[0] not in node_map or key[1] not in node_map:
            issues.append(CurriculumIssue(f"$.graph.edges[{index}]", "MISSING_EDGE_NODE", f"edge references an unknown node: {key!r}"))
        if key[0] == key[1]:
            issues.append(CurriculumIssue(f"$.graph.edges[{index}]", "SELF_DEPENDENCY", "graph edge cannot target its source"))
    expected_edges = _expected_edges(structure, taxonomy, first_introduction)
    for missing in sorted(expected_edges - actual_edges):
        issues.append(CurriculumIssue("$.graph.edges", "MISSING_DERIVED_EDGE", f"missing edge {missing!r}"))
    for extra in sorted(actual_edges - expected_edges):
        issues.append(CurriculumIssue("$.graph.edges", "UNDECLARED_EDGE", f"edge is not supported by the authoritative records: {extra!r}"))

    topological_order, cyclic = deterministic_topological_order(nodes, edges)
    if cyclic:
        issues.append(CurriculumIssue("$.graph.edges", "PREREQUISITE_CYCLE", f"ordering cycle includes: {', '.join(cyclic)}"))
    if graph.get("topological_order") != list(topological_order):
        issues.append(CurriculumIssue("$.graph.topological_order", "NONDETERMINISTIC_TOPOLOGY", "stored topological_order does not match deterministic ordering-edge traversal"))
    return issues, topological_order


def _coverage_issues(structure: dict[str, Any], coverage: dict[str, Any]) -> list[CurriculumIssue]:
    issues: list[CurriculumIssue] = []
    units, lessons, reviews = _record_indexes(structure)
    rows = coverage.get("dimensions", []) if isinstance(coverage.get("dimensions"), list) else []
    names = [row.get("dimension") for row in rows if isinstance(row, dict)]
    if names != list(DIMENSIONS):
        issues.append(CurriculumIssue("$.coverage.dimensions", "COVERAGE_GAP", f"dimensions must appear exactly as {list(DIMENSIONS)!r}"))
    seen: set[str] = set()
    for index, row in enumerate(rows):
        if not isinstance(row, dict):
            continue
        dimension = row.get("dimension")
        dimension_key = str(dimension)
        if dimension_key in seen:
            issues.append(CurriculumIssue(f"$.coverage.dimensions[{index}].dimension", "DUPLICATE_COVERAGE", f"duplicate dimension {dimension!r}"))
        seen.add(dimension_key)
        introduced = row.get("introduced_at")
        introduced_lesson = lessons.get(str(introduced))
        introduced_position: tuple[int, int] | None = None
        if introduced_lesson is None:
            issues.append(CurriculumIssue(f"$.coverage.dimensions[{index}].introduced_at", "UNKNOWN_COVERAGE_NODE", f"unknown lesson {introduced!r}"))
        else:
            introduced_position = _curriculum_position(introduced_lesson, units)
            if dimension_key not in introduced_lesson.get("dimensions", []):
                issues.append(
                    CurriculumIssue(
                        f"$.coverage.dimensions[{index}].introduced_at",
                        "COVERAGE_DIMENSION_MISMATCH",
                        f"introduction lesson {introduced!r} does not declare dimension {dimension!r}",
                    )
                )
        developed = row.get("developed_at", [])
        for target_index, target in enumerate(developed if isinstance(developed, list) else []):
            path = f"$.coverage.dimensions[{index}].developed_at[{target_index}]"
            lesson = lessons.get(str(target))
            if lesson is None:
                issues.append(CurriculumIssue(path, "UNKNOWN_COVERAGE_NODE", f"unknown lesson {target!r}"))
            else:
                if introduced_position is not None and _curriculum_position(lesson, units) <= introduced_position:
                    issues.append(CurriculumIssue(path, "COVERAGE_ORDER", f"development node {target!r} must follow introduction"))
                if dimension_key not in lesson.get("dimensions", []):
                    issues.append(
                        CurriculumIssue(
                            path,
                            "COVERAGE_DIMENSION_MISMATCH",
                            f"development lesson {target!r} does not declare dimension {dimension!r}",
                        )
                    )
        reviewed = row.get("reviewed_at", [])
        for target_index, target in enumerate(reviewed if isinstance(reviewed, list) else []):
            path = f"$.coverage.dimensions[{index}].reviewed_at[{target_index}]"
            review = reviews.get(str(target))
            if review is None:
                issues.append(CurriculumIssue(path, "UNKNOWN_COVERAGE_NODE", f"unknown review {target!r}"))
            else:
                review_unit = units.get(str(review.get("unit_id")), {})
                if introduced_position is not None and (int(review_unit.get("global_unit_number", 10_000)), 100) <= introduced_position:
                    issues.append(CurriculumIssue(path, "COVERAGE_ORDER", f"review node {target!r} must follow introduction"))
                review_lessons = review.get("review_lessons", [])
                declares_dimension = any(
                    dimension_key in lessons[lesson_id].get("dimensions", [])
                    for lesson_id in review_lessons if lesson_id in lessons
                ) if isinstance(review_lessons, list) else False
                if not declares_dimension:
                    issues.append(
                        CurriculumIssue(
                            path,
                            "COVERAGE_DIMENSION_MISMATCH",
                            f"review node {target!r} does not review a lesson declaring dimension {dimension!r}",
                        )
                    )
    return issues


def validate_bundle(
    bundle: CurriculumBundle,
    *,
    require_approved_taxonomy: bool = False,
    externally_approved_taxonomy_ids: AbstractSet[str] = frozenset(),
    required_taxonomy_ids: AbstractSet[str] | None = None,
) -> CurriculumValidationResult:
    """Validate schemas and all M5 cross-record invariants.

    ``externally_approved_taxonomy_ids`` represents an independently reviewed,
    hash-bound approval overlay. ``required_taxonomy_ids`` narrows the strict
    gate to the transitive records used by one downstream generation request.
    Both are explicit so strict callers never need to mutate the committed
    DRAFT taxonomy snapshot.
    """

    issues: list[CurriculumIssue] = []
    if require_approved_taxonomy:
        for collection_name in ("concepts", "vocabulary_senses"):
            records = bundle.taxonomy.get(collection_name, [])
            if isinstance(records, list):
                for index, record in enumerate(records):
                    if (
                        isinstance(record, dict)
                        and (required_taxonomy_ids is None or record.get("id") in required_taxonomy_ids)
                        and record.get("status") != "APPROVED"
                        and record.get("id") not in externally_approved_taxonomy_ids
                    ):
                        issues.append(
                            CurriculumIssue(
                                f"$.taxonomy.{collection_name}[{index}].status",
                                "APPROVED_TAXONOMY_REQUIRED",
                                "strict validation requires APPROVED taxonomy records",
                            )
                        )
    issues.extend(_schema_issues(bundle.structure, "curriculum-manifest", "$.structure"))
    issues.extend(_schema_issues(bundle.graph, "curriculum-graph", "$.graph"))
    issues.extend(_schema_issues(bundle.coverage, "curriculum-coverage-roadmap", "$.coverage"))
    issues.extend(_schema_issues(bundle.taxonomy, "taxonomy", "$.taxonomy"))
    topological_order: tuple[str, ...] = ()
    # Semantic passes are defensive and tolerate partial schema-invalid input.
    issues.extend(_hierarchy_issues(bundle.structure))
    reference_issues, first_introduction = _reference_issues(bundle.structure, bundle.taxonomy)
    issues.extend(reference_issues)
    graph_issues, topological_order = _graph_issues(bundle.structure, bundle.graph, bundle.taxonomy, first_introduction)
    issues.extend(graph_issues)
    issues.extend(_coverage_issues(bundle.structure, bundle.coverage))
    versions = {bundle.structure.get("curriculum_version"), bundle.graph.get("curriculum_version"), bundle.coverage.get("curriculum_version")}
    if len(versions) != 1:
        issues.append(CurriculumIssue("$.curriculum_version", "VERSION_MISMATCH", "structure, graph, and coverage must use the same curriculum_version"))
    if bundle.structure.get("taxonomy_dependency", {}).get("taxonomy_version") != bundle.taxonomy.get("taxonomy_version"):
        issues.append(CurriculumIssue("$.structure.taxonomy_dependency.taxonomy_version", "TAXONOMY_VERSION_MISMATCH", "declared taxonomy version does not match the loaded taxonomy"))
    issues = sorted(set(issues))
    structure = bundle.structure
    graph = bundle.graph
    coverage = bundle.coverage
    report = {
        "schema_version": "1.0",
        "curriculum_version": str(structure.get("curriculum_version", "00000000")),
        "status": "VALID" if not issues else "INVALID",
        "validated_artifacts": [
            bundle.paths[0].name,
            bundle.paths[1].name,
            bundle.paths[2].name,
            f"{bundle.paths[3].parent.name}/{bundle.paths[3].name}",
        ],
        "counts": {
            "levels": len(structure.get("levels", [])) if isinstance(structure.get("levels"), list) else 0,
            "tiers": sum(len(level.get("tiers", [])) for level in structure.get("levels", []) if isinstance(level, dict)) if isinstance(structure.get("levels"), list) else 0,
            "units": len(structure.get("units", [])) if isinstance(structure.get("units"), list) else 0,
            "lessons": len(structure.get("lessons", [])) if isinstance(structure.get("lessons"), list) else 0,
            "reviews": len(structure.get("reviews", [])) if isinstance(structure.get("reviews"), list) else 0,
            "graph_nodes": len(graph.get("nodes", [])) if isinstance(graph.get("nodes"), list) else 0,
            "graph_edges": len(graph.get("edges", [])) if isinstance(graph.get("edges"), list) else 0,
            "coverage_dimensions": len(coverage.get("dimensions", [])) if isinstance(coverage.get("dimensions"), list) else 0,
        },
        "issues": [issue.as_dict() for issue in issues],
        "topological_order": list(topological_order),
    }
    return CurriculumValidationResult(tuple(issues), topological_order, report)
