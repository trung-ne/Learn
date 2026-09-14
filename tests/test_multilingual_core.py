from __future__ import annotations

import json
from copy import deepcopy
from pathlib import Path

import pytest

from english_master.assessment_mastery.multilingual import score_multilingual_submission
from english_master.language_profiles import course_path, data_path, knowledge_graph_id, language_profile
from english_master.lesson_generation.canonical import sha256_json
from english_master.multilingual_validation import validate_multilingual_taxonomy
from english_master.schema_validation import (
    SchemaValidationError,
    load_document,
    validate_instance,
)


ROOT = Path(__file__).resolve().parents[1]
PACKAGE_PATH = (
    ROOT / "curriculum" / "assessments" / "v1" / "runs"
    / "assessment_38118701d2db5edb1013b6584591b78bd3d697cd3d47367af8c05eebc261c1d3"
    / "packages" / "lesson-quiz-m16a1-v1-a1-u01-l01.json"
)


def _answer(item: dict[str, object]) -> object:
    contract = item["answer_contract"]
    assert isinstance(contract, dict)
    if "correct_answer" in contract:
        return contract["correct_answer"]
    if "acceptable_answers" in contract:
        return contract["acceptable_answers"][0]
    if "correct_order" in contract:
        return contract["correct_order"]
    return contract["pairs"]


def _de_package() -> dict[str, object]:
    package = deepcopy(load_document(PACKAGE_PATH))
    for item in package["items"]:
        item["concept_ids"] = [f"kg_de_{concept_id.removeprefix('kg_')}" for concept_id in item["concept_ids"]]
        item["item_sha256"] = sha256_json({key: value for key, value in item.items() if key != "item_sha256"})
    package["package_sha256"] = sha256_json({key: value for key, value in package.items() if key != "package_sha256"})
    return package


def _submission(package: dict[str, object]) -> dict[str, object]:
    submission: dict[str, object] = {
        "schema_version": "1.0",
        "record_type": "assessment_submission",
        "assessment_id": package["assessment_id"],
        "package_sha256": package["package_sha256"],
        "seen_at": "2026-09-14T12:00:00Z",
        "responses": [
            {"item_id": item["item_id"], "answer": _answer(item)}
            for item in package["items"]
        ],
    }
    submission["submission_sha256"] = sha256_json(submission)
    return submission


def _write(path: Path, value: object) -> None:
    path.write_text(json.dumps(value, ensure_ascii=False), encoding="utf-8")


def test_language_profiles_are_safe_and_namespaced() -> None:
    assert language_profile("en").display_name == "English"
    assert language_profile("de").display_name == "German"
    assert course_path("de", "a1", "blueprint.json") == Path("course/de/a1/blueprint.json")
    assert data_path("de", "learner-state", "local-01", "state.json") == Path("data/learner-state/de/local-01/state.json")
    assert knowledge_graph_id("de", "A1.1", "grammar") == "kg_de_a1_1_grammar"
    with pytest.raises(ValueError, match="unsupported"):
        language_profile("fr")
    with pytest.raises(ValueError, match="unsafe"):
        course_path("de", "../escape")


def test_multilingual_scorer_binds_package_submission_and_state_language(tmp_path: Path) -> None:
    package = _de_package()
    submission = _submission(package)
    package_path, submission_path, state_path = tmp_path / "package.json", tmp_path / "submission.json", tmp_path / "state.json"
    _write(package_path, {"schema_version": "1.0", "record_type": "multilingual_assessment_package", "language_code": "de", "assessment": package})
    _write(submission_path, {"schema_version": "1.0", "record_type": "multilingual_assessment_submission", "language_code": "de", "submission": submission})

    result = score_multilingual_submission(package_path=package_path, submission_path=submission_path, state_path=state_path)
    state = load_document(state_path)
    assert result["language_code"] == "de"
    assert result["score"] == 1.0
    assert state["language_code"] == "de"
    assert all(row["concept_id"].startswith("kg_de_") for row in state["concepts"])

    mismatched = load_document(submission_path)
    mismatched["language_code"] = "en"
    _write(submission_path, mismatched)
    with pytest.raises(ValueError, match="languages do not match"):
        score_multilingual_submission(package_path=package_path, submission_path=submission_path, state_path=state_path)


def test_taxonomy_language_and_source_scope_fail_closed() -> None:
    taxonomy = deepcopy(load_document(ROOT / "curriculum" / "taxonomy" / "taxonomy.json"))
    multilingual_taxonomy = {
        "schema_version": "1.0",
        "record_type": "multilingual_taxonomy",
        "target_language_code": "en",
        "learner_language_code": "vi",
        "taxonomy": taxonomy,
    }
    validate_multilingual_taxonomy(multilingual_taxonomy)

    multilingual_taxonomy["taxonomy"]["vocabulary_senses"][0]["language"] = "de"
    with pytest.raises(SchemaValidationError, match="taxonomy target language"):
        validate_multilingual_taxonomy(multilingual_taxonomy)

    registry = load_document(ROOT / "sources" / "registry.yaml")
    source_registry = {
        "schema_version": "1.0",
        "record_type": "multilingual_source_registry",
        "registry": registry,
        "language_scopes": [
            {"source_id": source["source_id"], "language_codes": ["en"]}
            for source in registry["sources"]
        ],
    }
    multilingual_taxonomy = {
        "schema_version": "1.0",
        "record_type": "multilingual_taxonomy",
        "target_language_code": "de",
        "learner_language_code": "vi",
        "taxonomy": deepcopy(load_document(ROOT / "curriculum" / "taxonomy" / "taxonomy.json")),
    }
    with pytest.raises(SchemaValidationError, match="does not support taxonomy language 'de'"):
        validate_multilingual_taxonomy(multilingual_taxonomy, source_registry)
