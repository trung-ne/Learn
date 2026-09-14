from __future__ import annotations

from copy import deepcopy
import json
from pathlib import Path

import pytest

from english_master.german_a1_blueprint import build, validate_blueprint
from english_master.schema_validation import SchemaValidationError, validate_instance

ROOT = Path(__file__).parents[1]
BLUEPRINT = ROOT / "course" / "de" / "a1" / "blueprint-v1.json"


def test_german_blueprint_has_exact_outline_scope() -> None:
    value = json.loads(BLUEPRINT.read_text(encoding="utf-8"))
    validate_blueprint(value)
    validate_instance(value, "german-a1-blueprint-v1")
    assert value["language_code"] == "de"
    assert len(value["units"]) == 2
    assert sum(len(unit["lessons"]) for unit in value["units"]) == 10
    targets = {target["node_id"] for unit in value["units"] for lesson in unit["lessons"] for target in lesson["targets"]}
    assert targets == {f"kg_de_a1_1_{dimension}" for dimension in ("grammar", "vocabulary_senses", "functions", "pronunciation", "discourse", "pragmatics", "collocations", "lexical_chunks", "topics", "skills")}
    assert all("exercises" not in lesson and "content_sections" not in lesson for unit in value["units"] for lesson in unit["lessons"])


def test_german_blueprint_is_deterministic() -> None:
    assert build() == build()


@pytest.mark.parametrize("mutation", ["source_population_id", "source_population_sha256", "language_code"])
def test_german_blueprint_rejects_binding_drift(mutation: str) -> None:
    broken = deepcopy(build())
    broken[mutation] = "en" if mutation == "language_code" else "0" * (64 if "sha256" in mutation else 10)
    with pytest.raises((ValueError, SchemaValidationError)):
        validate_blueprint(broken)


def test_german_blueprint_rejects_cross_language_target() -> None:
    broken = deepcopy(build())
    broken["units"][0]["lessons"][0]["targets"][0]["node_id"] = "kg_en_a1_1_grammar"
    with pytest.raises((ValueError, SchemaValidationError)):
        validate_blueprint(broken)


def test_german_blueprint_rejects_use_before_introduction() -> None:
    broken = deepcopy(build())
    target = broken["units"][0]["lessons"][0]["targets"][0]
    target["use"] = "PRACTISE"
    with pytest.raises(ValueError, match="before introduction"):
        validate_blueprint(broken)


def test_existing_english_blueprint_remains_present() -> None:
    assert (ROOT / "curriculum" / "a1-full" / "v1" / "content-manifest.json").exists()
