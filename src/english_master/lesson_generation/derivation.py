"""Deterministic M5-to-M6 lesson context derivation."""

from __future__ import annotations

from collections import defaultdict
from typing import Any, Iterable, Mapping

from english_master.curriculum_validation.validator import CurriculumBundle

from .models import JsonObject

LEVELS = (
    "A1.1",
    "A1.2",
    "A2.1",
    "A2.2",
    "B1.1",
    "B1.2",
    "B2.1",
    "B2.2",
    "C1.1",
    "C1.2",
    "C2.1",
    "C2.2",
)
FAMILIES = ("grammar", "vocabulary", "functions", "pronunciation")
TYPE_BY_FAMILY = {
    "grammar": "GRAMMAR",
    "vocabulary": "VOCABULARY_SENSE",
    "functions": "COMMUNICATIVE_FUNCTION",
    "pronunciation": "PRONUNCIATION",
}


def taxonomy_index(bundle: CurriculumBundle) -> dict[str, JsonObject]:
    records: dict[str, JsonObject] = {}
    for collection in ("concepts", "vocabulary_senses"):
        values = bundle.taxonomy.get(collection, [])
        if not isinstance(values, list):
            continue
        for record in values:
            if isinstance(record, dict) and isinstance(record.get("id"), str):
                records[record["id"]] = record
    return records


def annotation_index(bundle: CurriculumBundle) -> dict[str, JsonObject]:
    values = bundle.taxonomy.get("vietnamese_learner_annotations", [])
    if not isinstance(values, list):
        return {}
    return {
        record["id"]: record
        for record in values
        if isinstance(record, dict) and isinstance(record.get("id"), str)
    }


def record_family(record: Mapping[str, Any]) -> str | None:
    record_type = record.get("type")
    if record_type == "grammar":
        return "grammar"
    if record_type == "communicative_function":
        return "functions"
    if record_type == "pronunciation":
        return "pronunciation"
    if "lemma" in record and "sense_number" in record:
        return "vocabulary"
    return None


def record_type(record: Mapping[str, Any]) -> str:
    return TYPE_BY_FAMILY.get(record_family(record) or "", "SUPPORTING_CONCEPT")


def record_cefr(record: Mapping[str, Any]) -> Any:
    return record.get("minimum_cefr", record.get("cefr"))


def record_definition(record: Mapping[str, Any]) -> Any:
    return record.get("description", record.get("definition"))


def canonical_edges(edges: Iterable[tuple[str, str]]) -> list[JsonObject]:
    return [
        {"from": source, "to": target}
        for source, target in sorted(set(edges))
    ]


def cycle_nodes(edges: Iterable[tuple[str, str]]) -> set[str]:
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


def taxonomy_closure(
    target_ids: set[str],
    taxonomy: Mapping[str, JsonObject],
) -> tuple[set[str], set[str]]:
    closure: set[str] = set()
    unresolved: set[str] = set()
    visiting: set[str] = set()
    visited: set[str] = set()

    def visit(record_id: str) -> None:
        if record_id in visiting:
            unresolved.add(record_id)
            return
        if record_id in visited:
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
        visited.add(record_id)

    for target_id in sorted(target_ids):
        visit(target_id)
    return closure, unresolved


def derive_context(bundle: CurriculumBundle, lesson_id: str) -> JsonObject:
    """Derive the full narrow context for one M5 lesson outline."""

    structure = bundle.structure
    graph = bundle.graph
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
            (
                (node_id, node.get("sequence_key", ""))
                for node_id, node in nodes.items()
                if node.get("type") == "lesson"
            ),
            key=lambda item: (item[1], item[0]),
        )
    ]
    edges = [edge for edge in graph.get("edges", []) if isinstance(edge, dict)]
    prerequisite_pairs = {
        (edge["from"], edge["to"])
        for edge in edges
        if edge.get("type") == "lesson_prerequisite"
        and isinstance(edge.get("from"), str)
        and isinstance(edge.get("to"), str)
    }
    introduction_pairs = {
        (edge["from"], edge["to"])
        for edge in edges
        if edge.get("type") == "introduction"
        and edge.get("from") == lesson_id
        and isinstance(edge.get("to"), str)
    }
    review_pairs = {
        (edge["from"], edge["to"])
        for edge in edges
        if edge.get("type") == "review"
        and edge.get("to") == lesson_id
        and isinstance(edge.get("from"), str)
        and nodes.get(edge.get("from"), {}).get("type") == "lesson"
    }
    direct_prerequisites = {
        source for source, target in prerequisite_pairs if target == lesson_id
    }
    transitive_lessons: set[str] = set()

    def add_lesson_predecessors(target: str) -> None:
        for source, edge_target in sorted(prerequisite_pairs):
            if edge_target == target and source not in transitive_lessons:
                transitive_lessons.add(source)
                add_lesson_predecessors(source)

    add_lesson_predecessors(lesson_id)
    taxonomy = taxonomy_index(bundle)
    outline_references: set[str] = set()
    supporting_references: set[str] = set()
    family_refs: dict[str, set[str]] = {family: set() for family in FAMILIES}
    if lesson is not None:
        for family in FAMILIES:
            values = lesson.get(family, [])
            if isinstance(values, list):
                family_refs[family] = {
                    value for value in values if isinstance(value, str)
                }
                outline_references.update(family_refs[family])
        values = lesson.get("taxonomy_concepts", [])
        if isinstance(values, list):
            supporting_references = {
                value for value in values if isinstance(value, str)
            }
            outline_references.update(supporting_references)
    introduction_targets = {target for _, target in introduction_pairs}
    introduced = {
        family: sorted(values & introduction_targets)
        for family, values in family_refs.items()
    }
    reviewed = {
        family: sorted(values - introduction_targets)
        for family, values in family_refs.items()
    }
    target_closure, unresolved = taxonomy_closure(outline_references, taxonomy)

    previous: dict[str, Any] = {
        "completed_lessons": sorted(transitive_lessons),
    }
    target_position = lesson_order.index(lesson_id) if lesson_id in lesson_order else -1
    earlier_lessons = set(lesson_order[:target_position]) if target_position >= 0 else set()
    for family in FAMILIES:
        known: set[str] = set()
        for edge in edges:
            target = edge.get("to")
            if (
                edge.get("type") == "introduction"
                and edge.get("from") in earlier_lessons
                and isinstance(target, str)
                and record_family(taxonomy.get(target, {})) == family
            ):
                known.add(target)
        previous[family] = sorted(known)
    previous["supporting"] = sorted(
        {
            edge["to"]
            for edge in edges
            if edge.get("type") == "introduction"
            and edge.get("from") in earlier_lessons
            and isinstance(edge.get("to"), str)
            and record_family(taxonomy.get(edge["to"], {})) is None
        }
    )

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
