from __future__ import annotations

from pathlib import Path

import pytest

from english_master.c1_curriculum_blueprint import DIMS, build, run, validate
from english_master.schema_validation import load_document

ROOT = Path(__file__).parents[1]
POPULATION_PATH = ROOT / "curriculum" / "a1-full" / "v1" / "m15-population.json"
BLUEPRINT_PATH = ROOT / "curriculum" / "c1-blueprint" / "m16-c1-blueprint.json"


def _population() -> dict:
    return load_document(POPULATION_PATH)


def _blueprint() -> tuple[dict, dict]:
    population = _population()
    return build(population), population


def test_builds_complete_outline_only_c1_blueprint() -> None:
    blueprint, population = _blueprint()
    validate(blueprint, population)

    assert blueprint["tiers"] == ["C1.1", "C1.2"]
    assert len(blueprint["units"]) == 10
    assert len(blueprint["lessons"]) == 50
    assert len(blueprint["unit_tests"]) == 10
    assert [unit["id"] for unit in blueprint["units"]] == [
        f"m16c1-v1-c1-u{number:02d}" for number in range(1, 11)
    ]
    assert all(unit["review_lesson_id"] == unit["lesson_ids"][-1] for unit in blueprint["units"])
    assert all(test["target_dimensions"] == list(DIMS) for test in blueprint["unit_tests"])


def test_committed_c1_blueprint_matches_builder_and_validates() -> None:
    population = _population()
    committed = load_document(BLUEPRINT_PATH)
    assert committed == build(population)
    validate(committed, population)


def test_all_c1_targets_are_resolved_introduced_once_and_reviewed() -> None:
    blueprint, population = _blueprint()
    validate(blueprint, population)
    expected = {
        f"kg_{tier.lower().replace('.', '_')}_{dimension}"
        for tier in ("C1.1", "C1.2")
        for dimension in DIMS
    }
    introduced = [
        target["node_id"]
        for lesson in blueprint["lessons"]
        for target in lesson["targets"]
        if target["use"] == "INTRODUCE"
    ]
    reviewed = {
        target["node_id"]
        for lesson in blueprint["lessons"]
        for target in lesson["targets"]
        if target["use"] == "REVIEW"
    }
    assert set(introduced) == expected
    assert len(introduced) == len(expected)
    assert reviewed == expected


@pytest.mark.parametrize(
    ("mutation", "message"),
    [
        (lambda value: value.__setitem__("source_population_id", "wrong"), "source population ID"),
        (lambda value: value.__setitem__("source_population_sha256", "0" * 64), "source population hash"),
        (lambda value: value["lessons"][0]["targets"][0].__setitem__("node_id", "kg_c1_2_grammar"), "tier/dimension"),
        (lambda value: value["lessons"][0]["targets"][0].__setitem__("dimension", "skills"), "tier/dimension"),
        (lambda value: value["lessons"][0]["targets"][0].__setitem__("use", "PRACTISE"), "introduction coverage"),
    ],
)
def test_rejects_source_and_target_drift(mutation, message: str) -> None:
    blueprint, population = _blueprint()
    mutation(blueprint)
    with pytest.raises(ValueError, match=message):
        validate(blueprint, population)


def test_rejects_invalid_entry_prerequisite_and_review_links() -> None:
    blueprint, population = _blueprint()
    blueprint["entry_prerequisite_node_ids"][0] = "kg_c1_1_grammar"
    with pytest.raises(ValueError, match="entry prerequisites"):
        validate(blueprint, population)

    blueprint, population = _blueprint()
    blueprint["units"][0]["review_lesson_id"] = blueprint["units"][0]["lesson_ids"][0]
    with pytest.raises(ValueError, match="review lesson must be last"):
        validate(blueprint, population)


def test_rejects_invalid_unit_test_and_prerequisite_order() -> None:
    blueprint, population = _blueprint()
    blueprint["unit_tests"][0]["assessed_lesson_ids"] = blueprint["unit_tests"][0]["assessed_lesson_ids"][:-1]
    with pytest.raises(ValueError, match="too short"):
        validate(blueprint, population)

    blueprint, population = _blueprint()
    blueprint["lessons"][0]["prerequisite_lesson_ids"] = [blueprint["lessons"][1]["id"]]
    with pytest.raises(ValueError, match="forward prerequisite|cycle"):
        validate(blueprint, population)


def test_rejects_prose_field_not_in_outline_contract() -> None:
    blueprint, population = _blueprint()
    blueprint["lessons"][0]["content_sections"] = [{"body": "not allowed"}]
    with pytest.raises(ValueError, match="Additional properties"):
        validate(blueprint, population)


def test_run_is_immutable_and_output_validates(tmp_path: Path) -> None:
    output = tmp_path / "m16-c1-blueprint.json"
    assert run(POPULATION_PATH, output) == output
    generated = load_document(output)
    validate(generated, _population())
    with pytest.raises(FileExistsError, match="refusing to overwrite"):
        run(POPULATION_PATH, output)


def test_validation_accepts_authored_titles_and_objectives() -> None:
    blueprint, population = _blueprint()
    blueprint["units"][0]["title"] = "An authored C1 planning title"
    blueprint["lessons"][0]["objectives"] = ["Use a valid, concise C1 planning objective."]
    validate(blueprint, population)
