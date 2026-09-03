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


def _review_source_scope(
    *,
    structure: Mapping[str, Any],
    lessons: Mapping[str, JsonObject],
    nodes: Mapping[str, JsonObject],
    lesson_order: list[str],
    lesson_id: str,
    lesson: JsonObject,
    review_pairs: set[tuple[str, str]],
    introduction_pairs: set[tuple[str, str]],
    taxonomy: Mapping[str, JsonObject],
) -> tuple[dict[str, set[str]], set[str]]:
    """Resolve only knowledge explicitly carried by authorized review-source lessons."""

    declared = lesson.get("review_of", [])
    if not isinstance(declared, list) or any(not isinstance(value, str) for value in declared):
        raise ValueError(f"lesson {lesson_id!r} has malformed review_of lesson references")
    declared_sources = set(declared)
    incoming_sources = {source for source, target in review_pairs if target == lesson_id}
    if declared_sources != incoming_sources:
        raise ValueError(
            f"lesson {lesson_id!r} review_of references do not match M5 review edges"
        )

    positions = {value: index for index, value in enumerate(lesson_order)}
    target_position = positions.get(lesson_id)
    if target_position is None:
        raise ValueError(f"lesson {lesson_id!r} has no resolvable M5 lesson position")
    accepted_statuses = set(
        structure.get("taxonomy_dependency", {}).get("accepted_record_statuses", [])
    )
    typed: dict[str, set[str]] = {family: set() for family in FAMILIES}
    supporting: set[str] = set()

    for source_id in sorted(declared_sources):
        source = lessons.get(source_id)
        source_position = positions.get(source_id)
        if (
            source is None
            or nodes.get(source_id, {}).get("type") != "lesson"
            or source_position is None
        ):
            raise ValueError(
                f"review source {source_id!r} for lesson {lesson_id!r} is not resolvable"
            )
        if source_position >= target_position:
            raise ValueError(
                f"review source {source_id!r} must precede lesson {lesson_id!r}"
            )

        source_references: list[tuple[str, str | None]] = []
        for family in FAMILIES:
            values = source.get(family, [])
            if not isinstance(values, list) or any(not isinstance(value, str) for value in values):
                raise ValueError(
                    f"review source {source_id!r} has malformed {family} references"
                )
            source_references.extend((value, family) for value in values)
        values = source.get("taxonomy_concepts", [])
        if not isinstance(values, list) or any(not isinstance(value, str) for value in values):
            raise ValueError(
                f"review source {source_id!r} has malformed taxonomy_concepts references"
            )
        source_references.extend((value, None) for value in values)

        for record_id, declared_family in source_references:
            record = taxonomy.get(record_id)
            if record is None:
                raise ValueError(
                    f"review target {record_id!r} from {source_id!r} is not resolvable"
                )
            actual_family = record_family(record)
            if declared_family is not None and actual_family != declared_family:
                raise ValueError(
                    f"review target {record_id!r} from {source_id!r} has the wrong type"
                )
            if record.get("status") not in accepted_statuses:
                raise ValueError(
                    f"review target {record_id!r} from {source_id!r} is not M5-authorized"
                )
            introduced_by = {
                introducer
                for introducer, target in introduction_pairs
                if target == record_id and introducer in positions
            }
            if not introduced_by or min(positions[value] for value in introduced_by) > source_position:
                raise ValueError(
                    f"review target {record_id!r} was not introduced by {source_id!r} or earlier"
                )
            if actual_family is None:
                supporting.add(record_id)
            else:
                typed[actual_family].add(record_id)

    return typed, supporting


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
    all_introduction_pairs = {
        (edge["from"], edge["to"])
        for edge in edges
        if edge.get("type") == "introduction"
        and isinstance(edge.get("from"), str)
        and isinstance(edge.get("to"), str)
    }
    introduction_pairs = {
        pair for pair in all_introduction_pairs if pair[0] == lesson_id
    }
    review_pairs = {
        (edge["from"], edge["to"])
        for edge in edges
        if edge.get("type") == "review"
        and edge.get("to") == lesson_id
        and isinstance(edge.get("from"), str)
        and isinstance(edge.get("to"), str)
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
    review_scope, review_supporting = _review_source_scope(
        structure=structure,
        lessons=lessons,
        nodes=nodes,
        lesson_order=lesson_order,
        lesson_id=lesson_id,
        lesson=lesson,
        review_pairs=review_pairs,
        introduction_pairs=all_introduction_pairs,
        taxonomy=taxonomy,
    ) if lesson is not None else ({family: set() for family in FAMILIES}, set())
    reviewed = {
        family: sorted(
            (values - introduction_targets)
            | (review_scope[family] - introduction_targets)
        )
        for family, values in family_refs.items()
    }
    supporting_references.update(review_supporting)
    outline_references.update(review_supporting)
    for values in review_scope.values():
        outline_references.update(values)
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
