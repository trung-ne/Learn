from __future__ import annotations

from copy import deepcopy
import json
import subprocess
import sys
from pathlib import Path

import pytest

from english_master.schema_validation import (
    SchemaValidationError,
    can_cite_for_taxonomy,
    load_json,
    load_source_registry,
    validate_coverage_matrix_collection,
    validate_instance,
    validate_taxonomy_collection,
    validation_issues,
)

ROOT = Path(__file__).parents[1]
TAXONOMY_PATH = ROOT / "curriculum" / "taxonomy" / "taxonomy.json"
COVERAGE_PATH = ROOT / "curriculum" / "taxonomy" / "coverage-matrix.json"


@pytest.fixture
def taxonomy() -> dict[str, object]:
    return load_json(TAXONOMY_PATH)


def test_committed_taxonomy_collection_is_valid(taxonomy: dict[str, object]) -> None:
    validate_taxonomy_collection(taxonomy)


def test_taxonomy_citation_respects_reference_only_status() -> None:
    registry = load_source_registry(ROOT / "sources" / "registry.yaml")

    assert can_cite_for_taxonomy(registry, "src_cefr_companion_volume")
    assert not can_cite_for_taxonomy(registry, "src_english_profile_evp")
    assert not can_cite_for_taxonomy(registry, "src_not_registered")


def test_committed_coverage_matrix_is_valid_and_complete() -> None:
    matrix = load_json(COVERAGE_PATH)

    validate_coverage_matrix_collection(matrix)
    assert [row["cefr_range"] for row in matrix["rows"]] == [
        "A1.1-A1.2",
        "A2.1-A2.2",
        "B1.1-B1.2",
        "B2.1-B2.2",
        "C1.1-C1.2",
        "C2.1-C2.2",
    ]


def test_internal_levels_are_complete_and_explicitly_not_official(taxonomy: dict[str, object]) -> None:
    cefr_model = taxonomy["cefr_model"]

    assert cefr_model["internal_levels"] == [
        "A1.1", "A1.2", "A2.1", "A2.2", "B1.1", "B1.2",
        "B2.1", "B2.2", "C1.1", "C1.2", "C2.1", "C2.2",
    ]
    assert "not official CEFR levels" in cefr_model["subdivision_notice"]


def test_every_required_taxonomy_dimension_has_a_representative_concept(
    taxonomy: dict[str, object],
) -> None:
    concepts = taxonomy["concepts"]
    represented_types = {concept["type"] for concept in concepts}
    skill_subtypes = {concept.get("subtype") for concept in concepts if concept["type"] == "skill"}
    pronunciation_subtypes = {
        concept.get("subtype") for concept in concepts if concept["type"] == "pronunciation"
    }

    assert represented_types == {
        "skill", "grammar", "collocation", "lexical_chunk", "pronunciation",
        "communicative_function", "topic", "discourse", "pragmatics",
        "assessment_capability",
    }
    assert skill_subtypes == {
        "listening", "spoken_production", "spoken_interaction", "reading",
        "written_production", "mediation",
    }
    assert pronunciation_subtypes == {
        "phonemes", "minimal_pairs", "syllables", "word_stress", "sentence_stress",
        "weak_forms", "linking", "connected_speech", "rhythm", "intonation",
    }


def test_nested_records_conform_to_their_individual_schemas(taxonomy: dict[str, object]) -> None:
    for concept in taxonomy["concepts"]:
        validate_instance(concept, "taxonomy-concept")
    for sense in taxonomy["vocabulary_senses"]:
        validate_instance(sense, "taxonomy-vocabulary-sense")
    for annotation in taxonomy["vietnamese_learner_annotations"]:
        validate_instance(annotation, "vietnamese-learner-annotation")


def test_duplicate_concept_id_is_rejected(taxonomy: dict[str, object]) -> None:
    invalid = deepcopy(taxonomy)
    invalid["concepts"].append(deepcopy(invalid["concepts"][0]))

    issues = validation_issues(invalid, "taxonomy")

    assert any("duplicate id" in issue.message for issue in issues)


def test_unknown_prerequisite_and_relationship_are_rejected(taxonomy: dict[str, object]) -> None:
    invalid = deepcopy(taxonomy)
    invalid["concepts"][0]["prerequisites"] = ["concept_missing"]
    invalid["concepts"][0]["related_concepts"] = [
        {"type": "supports", "target_id": "concept_also_missing"}
    ]

    issues = validation_issues(invalid, "taxonomy")

    assert any("unknown concept prerequisite" in issue.message for issue in issues)
    assert any("unknown related concept" in issue.message for issue in issues)


def test_prerequisite_cycle_is_rejected(taxonomy: dict[str, object]) -> None:
    invalid = deepcopy(taxonomy)
    concepts = {concept["id"]: concept for concept in invalid["concepts"]}
    concepts["concept_present_simple"]["prerequisites"] = ["concept_past_simple"]

    issues = validation_issues(invalid, "taxonomy")

    assert any("prerequisite cycle detected" in issue.message for issue in issues)
    with pytest.raises(SchemaValidationError):
        validate_taxonomy_collection(invalid)


def test_vocabulary_sense_identity_and_references_are_enforced(taxonomy: dict[str, object]) -> None:
    invalid = deepcopy(taxonomy)
    invalid["vocabulary_senses"][0]["id"] = "vocab_en_run_099"
    invalid["vocabulary_senses"][0]["relationships"][0]["target_id"] = "vocab_en_absent_001"
    invalid["vocabulary_senses"][0]["prerequisites"] = ["concept_absent"]

    issues = validation_issues(invalid, "taxonomy")

    assert any("sense ID must be 'vocab_en_run_001'" in issue.message for issue in issues)
    assert any("unknown vocabulary sense" in issue.message for issue in issues)
    assert any("unknown concept prerequisite" in issue.message for issue in issues)


def test_vietnamese_annotation_target_and_claim_kind_are_enforced(
    taxonomy: dict[str, object],
) -> None:
    invalid_target = deepcopy(taxonomy)
    invalid_target["vietnamese_learner_annotations"][0]["target_id"] = "concept_absent"
    assert any(
        "unknown concept target" in issue.message
        for issue in validation_issues(invalid_target, "taxonomy")
    )

    invalid_kind = deepcopy(taxonomy["vietnamese_learner_annotations"][0])
    invalid_kind["evidence_or_reference"][0]["kind"] = "PEDAGOGICAL_OBSERVATION"
    issues = validation_issues(invalid_kind, "vietnamese-learner-annotation")
    assert issues


def test_coverage_matrix_rejects_duplicate_and_missing_range() -> None:
    invalid = load_json(COVERAGE_PATH)
    invalid["rows"][5] = deepcopy(invalid["rows"][0])

    issues = validation_issues(invalid, "coverage-matrix")

    assert any("duplicate cefr_range" in issue.message for issue in issues)
    assert any("missing CEFR coverage ranges: C2.1-C2.2" in issue.message for issue in issues)


@pytest.mark.parametrize(
    ("schema_name", "path"),
    [("taxonomy", TAXONOMY_PATH), ("coverage-matrix", COVERAGE_PATH)],
)
def test_cli_validates_m2_collections(schema_name: str, path: Path) -> None:
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "english_master.schema_validation",
            "--schema",
            schema_name,
            str(path),
        ],
        check=False,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0, result.stderr
    assert "VALID" in result.stdout


def test_cli_rejects_semantically_invalid_taxonomy(
    taxonomy: dict[str, object], tmp_path: Path
) -> None:
    invalid = deepcopy(taxonomy)
    invalid["concepts"][0]["prerequisites"] = ["concept_missing"]
    path = tmp_path / "invalid-taxonomy.json"
    path.write_text(json.dumps(invalid), encoding="utf-8")

    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "english_master.schema_validation",
            "--schema",
            "taxonomy",
            str(path),
        ],
        check=False,
        capture_output=True,
        text=True,
    )

    assert result.returncode != 0
    assert "unknown concept prerequisite" in result.stderr
