from __future__ import annotations
import json
from pathlib import Path
import pytest
from english_master.adaptive_review.service import build_review_plan
from english_master.adaptive_review.state import load_state
from english_master.lesson_generation.canonical import sha256_json
from english_master.schema_validation import validate_instance

ROOT = Path(__file__).resolve().parents[1]
RUN = ROOT / "curriculum/assessments/v1/runs/assessment_38118701d2db5edb1013b6584591b78bd3d697cd3d47367af8c05eebc261c1d3"

def write(path: Path, value: object) -> None:
    path.write_text(json.dumps(value), encoding="utf-8")

def test_empty_state_plan_is_hash_bound_and_deterministic(tmp_path: Path) -> None:
    first = build_review_plan(assessment_run=RUN, state_path=tmp_path/"state.json", adaptive_state_path=tmp_path/"adaptive.json", lesson_id="m16a1-v1-a1-u01-l01", as_of="2026-09-14T12:00:00Z", output_path=tmp_path/"one.json")
    second_path = tmp_path/"two.json"
    second = build_review_plan(assessment_run=RUN, state_path=tmp_path/"state.json", adaptive_state_path=tmp_path/"adaptive.json", lesson_id="m16a1-v1-a1-u01-l01", as_of="2026-09-14T12:00:00Z", output_path=second_path)
    assert first == second
    validate_instance(first, "adaptive-review-plan-v1")
    assert first["plan_sha256"] == sha256_json({k:v for k,v in first.items() if k != "plan_sha256"})
    assert first["entries"][0]["reasons"] == ["NEW_LESSON"]

def test_plan_is_read_only_and_rejects_unknown_lesson(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="lesson not found"):
        build_review_plan(assessment_run=RUN, state_path=tmp_path/"state.json", adaptive_state_path=tmp_path/"adaptive.json", lesson_id="missing", as_of="2026-09-14T12:00:00Z", output_path=tmp_path/"plan.json")
    assert not (tmp_path/"adaptive.json").exists()

def test_adaptive_state_schema_loads_sorted_records(tmp_path: Path) -> None:
    state = [{"concept_id":"kg_a1_1_functions","interval_index":0,"last_reviewed_at":"2026-09-14T12:00:00Z","last_mistake_at":None,"next_review":"2026-09-15T12:00:00Z"}]
    write(tmp_path/"adaptive.json", state)
    assert load_state(tmp_path/"adaptive.json") == state
