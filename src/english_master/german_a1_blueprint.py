"""Build and validate the outline-only German A1.1 mini blueprint."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from english_master.german_bootstrap import validate_population
from english_master.language_profiles import course_path, knowledge_graph_id
from english_master.lesson_generation.canonical import sha256_json
from english_master.schema_validation import load_document, validate_instance

ROOT = Path(__file__).resolve().parents[2]
POPULATION_PATH = ROOT / "curriculum" / "german-bootstrap" / "v1" / "population.json"
DIMS = ("grammar", "vocabulary_senses", "functions", "pronunciation", "discourse", "pragmatics", "collocations", "lexical_chunks", "topics", "skills")

_UNIT_SPECS = (
    ("Erste Kontakte", (
        ("Begrüßen und buchstabieren", "Einfache deutsche Begrüßungen verwenden und Namen buchstabieren.", ("grammar", "pronunciation", "lexical_chunks")),
        ("Sich vorstellen", "Den eigenen Namen nennen und nach dem Namen fragen.", ("vocabulary_senses", "functions")),
        ("Name, Herkunft und Wohnort", "Einfache persönliche Angaben machen und verstehen.", ("topics", "collocations")),
        ("Ein kurzes Kennenlerngespräch", "Ein kurzes Gespräch mit passenden Fragen und Antworten führen.", ("discourse", "pragmatics", "skills")),
        ("Wiederholung: Erste Kontakte", "Die Ziele der Einheit in einem kurzen Austausch wiederholen.", DIMS),
    )),
    ("Persönliche Angaben im Alltag", (
        ("Über sich und andere sprechen", "Über eine Person mit einfachen Angaben sprechen.", ("grammar", "vocabulary_senses", "functions")),
        ("Orte und einfache Angaben", "Orte, Herkunft und Wohnort in kurzen Sätzen verbinden.", ("topics", "collocations", "discourse")),
        ("Nachfragen und höflich reagieren", "Eine einfache Rückfrage stellen und höflich reagieren.", ("pragmatics", "lexical_chunks", "pronunciation")),
        ("Ein erstes Gespräch führen", "Ein kurzes Gespräch über persönliche Angaben zusammenhängend führen.", ("skills", "functions", "discourse")),
        ("Wiederholung: Persönliche Angaben", "Alle A1.1-Ziele in einem ersten Gespräch wiederholen.", DIMS),
    )),
)


def _population_hash(population: dict[str, Any]) -> str:
    return sha256_json(population)


def build(population: dict[str, Any] | None = None) -> dict[str, Any]:
    population = population or json.loads(POPULATION_PATH.read_text(encoding="utf-8"))
    validate_population(population)
    source_nodes = {node["id"]: node for node in population["nodes"]}
    lessons: list[dict[str, Any]] = []
    units: list[dict[str, Any]] = []
    previous_id: str | None = None
    for unit_number, (unit_title, lesson_specs) in enumerate(_UNIT_SPECS, start=1):
        unit_id = f"de-a1-v1-u{unit_number:02d}"
        unit_lessons: list[dict[str, Any]] = []
        for lesson_number, (title, objective, dimensions) in enumerate(lesson_specs, start=1):
            lesson_id = f"{unit_id}-l{lesson_number:02d}"
            kind = "REVIEW" if lesson_number == 5 else "LEARN"
            targets = [{"node_id": knowledge_graph_id("de", "A1.1", dimension), "use": "REVIEW" if kind == "REVIEW" else ("INTRODUCE" if not any(t["node_id"] == knowledge_graph_id("de", "A1.1", dimension) for l in lessons for t in l["targets"]) else "PRACTISE")} for dimension in dimensions]
            lesson = {"id": lesson_id, "unit_id": unit_id, "tier": "A1.1", "sequence": lesson_number, "kind": kind, "title": title, "objective": objective, "targets": targets, "prerequisites": [previous_id] if previous_id else []}
            unit_lessons.append(lesson)
            lessons.append(lesson)
            previous_id = lesson_id
        units.append({"id": unit_id, "tier": "A1.1", "sequence": unit_number, "title": unit_title, "lesson_ids": [lesson["id"] for lesson in unit_lessons], "review_lesson_id": unit_lessons[-1]["id"], "lessons": unit_lessons})
    value = {"schema_version": "1.0", "record_type": "german_a1_bootstrap_blueprint", "edition": "de-a1-v1", "language_code": "de", "status": "OUTLINE_ONLY", "source_population_id": population["population_id"], "source_population_sha256": _population_hash(population), "tiers": ["A1.1"], "units": units}
    validate_blueprint(value, population)
    return value


def validate_blueprint(value: dict[str, Any], population: dict[str, Any] | None = None) -> dict[str, Any]:
    validate_instance(value, "german-a1-blueprint-v1")
    population = population or json.loads(POPULATION_PATH.read_text(encoding="utf-8"))
    validate_population(population)
    if value["source_population_id"] != population["population_id"] or value["source_population_sha256"] != _population_hash(population):
        raise ValueError("German blueprint source population binding mismatch")
    if len(value["units"]) != 2 or [unit["sequence"] for unit in value["units"]] != [1, 2]:
        raise ValueError("German blueprint must contain two ordered units")
    nodes = {node["id"]: node for node in population["nodes"]}
    expected = {knowledge_graph_id("de", "A1.1", dimension) for dimension in DIMS}
    all_lessons = [lesson for unit in value["units"] for lesson in unit["lessons"]]
    if len(all_lessons) != 10 or len({lesson["id"] for lesson in all_lessons}) != 10:
        raise ValueError("German blueprint must contain ten unique lessons")
    introduced: set[str] = set()
    introduced_count: dict[str, int] = {node_id: 0 for node_id in expected}
    position = {lesson["id"]: index for index, lesson in enumerate(all_lessons)}
    for unit in value["units"]:
        expected_ids = [lesson["id"] for lesson in unit["lessons"]]
        if unit["lesson_ids"] != expected_ids or unit["review_lesson_id"] != expected_ids[-1]:
            raise ValueError(f"unit lesson links do not match: {unit['id']}")
        for lesson in unit["lessons"]:
            if lesson["unit_id"] != unit["id"] or lesson["sequence"] != unit["lessons"].index(lesson) + 1:
                raise ValueError(f"lesson placement mismatch: {lesson['id']}")
            if any(prerequisite not in position or position[prerequisite] >= position[lesson["id"]] for prerequisite in lesson["prerequisites"]):
                raise ValueError(f"forward or unknown lesson prerequisite: {lesson['id']}")
            if lesson["kind"] == "REVIEW" and lesson["sequence"] != 5:
                raise ValueError(f"only final lesson may be review: {lesson['id']}")
            for target in lesson["targets"]:
                node_id = target["node_id"]
                if node_id not in expected or node_id not in nodes or nodes[node_id]["tier"] != "A1.1" or nodes[node_id]["dimension"] != node_id.removeprefix("kg_de_a1_1_"):
                    raise ValueError(f"invalid German A1.1 target: {node_id}")
                if target["use"] == "INTRODUCE":
                    introduced_count[node_id] += 1
                    if node_id in introduced:
                        raise ValueError(f"target introduced more than once: {node_id}")
                    introduced.add(node_id)
                elif node_id not in introduced:
                    raise ValueError(f"target used before introduction: {node_id}")
                if lesson["kind"] == "REVIEW" and target["use"] != "REVIEW":
                    raise ValueError(f"review lesson has non-review target: {lesson['id']}")
    if introduced != expected or any(count != 1 for count in introduced_count.values()):
        raise ValueError("German A1.1 targets must each be introduced exactly once")
    return value


def write_blueprint(output: Path | None = None) -> Path:
    output = output or ROOT / course_path("de", "a1", "blueprint-v1.json")
    if output.exists():
        raise FileExistsError(f"refusing to overwrite immutable blueprint: {output}")
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(build(), ensure_ascii=False, sort_keys=True, indent=2) + "\n", encoding="utf-8")
    return output


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)
    write_parser = subparsers.add_parser("write")
    write_parser.add_argument("output", nargs="?", type=Path)
    validate_parser = subparsers.add_parser("validate")
    validate_parser.add_argument("blueprint", type=Path)
    args = parser.parse_args()
    if args.command == "write":
        print(write_blueprint(args.output))
    else:
        value = load_document(args.blueprint)
        validate_blueprint(value)
        print("PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
