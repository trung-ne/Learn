from __future__ import annotations

import json
import subprocess
import sys
from copy import deepcopy
from pathlib import Path

import pytest

from english_master.curriculum_validate import main
from english_master.curriculum_validation import (
    CurriculumBundle,
    deterministic_topological_order,
    load_bundle,
    validate_bundle,
)
from english_master.schema_validation import validation_issues

ROOT = Path(__file__).resolve().parents[1]
STRUCTURE = ROOT / "curriculum" / "structure.json"


@pytest.fixture(scope="module")
def valid_bundle() -> CurriculumBundle:
    return load_bundle(STRUCTURE)


def changed(bundle: CurriculumBundle, *, structure=None, graph=None, coverage=None, taxonomy=None) -> CurriculumBundle:
    return CurriculumBundle(
        structure=structure if structure is not None else deepcopy(bundle.structure),
        graph=graph if graph is not None else deepcopy(bundle.graph),
        coverage=coverage if coverage is not None else deepcopy(bundle.coverage),
        taxonomy=taxonomy if taxonomy is not None else deepcopy(bundle.taxonomy),
        paths=bundle.paths,
    )


def codes(bundle: CurriculumBundle) -> set[str]:
    return {issue.code for issue in validate_bundle(bundle).issues}


def test_committed_curriculum_bundle_is_valid_and_complete(valid_bundle: CurriculumBundle) -> None:
    result = validate_bundle(valid_bundle)
    assert result.valid, result.issues
    assert result.report["status"] == "VALID"
    assert result.report["counts"] == {
        "levels": 6,
        "tiers": 12,
        "units": 12,
        "lessons": 24,
        "reviews": 12,
        "graph_nodes": 77,
        "graph_edges": len(valid_bundle.graph["edges"]),
        "coverage_dimensions": 16,
    }
    assert result.report["topological_order"] == valid_bundle.graph["topological_order"]


def test_twelve_internal_tiers_and_globally_numbered_units_avoid_collisions(valid_bundle: CurriculumBundle) -> None:
    tiers = [tier for level in valid_bundle.structure["levels"] for tier in level["tiers"]]
    assert [tier["sequence"] for tier in tiers] == list(range(1, 13))
    assert all(tier["official_status"] == "INTERNAL_CURRICULUM_SUBDIVISION" for tier in tiers)
    assert [unit["global_unit_number"] for unit in valid_bundle.structure["units"]] == list(range(1, 13))
    lesson_ids = [lesson["id"] for lesson in valid_bundle.structure["lessons"]]
    assert len(lesson_ids) == len(set(lesson_ids))
    assert "A1-U01-L01" in lesson_ids and "A1-U02-L01" in lesson_ids


def test_outline_contract_has_required_reference_families(valid_bundle: CurriculumBundle) -> None:
    required = {"grammar", "vocabulary", "functions", "pronunciation", "prerequisites", "review_of", "lesson_kind", "status"}
    assert all(required <= lesson.keys() for lesson in valid_bundle.structure["lessons"])
    assert any(lesson["grammar"] for lesson in valid_bundle.structure["lessons"])
    assert any(lesson["vocabulary"] for lesson in valid_bundle.structure["lessons"])
    assert any(lesson["functions"] for lesson in valid_bundle.structure["lessons"])
    assert any(lesson["pronunciation"] for lesson in valid_bundle.structure["lessons"])


def test_full_lesson_content_and_exercises_are_rejected_by_outline_schema(valid_bundle: CurriculumBundle) -> None:
    lesson = deepcopy(valid_bundle.structure["lessons"][0])
    lesson["content_sections"] = [{"body_text": "This would be M6 prose."}]
    lesson["exercises"] = ["ex_A1-U01-L01_001"]
    messages = " ".join(issue.message for issue in validation_issues(lesson, "curriculum-lesson-outline"))
    assert "Additional properties are not allowed" in messages
    assert "content_sections" in messages and "exercises" in messages


def test_duplicate_and_parent_link_failures_are_reported(valid_bundle: CurriculumBundle) -> None:
    structure = deepcopy(valid_bundle.structure)
    structure["lessons"].append(deepcopy(structure["lessons"][0]))
    assert "DUPLICATE_ID" in codes(changed(valid_bundle, structure=structure))
    structure = deepcopy(valid_bundle.structure)
    structure["lessons"][0]["unit_id"] = structure["units"][1]["id"]
    assert {"LESSON_PARENT_MISMATCH", "LESSON_PARENT_COUNT"} & codes(changed(valid_bundle, structure=structure))


def test_missing_self_and_later_lesson_prerequisites_fail(valid_bundle: CurriculumBundle) -> None:
    structure = deepcopy(valid_bundle.structure)
    structure["lessons"][0]["prerequisites"] = ["A1-U99-L99"]
    assert "MISSING_PREREQUISITE" in codes(changed(valid_bundle, structure=structure))
    structure = deepcopy(valid_bundle.structure)
    structure["lessons"][1]["prerequisites"] = [structure["lessons"][1]["id"]]
    assert "SELF_DEPENDENCY" in codes(changed(valid_bundle, structure=structure))
    structure = deepcopy(valid_bundle.structure)
    structure["lessons"][0]["prerequisites"] = [structure["lessons"][1]["id"]]
    assert "PREREQUISITE_NOT_EARLIER" in codes(changed(valid_bundle, structure=structure))


def test_ordering_cycle_and_duplicate_graph_nodes_fail(valid_bundle: CurriculumBundle) -> None:
    graph = deepcopy(valid_bundle.graph)
    graph["edges"].append({"from": "C2-U12-L02", "to": "A1-U01-L01", "type": "lesson_prerequisite"})
    assert "PREREQUISITE_CYCLE" in codes(changed(valid_bundle, graph=graph))
    graph = deepcopy(valid_bundle.graph)
    graph["nodes"].append(deepcopy(graph["nodes"][0]))
    assert "DUPLICATE_ID" in codes(changed(valid_bundle, graph=graph))


def test_related_edges_are_explicitly_non_ordering() -> None:
    nodes = [
        {"id": "concept_a", "sequence_key": "01"},
        {"id": "concept_b", "sequence_key": "02"},
    ]
    related_cycle = [
        {"from": "concept_a", "to": "concept_b", "type": "related_non_ordering"},
        {"from": "concept_b", "to": "concept_a", "type": "related_non_ordering"},
    ]
    order, cyclic = deterministic_topological_order(nodes, related_cycle)
    assert order == ("concept_a", "concept_b")
    assert cyclic == ()


def test_taxonomy_reference_type_status_and_prerequisite_gates(valid_bundle: CurriculumBundle) -> None:
    structure = deepcopy(valid_bundle.structure)
    structure["lessons"][0]["grammar"] = ["concept_listening"]
    assert "TAXONOMY_TYPE_MISMATCH" in codes(changed(valid_bundle, structure=structure))
    taxonomy = deepcopy(valid_bundle.taxonomy)
    taxonomy["concepts"][0]["status"] = "APPROVED"
    assert "UNAUTHORIZED_DEPENDENCY" in codes(changed(valid_bundle, taxonomy=taxonomy))
    structure = deepcopy(valid_bundle.structure)
    structure["lessons"][0]["taxonomy_concepts"].append("concept_past_perfect")
    assert {"CEFR_REFERENCE_TOO_EARLY", "TAXONOMY_PREREQUISITE_NOT_EARLIER"} <= codes(changed(valid_bundle, structure=structure))


def test_draft_taxonomy_has_explicit_m6_blocking_review_gate(valid_bundle: CurriculumBundle) -> None:
    gate = valid_bundle.structure["taxonomy_dependency"]
    assert gate["accepted_record_statuses"] == ["DRAFT"]
    assert gate["approved_for_outline_planning_only"] is True
    assert gate["blocks_content_generation"] is True
    structure = deepcopy(valid_bundle.structure)
    structure["taxonomy_dependency"]["blocks_content_generation"] = False
    assert {issue.code for issue in validate_bundle(changed(valid_bundle, structure=structure)).issues} >= {"SCHEMA_INVALID", "DRAFT_REVIEW_GATE"}


def test_review_before_introduction_and_unresolved_review_fail(valid_bundle: CurriculumBundle) -> None:
    structure = deepcopy(valid_bundle.structure)
    structure["lessons"][0]["review_of"] = [structure["lessons"][1]["id"]]
    assert "REVIEW_BEFORE_INTRODUCTION" in codes(changed(valid_bundle, structure=structure))
    structure = deepcopy(valid_bundle.structure)
    structure["reviews"][0]["review_concepts"].append("concept_past_perfect")
    assert "REVIEW_BEFORE_INTRODUCTION" in codes(changed(valid_bundle, structure=structure))
    structure = deepcopy(valid_bundle.structure)
    structure["reviews"][0]["review_concepts"].append("concept_unknown")
    assert "UNRESOLVED_REVIEW" in codes(changed(valid_bundle, structure=structure))


def test_coverage_gaps_unknown_nodes_and_ordering_fail(valid_bundle: CurriculumBundle) -> None:
    coverage = deepcopy(valid_bundle.coverage)
    coverage["dimensions"].pop()
    assert "COVERAGE_GAP" in codes(changed(valid_bundle, coverage=coverage))
    coverage = deepcopy(valid_bundle.coverage)
    coverage["dimensions"][0]["developed_at"] = [coverage["dimensions"][0]["introduced_at"]]
    assert "COVERAGE_ORDER" in codes(changed(valid_bundle, coverage=coverage))


def test_graph_serialization_and_topology_are_deterministic(valid_bundle: CurriculumBundle) -> None:
    first = validate_bundle(valid_bundle)
    second = validate_bundle(load_bundle(STRUCTURE))
    assert first.report == second.report
    graph = deepcopy(valid_bundle.graph)
    graph["nodes"] = list(reversed(graph["nodes"]))
    assert "NONDETERMINISTIC_SERIALIZATION" in codes(changed(valid_bundle, graph=graph))


def test_cli_strict_taxonomy_gate_fails_for_draft_taxonomy() -> None:
    assert main(["--require-approved-taxonomy", str(STRUCTURE)]) == 1


def test_cli_exit_codes_report_and_subprocess_offline(valid_bundle: CurriculumBundle, tmp_path: Path) -> None:
    report = tmp_path / "report.json"
    assert main([str(STRUCTURE), "--report", str(report)]) == 0
    payload = json.loads(report.read_text(encoding="utf-8"))
    assert payload["status"] == "VALID"
    assert payload["validated_artifacts"] == ["structure.json", "prerequisite_graph.json", "coverage-roadmap.json", "taxonomy/taxonomy.json"]
    completed = subprocess.run(
        [sys.executable, "-m", "english_master.curriculum_validate", str(STRUCTURE)],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    assert completed.returncode == 0
    assert "VALID" in completed.stdout
    invalid = tmp_path / "invalid-structure.json"
    payload = deepcopy(valid_bundle.structure)
    payload["levels"].pop()
    invalid.write_text(json.dumps(payload), encoding="utf-8")
    completed = subprocess.run(
        [sys.executable, "-m", "english_master.curriculum_validate", str(invalid), "--graph", str(valid_bundle.paths[1]), "--coverage", str(valid_bundle.paths[2]), "--taxonomy", str(valid_bundle.paths[3])],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    assert completed.returncode == 1
    assert "INVALID" in completed.stderr
