"""Build and validate the outline-only M16 A2 curriculum blueprint."""

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
TIERS = ("A2.1", "A2.2")
UNIT_LESSON_COUNT = 5
UNITS_PER_TIER = 5

# These concise planning labels are original project-authored outline data. They
# allocate broad M15 nodes without supplying instructional prose or exercises.
UNIT_SPECS: tuple[dict[str, Any], ...] = (
    {
        "title": "Recent experiences and simple stories",
        "lessons": (
            ("Past events: form and key words", "Describe one finished event with simple past-time language.", ("grammar", "vocabulary_senses", "pronunciation")),
            ("Event-reporting chunks", "Use a short frame to report what happened and when.", ("functions", "discourse", "lexical_chunks")),
            ("Follow-up questions and repair", "Ask one follow-up question and repair a simple misunderstanding.", ("pragmatics", "collocations", "topics", "skills")),
            ("A short personal account", "Organize a short account in a clear event order.", DIMS),
            ("Review: recent experiences", "Review the unit targets in a short account and follow-up exchange.", DIMS),
        ),
    },
    {
        "title": "Shopping and quantities",
        "lessons": (
            ("Choosing quantities", "Use count and noncount language for everyday shopping.", ("grammar", "vocabulary_senses", "functions")),
            ("Clarifying a purchase", "Ask for a quantity, price, or alternative in a short transaction.", ("functions", "pragmatics", "collocations")),
            ("Pronouncing clear requests", "Use thought groups and clear key words in a shopping request.", ("pronunciation", "lexical_chunks", "skills")),
            ("A useful local-service exchange", "Understand and produce a short, polite service exchange.", ("discourse", "topics", "skills")),
            ("Review: shopping and quantities", "Review quantity, request, and clarification language.", DIMS),
        ),
    },
    {
        "title": "Health, advice, and local services",
        "lessons": (
            ("Describing a recent problem", "Give a simple account of a recent health or service problem.", ("grammar", "vocabulary_senses", "functions")),
            ("Asking for help politely", "Make and respond to a polite request for practical help.", ("pragmatics", "lexical_chunks", "collocations")),
            ("Clear event sequence", "Use short thought groups to make the order of events clear.", ("pronunciation", "discourse", "skills")),
            ("Health and service follow-up", "Ask and answer a follow-up question about a local service.", ("topics", "functions", "skills")),
            ("Review: health and services", "Review the unit language in a short problem-and-response exchange.", DIMS),
        ),
    },
    {
        "title": "Travel and transport experiences",
        "lessons": (
            ("A completed journey", "Report a completed journey with key time and place details.", ("grammar", "vocabulary_senses", "discourse")),
            ("Travel questions and answers", "Ask and answer short questions about a journey or delay.", ("functions", "lexical_chunks", "skills")),
            ("Past endings and key information", "Make past-tense endings and important travel details audible.", ("pronunciation", "collocations", "topics")),
            ("Handling a travel problem", "Explain a simple travel problem and ask for a practical response.", ("pragmatics", "functions", "skills")),
            ("Review: travel experiences", "Review a short travel account, follow-up question, and repair.", DIMS),
        ),
    },
    {
        "title": "A2.1 consolidation",
        "lessons": (
            ("Comparing everyday situations", "Select suitable A2.1 language for a story, transaction, or request.", DIMS),
            ("Listening and retelling", "Follow a short event account and retell its main sequence.", ("discourse", "skills", "pronunciation", "vocabulary_senses")),
            ("Practical interaction", "Use a request, follow-up, and repair in one short interaction.", ("functions", "pragmatics", "lexical_chunks", "collocations")),
            ("A2.1 preparation", "Prepare to use the A2.1 targets across familiar practical contexts.", DIMS),
            ("Review: A2.1 consolidation", "Review all A2.1 target dimensions before the unit test.", DIMS),
        ),
    },
    {
        "title": "Plans for study and everyday life",
        "lessons": (
            ("Future plans with going to", "State a personal plan and give one reason for it.", ("grammar", "vocabulary_senses", "functions")),
            ("Planning language in speech", "Use weak forms and thought groups in a short plan.", ("pronunciation", "discourse", "lexical_chunks")),
            ("Inviting and responding", "Make, accept, or decline a simple invitation appropriately.", ("pragmatics", "collocations", "skills")),
            ("Study and future plans", "Organize a short exchange about study and future plans.", ("topics", "functions", "skills")),
            ("Review: plans for study and life", "Review plan, reason, invitation, and response language.", DIMS),
        ),
    },
    {
        "title": "Work, routines, and achievements",
        "lessons": (
            ("Work and study plans", "Describe a work or study plan using clear future language.", ("grammar", "vocabulary_senses", "topics")),
            ("Talking about an achievement", "Report a simple achievement and ask a relevant follow-up.", ("functions", "discourse", "skills")),
            ("Useful work and study chunks", "Use common planning and achievement chunks in a short exchange.", ("lexical_chunks", "collocations", "pragmatics")),
            ("Natural planned speech", "Use weak forms and clear information stress when arranging a plan.", ("pronunciation", "skills", "functions")),
            ("Review: work, routines, and achievements", "Review planning, achievement, and follow-up language.", DIMS),
        ),
    },
    {
        "title": "Offers, invitations, and arrangements",
        "lessons": (
            ("Making an offer", "Make a practical offer and respond clearly.", ("functions", "pragmatics", "vocabulary_senses")),
            ("Arranging a time and place", "Make a simple arrangement with a time, place, and plan.", ("grammar", "discourse", "topics")),
            ("Responding naturally", "Use invitation and arrangement chunks with suitable stress.", ("lexical_chunks", "collocations", "pronunciation")),
            ("Changing a plan", "Suggest and negotiate one small change to an arrangement.", ("functions", "skills", "pragmatics")),
            ("Review: offers and arrangements", "Review offers, invitations, arrangements, and changes.", DIMS),
        ),
    },
    {
        "title": "Community and future participation",
        "lessons": (
            ("Community plans", "Describe a future community activity and its purpose.", ("grammar", "vocabulary_senses", "topics")),
            ("Reasons and organization", "Organize a short plan with a reason and clear sequence.", ("discourse", "functions", "skills")),
            ("Inviting others", "Invite another person and respond appropriately to their answer.", ("pragmatics", "lexical_chunks", "collocations")),
            ("Clear planned speech", "Use weak forms, thought groups, and key-word stress in a plan.", ("pronunciation", "skills", "functions")),
            ("Review: community participation", "Review future plans, reasons, invitations, and arrangements.", DIMS),
        ),
    },
    {
        "title": "A2.2 consolidation",
        "lessons": (
            ("Planning across contexts", "Select suitable A2.2 language for study, work, or community plans.", DIMS),
            ("Coordinating a plan", "Make an arrangement, give a reason, and respond to a change.", ("functions", "discourse", "pragmatics", "skills")),
            ("Listening and speaking preparation", "Follow a short planned interaction and produce a clear response.", ("pronunciation", "vocabulary_senses", "lexical_chunks", "collocations")),
            ("A2.2 preparation", "Prepare to use the A2.2 targets in a connected practical exchange.", DIMS),
            ("Review: A2.2 consolidation", "Review all A2.2 target dimensions before the unit test.", DIMS),
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


def build(population: dict[str, Any], edition: str = "m16a2-v1") -> dict[str, Any]:
    """Build the fixed, content-free A2 planning outline from M15 nodes."""
    if edition != "m16a2-v1":
        raise ValueError("A2 blueprint edition must be m16a2-v1")
    nodes = {node["id"]: node for node in population["nodes"]}
    expected_a2_nodes = {_node_id(tier, dimension) for tier in TIERS for dimension in DIMS}
    missing = expected_a2_nodes - nodes.keys()
    if missing:
        raise ValueError(f"missing M15 A2 target: {sorted(missing)[0]}")

    entry_prerequisites = sorted({
        prerequisite
        for dimension in DIMS
        for prerequisite in nodes[_node_id("A2.1", dimension)]["prerequisites"]
    })
    units: list[dict[str, Any]] = []
    lessons: list[dict[str, Any]] = []
    unit_tests: list[dict[str, Any]] = []
    introduced: set[str] = set()

    for unit_index, spec in enumerate(UNIT_SPECS, start=1):
        tier = TIERS[(unit_index - 1) // UNITS_PER_TIER]
        unit_id = f"{edition}-a2-u{unit_index:02d}"
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
                f"{edition}-a2-u{unit_index:02d}-l{lesson_index - 1:02d}"
                if lesson_index > 1
                else f"{edition}-a2-u{unit_index - 1:02d}-l{UNIT_LESSON_COUNT:02d}"
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
        test_id = f"{edition}-a2-unit-test-{unit_index:02d}"
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
        "record_type": "m16_a2_curriculum_blueprint",
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
    """Validate A2 reference integrity, coverage, order, and prerequisites."""
    validate_instance(value, "m16-a2-curriculum-blueprint")
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
        raise ValueError("A2 blueprint must contain ten units, fifty lessons, and ten unit tests")

    expected_nodes = {_node_id(tier, dimension) for tier in TIERS for dimension in DIMS}
    entry_nodes = set(value["entry_prerequisite_node_ids"])
    expected_entry_nodes = {
        prerequisite
        for dimension in DIMS
        for prerequisite in nodes[_node_id("A2.1", dimension)]["prerequisites"]
    }
    if entry_nodes != expected_entry_nodes:
        raise ValueError("A2 entry prerequisites must match direct A2.1 M15 prerequisites")
    for node_id in entry_nodes:
        if node_id not in nodes:
            raise ValueError(f"A2 entry prerequisite does not resolve: {node_id}")
        if nodes[node_id]["tier"] != "A1.2":
            raise ValueError(f"A2 entry prerequisite is not an A1.2 node: {node_id}")

    unit_order: dict[str, int] = {}
    for unit in units.values():
        expected_unit_id = f"m16a2-v1-a2-u{unit['sequence']:02d}"
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
        raise ValueError(f"A2 target introduction coverage is incomplete or invalid: {detail}")
    if reviewed != expected_nodes:
        missing = expected_nodes - reviewed
        detail = sorted(missing or expected_nodes - reviewed)[0]
        raise ValueError(f"A2 target review coverage is incomplete: {detail}")
    for node_id, orders in review_orders.items():
        if not any(order > lesson_order[introduced[node_id]] for order in orders):
            raise ValueError(f"A2 target {node_id} is reviewed before its introduction")

    for lesson in lessons.values():
        order = lesson_order[lesson["id"]]
        for prerequisite_id in lesson["prerequisite_lesson_ids"]:
            if lesson_order[prerequisite_id] >= order:
                raise ValueError(f"lesson {lesson['id']} has a forward prerequisite {prerequisite_id}")
        for target in lesson["targets"]:
            node = nodes[target["node_id"]]
            for prerequisite_node_id in node["prerequisites"]:
                if node["tier"] == "A2.1":
                    if prerequisite_node_id not in entry_nodes:
                        raise ValueError(f"A2.1 target has undeclared prior-level prerequisite {prerequisite_node_id}")
                elif prerequisite_node_id not in introduced:
                    raise ValueError(f"A2.2 target has missing A2 prerequisite {prerequisite_node_id}")
                elif lesson_order[introduced[prerequisite_node_id]] >= order:
                    raise ValueError(f"A2 target is introduced before its prerequisite {prerequisite_node_id}")

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
    """Build and atomically publish one outline-only A2 blueprint."""
    if output.exists():
        raise FileExistsError(f"refusing to overwrite immutable A2 blueprint: {output}")
    population = load_document(population_path)
    value = build(population)
    validate(value, population)
    output.parent.mkdir(parents=True, exist_ok=True)
    temporary = output.with_name(f".{output.name}.tmp")
    if temporary.exists():
        raise FileExistsError(f"refusing to overwrite temporary A2 blueprint: {temporary}")
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

    parser = argparse.ArgumentParser(description="Build or validate the M16 A2 outline blueprint")
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
