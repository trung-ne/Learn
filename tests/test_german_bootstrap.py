from __future__ import annotations

from copy import deepcopy

import pytest

from english_master.german_bootstrap import DIMENSIONS, TIERS, build_population, validate_population
from english_master.knowledge_graph.service import build_population as build_english_population
from english_master.schema_validation import SchemaValidationError, validate_instance


def test_german_population_is_language_bound_and_german_specific() -> None:
    population = build_population()
    validate_instance(population, "multilingual-knowledge-graph-population-v1")
    assert population["language_code"] == "de"
    assert len(population["nodes"]) == len(TIERS) * len(DIMENSIONS) == 120
    assert all(node["id"].startswith("kg_de_") for node in population["nodes"])
    assert any("Nominativ" in node["name"] or "Akkusativ" in node["name"] for node in population["nodes"])
    assert any("trennbare" in node["name"] for node in population["nodes"])
    assert any("Umlaute" in node["name"] for node in population["nodes"])


def test_german_graph_rejects_cross_language_prerequisite() -> None:
    population = build_population()
    broken = deepcopy(population)
    broken["nodes"][1]["prerequisites"] = ["kg_en_a1_1_grammar"]
    broken["nodes"][1]["dependency_edges"] = [{"source": "kg_en_a1_1_grammar", "target": broken["nodes"][1]["id"], "relation": "PREREQUISITE"}]
    with pytest.raises((ValueError, SchemaValidationError)):
        validate_population(broken)


def test_existing_english_population_is_unchanged() -> None:
    english = build_english_population()
    assert len(english["nodes"]) == 120
    assert all(node["id"].startswith("kg_") and not node["id"].startswith("kg_de_") for node in english["nodes"])
