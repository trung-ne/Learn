"""Build and validate the outline-only M16 B1 curriculum blueprint."""

from __future__ import annotations

import json
from collections import defaultdict, deque
from pathlib import Path
from typing import Any, Iterable

from english_master.knowledge_graph.service import validate_population
from english_master.lesson_generation.canonical import sha256_json
from english_master.schema_validation import load_document, validate_instance

DIMS = (
    "grammar",
    "vocabulary_senses",
    "functions",
    "pronunciation",
    "discourse",
    "pragmatics",
    "collocations",
    "lexical_chunks",
    "topics",
    "skills",
)
TIERS = ("B1.1", "B1.2")
UNIT_LESSON_COUNT = 5
UNITS_PER_TIER = 5

# These concise planning labels are original project-authored outline data. They
# allocate broad M15 nodes without supplying instructional prose or exercises.
UNIT_SPECS: tuple[dict[str, Any], ...] = (
    {
        "title": "Life experiences and personal change",
        "lessons": (
            ("Experiences up to now", "Describe a life experience and connect it to the present.", ("grammar", "vocabulary_senses", "pronunciation")),
            ("Explaining an opinion", "State an opinion and support it with a clear reason.", ("functions", "discourse", "lexical_chunks")),
            ("Agreeing and disagreeing tactfully", "Respond to a different view without sounding abrupt.", ("pragmatics", "collocations", "topics", "skills")),
            ("A connected personal response", "Combine experience and opinion in connected language.", DIMS),
            ("Review: experiences and change", "Review experience, opinion, and tactful response targets.", DIMS),
        ),
    },
    {
        "title": "Media and informed opinions",
        "lessons": (
            ("Media experiences", "Relate media experiences and distinguish finished from current relevance.", ("grammar", "vocabulary_senses", "topics")),
            ("Reasons and examples", "Develop an opinion with a reason and a relevant example.", ("functions", "discourse", "skills")),
            ("Emphasis and viewpoint", "Use contrastive stress and opinion frames to highlight a viewpoint.", ("pronunciation", "lexical_chunks", "collocations")),
            ("Discussing different views", "Agree or disagree tactfully in a familiar media discussion.", ("pragmatics", "functions", "skills")),
            ("Review: media opinions", "Review connected opinions about familiar media.", DIMS),
        ),
    },
    {
        "title": "Relationships and communication",
        "lessons": (
            ("Changes in relationships", "Describe an experience or change in a familiar relationship.", ("grammar", "vocabulary_senses", "topics")),
            ("Expressing a concern", "Give a view and explain a relationship concern clearly.", ("functions", "discourse", "lexical_chunks")),
            ("Tactful responses", "Use suitable stress and pragmatic choices when views differ.", ("pronunciation", "pragmatics", "skills")),
            ("Relationship language", "Use common opinion and relationship collocations in discussion.", ("collocations", "functions", "skills")),
            ("Review: relationships", "Review experience, concern, and tactful discussion language.", DIMS),
        ),
    },
    {
        "title": "Community issues and choices",
        "lessons": (
            ("Experience in the community", "Connect a past community experience to a current issue.", ("grammar", "vocabulary_senses", "topics")),
            ("Building a viewpoint", "Organize a paragraph or short turn around one supported opinion.", ("functions", "discourse", "skills")),
            ("Emphasizing key contrasts", "Use contrastive stress and opinion chunks to compare choices.", ("pronunciation", "lexical_chunks", "collocations")),
            ("Discussing alternatives", "Disagree tactfully and propose a reasonable alternative.", ("pragmatics", "functions", "skills")),
            ("Review: community choices", "Review supported opinions and responses about community choices.", DIMS),
        ),
    },
    {
        "title": "B1.1 consolidation",
        "lessons": (
            ("Experiences across contexts", "Select suitable B1.1 language for experience and change.", DIMS),
            ("Connected opinion practice", "Develop a clear opinion across several linked sentences.", ("discourse", "functions", "skills", "vocabulary_senses")),
            ("Tactful discussion practice", "Use stress, chunks, and pragmatic choices in a short discussion.", ("pronunciation", "pragmatics", "lexical_chunks", "collocations")),
            ("B1.1 preparation", "Prepare to combine experience and supported opinion targets.", DIMS),
            ("Review: B1.1 consolidation", "Review all B1.1 target dimensions before the unit test.", DIMS),
        ),
    },
    {
        "title": "Stories of personal change",
        "lessons": (
            ("A sequenced past story", "Sequence past events in a coherent account of change.", ("grammar", "vocabulary_senses", "discourse")),
            ("Clarifying what happened", "Clarify a detail when a listener does not understand.", ("functions", "lexical_chunks", "skills")),
            ("Narrative intonation", "Use intonation to mark stages and highlights in a story.", ("pronunciation", "collocations", "topics")),
            ("Choosing an appropriate register", "Adjust familiar language for a less familiar listener.", ("pragmatics", "functions", "skills")),
            ("Review: personal-change stories", "Review sequence, clarification, and narrative delivery.", DIMS),
        ),
    },
    {
        "title": "Events in the community",
        "lessons": (
            ("Reporting an event", "Tell a coherent story about a familiar community event.", ("grammar", "vocabulary_senses", "topics")),
            ("Developing the story", "Link events and maintain a clear topic across the account.", ("discourse", "functions", "skills")),
            ("Repairing and elaborating", "Use repair frames and collocations to clarify or add detail.", ("lexical_chunks", "collocations", "pragmatics")),
            ("Engaging spoken delivery", "Use narrative intonation to make event structure clear.", ("pronunciation", "skills", "functions")),
            ("Review: community events", "Review coherent event reporting and clarification.", DIMS),
        ),
    },
    {
        "title": "Media stories and perspectives",
        "lessons": (
            ("Retelling a media story", "Retell the main sequence of a familiar media story.", ("grammar", "vocabulary_senses", "discourse")),
            ("Explaining a perspective", "Clarify a viewpoint and add enough context for a listener.", ("functions", "pragmatics", "skills")),
            ("Narrative language patterns", "Use narrative chunks, collocations, and intonation coherently.", ("lexical_chunks", "collocations", "pronunciation")),
            ("Comparing accounts", "Discuss two accounts and repair a misunderstanding when needed.", ("topics", "functions", "skills")),
            ("Review: media stories", "Review retelling, perspective, and repair targets.", DIMS),
        ),
    },
    {
        "title": "Relationships over time",
        "lessons": (
            ("A relationship story", "Sequence events that changed or maintained a relationship.", ("grammar", "vocabulary_senses", "collocations")),
            ("Topic development", "Develop the people, events, and consequences in a clear account.", ("discourse", "topics", "skills")),
            ("Clarifying sensitively", "Repair meaning with register suitable for a less familiar setting.", ("functions", "pragmatics", "lexical_chunks")),
            ("Telling the story aloud", "Use narrative intonation and connected language in discussion.", ("pronunciation", "skills", "functions")),
            ("Review: relationships over time", "Review relationship narratives and sensitive clarification.", DIMS),
        ),
    },
    {
        "title": "B1.2 consolidation",
        "lessons": (
            ("Narratives across contexts", "Select suitable B1.2 language for stories and discussion.", DIMS),
            ("Extended story practice", "Develop and clarify a coherent story in connected language.", ("grammar", "discourse", "functions", "skills")),
            ("Spoken interaction practice", "Use narrative intonation, repair frames, and relationship language.", ("pronunciation", "vocabulary_senses", "lexical_chunks", "collocations")),
            ("B1.2 preparation", "Prepare to use all B1.2 targets in an extended familiar discussion.", DIMS),
            ("Review: B1.2 consolidation", "Review all B1.2 target dimensions before the unit test.", DIMS),
        ),
    },
)


def _node_id(tier: str, dimension: str) -> str:
    return f"kg_{tier.lower().replace('.', '_')}_{dimension}"


def _unique_by_id(records: Iterable[dict[str, Any]], kind: str) -> dict[str, dict[str, Any]]:
    values = list(records)
    result = {record["id"]: record for record in values}
    if len(result) != len(values):
        raise ValueError(f"duplicate {kind} IDs")
    return result


def build(population: dict[str, Any], edition: str = "m16b1-v1") -> dict[str, Any]:
    """Build the fixed, content-free B1 planning outline from M15 nodes."""
    if edition != "m16b1-v1":
        raise ValueError("B1 blueprint edition must be m16b1-v1")
    nodes = {node["id"]: node for node in population["nodes"]}
    expected_b1_nodes = {_node_id(tier, dimension) for tier in TIERS for dimension in DIMS}
    missing = expected_b1_nodes - nodes.keys()
    if missing:
        raise ValueError(f"missing M15 B1 target: {sorted(missing)[0]}")

    entry_prerequisites = sorted({
        prerequisite
        for dimension in DIMS
        for prerequisite in nodes[_node_id("B1.1", dimension)]["prerequisites"]
    })
    units: list[dict[str, Any]] = []
    lessons: list[dict[str, Any]] = []
    unit_tests: list[dict[str, Any]] = []
    introduced: set[str] = set()

    for unit_index, spec in enumerate(UNIT_SPECS, start=1):
        tier = TIERS[(unit_index - 1) // UNITS_PER_TIER]
        unit_id = f"{edition}-b1-u{unit_index:02d}"
        lesson_ids: list[str] = []
        for lesson_index, (title, objective, dimensions) in enumerate(spec["lessons"], start=1):
            lesson_id = f"{unit_id}-l{lesson_index:02d}"
            lesson_ids.append(lesson_id)
            kind = "REVIEW" if lesson_index == UNIT_LESSON_COUNT else "LEARN"
            targets = []
            for dimension in dimensions:
                node_id = _node_id(tier, dimension)
                if kind == "REVIEW":
                    use = "REVIEW"
                elif node_id not in introduced:
                    use = "INTRODUCE"
                    introduced.add(node_id)
                else:
                    use = "PRACTISE"
                targets.append({"node_id": node_id, "dimension": dimension, "use": use})
            prerequisite_ids = [] if unit_index == 1 and lesson_index == 1 else [
                f"{edition}-b1-u{unit_index:02d}-l{lesson_index - 1:02d}"
                if lesson_index > 1
                else f"{edition}-b1-u{unit_index - 1:02d}-l{UNIT_LESSON_COUNT:02d}"
            ]
            lessons.append({
                "id": lesson_id,
                "unit_id": unit_id,
                "tier": tier,
                "sequence": lesson_index,
                "lesson_kind": kind,
                "title": title,
                "objectives": [objective],
                "targets": targets,
                "prerequisite_lesson_ids": prerequisite_ids,
            })
        test_id = f"{edition}-b1-unit-test-{unit_index:02d}"
        units.append({
            "id": unit_id,
            "tier": tier,
            "sequence": unit_index,
            "title": spec["title"],
            "lesson_ids": lesson_ids,
            "review_lesson_id": lesson_ids[-1],
            "unit_test_id": test_id,
        })
        unit_tests.append({
            "id": test_id,
            "tier": tier,
            "unit_id": unit_id,
            "placement_after_lesson_id": lesson_ids[-1],
            "assessed_lesson_ids": lesson_ids,
            "target_dimensions": list(DIMS),
        })

    return {
        "schema_version": "1.0",
        "record_type": "m16_b1_curriculum_blueprint",
        "edition": edition,
        "status": "OUTLINE_ONLY",
        "source_population_id": population["population_id"],
        "source_population_sha256": sha256_json(population),
        "tiers": list(TIERS),
        "entry_prerequisite_node_ids": entry_prerequisites,
        "units": units,
        "lessons": lessons,
        "unit_tests": unit_tests,
    }


def validate(value: dict[str, Any], population: dict[str, Any]) -> dict[str, Any]:
    """Validate B1 reference integrity, coverage, order, and prerequisites."""
    validate_instance(value, "m16-b1-curriculum-blueprint")
    validate_population(population)
    if value["source_population_id"] != population["population_id"]:
        raise ValueError("blueprint source population ID does not match M15 population")
    if value["source_population_sha256"] != sha256_json(population):
        raise ValueError("blueprint source population hash does not match M15 population")

    nodes = {node["id"]: node for node in population["nodes"]}
    units = _unique_by_id(value["units"], "unit")
    lessons = _unique_by_id(value["lessons"], "lesson")
    unit_tests = _unique_by_id(value["unit_tests"], "unit test")
    if len(units) != 10 or len(lessons) != 50 or len(unit_tests) != 10:
        raise ValueError("B1 blueprint must contain ten units, fifty lessons, and ten unit tests")

    expected_nodes = {_node_id(tier, dimension) for tier in TIERS for dimension in DIMS}
    entry_nodes = set(value["entry_prerequisite_node_ids"])
    expected_entry_nodes = {
        prerequisite
        for dimension in DIMS
        for prerequisite in nodes[_node_id("B1.1", dimension)]["prerequisites"]
    }
    if entry_nodes != expected_entry_nodes:
        raise ValueError("B1 entry prerequisites must match direct B1.1 M15 prerequisites")
    for node_id in entry_nodes:
        if node_id not in nodes:
            raise ValueError(f"B1 entry prerequisite does not resolve: {node_id}")
        if nodes[node_id]["tier"] != "A2.2":
            raise ValueError(f"B1 entry prerequisite is not an A2.2 node: {node_id}")

    unit_order: dict[str, int] = {}
    for unit in units.values():
        expected_unit_id = f"m16b1-v1-b1-u{unit['sequence']:02d}"
        if unit["id"] != expected_unit_id:
            raise ValueError(f"unit has non-deterministic ID: {unit['id']}")
        if unit["sequence"] in unit_order.values():
            raise ValueError(f"duplicate unit sequence: {unit['sequence']}")
        expected_tier = TIERS[(unit["sequence"] - 1) // UNITS_PER_TIER]
        if unit["tier"] != expected_tier:
            raise ValueError(f"unit {unit['id']} has incorrect tier")
        unit_order[unit["id"]] = unit["sequence"]
        if len(unit["lesson_ids"]) != UNIT_LESSON_COUNT or len(set(unit["lesson_ids"])) != UNIT_LESSON_COUNT:
            raise ValueError(f"unit {unit['id']} must contain five unique lessons")
        if unit["review_lesson_id"] != unit["lesson_ids"][-1]:
            raise ValueError(f"unit {unit['id']} review lesson must be last")
        if unit["unit_test_id"] not in unit_tests:
            raise ValueError(f"unit {unit['id']} references missing unit test")
        for lesson_id in unit["lesson_ids"]:
            lesson = lessons.get(lesson_id)
            if lesson is None:
                raise ValueError(f"unit {unit['id']} references missing lesson {lesson_id}")
            if lesson["unit_id"] != unit["id"] or lesson["tier"] != unit["tier"]:
                raise ValueError(f"lesson {lesson_id} does not agree with unit {unit['id']}")
        review = lessons[unit["review_lesson_id"]]
        if review["lesson_kind"] != "REVIEW":
            raise ValueError(f"unit {unit['id']} review lesson is not marked REVIEW")

    lesson_order: dict[str, tuple[int, int]] = {}
    introduced: dict[str, str] = {}
    reviewed: set[str] = set()
    review_orders: dict[str, list[tuple[int, int]]] = defaultdict(list)
    adjacency: dict[str, set[str]] = defaultdict(set)
    for lesson in lessons.values():
        unit = units.get(lesson["unit_id"])
        if unit is None:
            raise ValueError(f"lesson {lesson['id']} references missing unit {lesson['unit_id']}")
        expected_lesson_id = f"{unit['id']}-l{lesson['sequence']:02d}"
        if lesson["id"] != expected_lesson_id:
            raise ValueError(f"lesson has non-deterministic ID: {lesson['id']}")
        order = (unit_order[unit["id"]], lesson["sequence"])
        if order in lesson_order.values():
            raise ValueError(f"duplicate lesson order: {order}")
        lesson_order[lesson["id"]] = order
        if lesson["id"] not in unit["lesson_ids"]:
            raise ValueError(f"lesson {lesson['id']} is not linked from its unit")
        target_node_ids: set[str] = set()
        for target in lesson["targets"]:
            node_id = target["node_id"]
            node = nodes.get(node_id)
            if node is None:
                raise ValueError(f"lesson {lesson['id']} references missing target {node_id}")
            if node_id in target_node_ids:
                raise ValueError(f"lesson {lesson['id']} repeats target {node_id}")
            target_node_ids.add(node_id)
            if node_id not in expected_nodes or node["tier"] != lesson["tier"] or node["dimension"] != target["dimension"]:
                raise ValueError(f"lesson {lesson['id']} target {node_id} tier/dimension disagrees")
            if target["use"] == "INTRODUCE":
                if node_id in introduced:
                    raise ValueError(f"target {node_id} is introduced more than once")
                introduced[node_id] = lesson["id"]
            elif target["use"] == "REVIEW":
                reviewed.add(node_id)
                review_orders[node_id].append(order)
        if lesson["lesson_kind"] == "REVIEW" and not all(target["use"] == "REVIEW" for target in lesson["targets"]):
            raise ValueError(f"review lesson {lesson['id']} must only review targets")
        if lesson["lesson_kind"] == "LEARN" and any(target["use"] == "REVIEW" for target in lesson["targets"]):
            raise ValueError(f"non-review lesson {lesson['id']} cannot use REVIEW targets")
        for prerequisite_id in lesson["prerequisite_lesson_ids"]:
            if prerequisite_id not in lessons:
                raise ValueError(f"lesson {lesson['id']} references missing prerequisite {prerequisite_id}")
            adjacency[prerequisite_id].add(lesson["id"])

    if set(introduced) != expected_nodes:
        missing = expected_nodes - set(introduced)
        extra = set(introduced) - expected_nodes
        detail = sorted(missing or extra)[0]
        raise ValueError(f"B1 target introduction coverage is incomplete or invalid: {detail}")
    if reviewed != expected_nodes:
        missing = expected_nodes - reviewed
        detail = sorted(missing or expected_nodes - reviewed)[0]
        raise ValueError(f"B1 target review coverage is incomplete: {detail}")
    for node_id, orders in review_orders.items():
        if not any(order > lesson_order[introduced[node_id]] for order in orders):
            raise ValueError(f"B1 target {node_id} is reviewed before its introduction")

    for lesson in lessons.values():
        order = lesson_order[lesson["id"]]
        for prerequisite_id in lesson["prerequisite_lesson_ids"]:
            if lesson_order[prerequisite_id] >= order:
                raise ValueError(f"lesson {lesson['id']} has a forward prerequisite {prerequisite_id}")
        for target in lesson["targets"]:
            node = nodes[target["node_id"]]
            for prerequisite_node_id in node["prerequisites"]:
                if node["tier"] == "B1.1":
                    if prerequisite_node_id not in entry_nodes:
                        raise ValueError(f"B1.1 target has undeclared prior-level prerequisite {prerequisite_node_id}")
                elif prerequisite_node_id not in introduced:
                    raise ValueError(f"B1.2 target has missing B1 prerequisite {prerequisite_node_id}")
                elif lesson_order[introduced[prerequisite_node_id]] >= order:
                    raise ValueError(f"B1 target is introduced before its prerequisite {prerequisite_node_id}")

    for unit_test in unit_tests.values():
        unit = units.get(unit_test["unit_id"])
        if unit is None:
            raise ValueError(f"unit test {unit_test['id']} references missing unit")
        if unit_test["id"] != unit["unit_test_id"] or unit_test["tier"] != unit["tier"]:
            raise ValueError(f"unit test {unit_test['id']} does not agree with unit {unit['id']}")
        if unit_test["placement_after_lesson_id"] != unit["review_lesson_id"]:
            raise ValueError(f"unit test {unit_test['id']} must follow the review lesson")
        if unit_test["assessed_lesson_ids"] != unit["lesson_ids"]:
            raise ValueError(f"unit test {unit_test['id']} must assess its five unit lessons")
        if set(unit_test["target_dimensions"]) != set(DIMS):
            raise ValueError(f"unit test {unit_test['id']} must cover all target dimensions")

    indegree = {lesson_id: 0 for lesson_id in lessons}
    for targets in adjacency.values():
        for target in targets:
            indegree[target] += 1
    ready = deque(lesson_id for lesson_id, degree in indegree.items() if degree == 0)
    visited = 0
    while ready:
        lesson_id = ready.popleft()
        visited += 1
        for target in adjacency[lesson_id]:
            indegree[target] -= 1
            if indegree[target] == 0:
                ready.append(target)
    if visited != len(lessons):
        raise ValueError("lesson prerequisite graph contains a cycle")
    return value


def run(population_path: Path, output: Path) -> Path:
    """Build and atomically publish one outline-only B1 blueprint."""
    if output.exists():
        raise FileExistsError(f"refusing to overwrite immutable B1 blueprint: {output}")
    population = load_document(population_path)
    value = build(population)
    validate(value, population)
    output.parent.mkdir(parents=True, exist_ok=True)
    temporary = output.with_name(f".{output.name}.tmp")
    if temporary.exists():
        raise FileExistsError(f"refusing to overwrite temporary B1 blueprint: {temporary}")
    try:
        temporary.write_text(
            json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2) + "\n",
            encoding="utf-8",
        )
        temporary.replace(output)
    except BaseException:
        temporary.unlink(missing_ok=True)
        raise
    return output


def main() -> int:
    import argparse

    parser = argparse.ArgumentParser(description="Build or validate the M16 B1 outline blueprint")
    commands = parser.add_subparsers(dest="command", required=True)
    build_parser = commands.add_parser("build")
    build_parser.add_argument("population", type=Path)
    build_parser.add_argument("output", type=Path)
    validate_parser = commands.add_parser("validate")
    validate_parser.add_argument("population", type=Path)
    validate_parser.add_argument("blueprint", type=Path)
    args = parser.parse_args()
    if args.command == "build":
        run(args.population, args.output)
    else:
        validate(load_document(args.blueprint), load_document(args.population))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
