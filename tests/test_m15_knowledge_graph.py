import json
import pytest
from english_master.knowledge_graph.service import DIMENSIONS, TIERS, build_population, run, validate_population


def test_population_has_concrete_complete_coverage_and_chain():
    population = build_population()
    assert len(population["nodes"]) == 120
    assert {n["tier"] for n in population["nodes"]} == set(TIERS)
    assert {n["dimension"] for n in population["nodes"]} == set(DIMENSIONS)
    assert all("foundation" not in n["name"] for n in population["nodes"])
    by_name = {n["name"]: n for n in population["nodes"]}
    assert [by_name[x]["id"] for x in ("present simple", "adverbs of frequency", "daily routines", "discussing habits")] == [
        "kg_a1_1_grammar", "kg_a1_1_vocabulary_senses", "kg_a1_1_topics", "kg_a1_1_functions"
    ]
    for source, target in zip(("present simple", "adverbs of frequency", "daily routines"), ("adverbs of frequency", "daily routines", "discussing habits")):
        assert {e["source"] for e in by_name[target]["dependency_edges"]} >= {by_name[source]["id"]}


def test_population_is_deterministic_and_tamper_detecting():
    first = build_population()
    assert first == build_population()
    altered = json.loads(json.dumps(first))
    altered["nodes"][0]["description"] = "tampered"
    with pytest.raises(ValueError):
        validate_population(altered)


def test_run_refuses_overwrite(tmp_path):
    output = tmp_path / "population.json"
    run(output)
    assert output.exists()
    with pytest.raises(FileExistsError):
        run(output)
    assert json.loads(output.read_text(encoding="utf-8"))["population_id"].startswith("kgpop_")
