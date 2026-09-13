from __future__ import annotations

import json
from collections import Counter
from copy import deepcopy
from pathlib import Path

import pytest

from english_master.assessment_mastery.learner_state import score_submission
from english_master.assessment_mastery.service import POLICY_VERSION, build_run, verify_run
from english_master.lesson_generation.canonical import sha256_json
from english_master.schema_validation import SchemaValidationError, load_document, validate_instance

ROOT = Path(__file__).resolve().parents[1]
REQUEST = ROOT / "curriculum" / "assessments" / "v1" / "request.json"
RUN = ROOT / "curriculum" / "assessments" / "v1" / "runs" / "assessment_38118701d2db5edb1013b6584591b78bd3d697cd3d47367af8c05eebc261c1d3"


def _package(name: str) -> Path:
    return RUN / "packages" / name


def _answer(item: dict[str, object]) -> object:
    contract = item["answer_contract"]
    assert isinstance(contract, dict)
    for key in ("correct_answer", "acceptable_answers", "correct_order", "pairs"):
        if key in contract:
            value = contract[key]
            return value[0] if key == "acceptable_answers" else value
    raise AssertionError("missing answer contract")


def _submission(package: dict[str, object], seen_at: str, *, answers: list[object] | None = None) -> dict[str, object]:
    items = package["items"]
    assert isinstance(items, list)
    values = answers if answers is not None else [_answer(item) for item in items]
    value: dict[str, object] = {
        "schema_version": "1.0", "record_type": "assessment_submission",
        "assessment_id": package["assessment_id"], "package_sha256": package["package_sha256"],
        "seen_at": seen_at,
        "responses": [{"item_id": item["item_id"], "answer": answer} for item, answer in zip(items, values, strict=True)],
    }
    value["submission_sha256"] = sha256_json(value)
    return value


def _write(path: Path, value: object) -> None:
    path.write_text(json.dumps(value, ensure_ascii=False), encoding="utf-8")


def test_committed_run_reverifies_all_sources_and_packages() -> None:
    result = verify_run(request_path=REQUEST, run_dir=RUN)
    assert result == {
        "result": "PASS", "run_id": RUN.name,
        "manifest_sha256": load_document(RUN / "manifest.json")["manifest_sha256"],
        "package_count": 367,
    }


def test_manifest_has_exact_closed_inventory_and_source_bindings() -> None:
    manifest = load_document(RUN / "manifest.json")
    validate_instance(manifest, "assessment-run-manifest-v1")
    assert manifest["policy_version"] == POLICY_VERSION
    assert manifest["content_status"] == "UNREVIEWED"
    assert manifest["counts"] == {"lesson_quizzes": 300, "unit_tests": 60, "level_tests": 6, "placement_packages": 1, "packages": 367}
    assert Counter(row["assessment_type"] for row in manifest["package_inventory"]) == {"LESSON_QUIZ": 300, "UNIT_TEST": 60, "LEVEL_TEST": 6, "PLACEMENT": 1}
    assert len(manifest["source_inputs"]) == 6
    assert len({row["run_manifest_sha256"] for row in manifest["source_inputs"]}) == 6


def test_packages_are_objective_no_media_and_scope_complete() -> None:
    manifest = load_document(RUN / "manifest.json")
    eligible = {"multiple_choice", "fill_blank", "matching", "ordering", "reading", "listening"}
    for entry in manifest["package_inventory"]:
        package = load_document(RUN / entry["path"])
        assert package["content_status"] == "UNREVIEWED"
        assert package["package_sha256"] == entry["package_sha256"]
        assert all(item["item_type"] in eligible and item["media_required"] is False for item in package["items"])
        assert all(item["concept_ids"] and item["target_ids"] and item["target_dimensions"] for item in package["items"])
        if package["assessment_type"] == "UNIT_TEST":
            assert len(package["items"]) == 10
            assert {item["source"]["lesson_id"] for item in package["items"]} == set(package["scope"]["lesson_ids"])
        elif package["assessment_type"] == "LEVEL_TEST":
            assert len(package["items"]) == 20
            assert {item["source"]["unit_id"] for item in package["items"]} == set(package["scope"]["unit_ids"])


def test_placement_has_two_distinct_lessons_per_tier() -> None:
    package = load_document(_package("placement-a1-c2.json"))
    by_tier: dict[str, list[dict[str, object]]] = {}
    for item in package["items"]:
        by_tier.setdefault(item["source"]["tier"], []).append(item)
    assert len(by_tier) == 12
    assert all(len(items) == 2 and len({item["source"]["lesson_id"] for item in items}) == 2 for items in by_tier.values())


def test_request_and_schema_reject_drift_and_extra_state_keys() -> None:
    request = load_document(REQUEST)
    request["levels"][0]["run_dir"] += "-drift"
    with pytest.raises(ValueError, match="hash mismatch"):
        from english_master.assessment_mastery.service import _validate_request
        _validate_request(request)
    with pytest.raises(SchemaValidationError):
        validate_instance([{"concept_id": "kg_a1_1_functions", "attempts": 1, "correct": 1, "incorrect": 0, "mastery": 1.0, "last_seen": "2026-09-13T00:00:00Z", "next_review": "2026-09-16T00:00:00Z", "learner_id": "forbidden"}], "learner-concept-state-v1")


def test_build_is_no_overwrite(tmp_path: Path) -> None:
    manifest = build_run(request_path=REQUEST, output_root=tmp_path)
    with pytest.raises(FileExistsError, match="overwrite"):
        build_run(request_path=REQUEST, output_root=tmp_path)
    assert (tmp_path / manifest["run_id"] / "manifest.json").is_file()


def test_complete_correct_submission_initializes_exact_seven_key_state(tmp_path: Path) -> None:
    package_path = _package("lesson-quiz-m16a1-v1-a1-u01-l01.json")
    package = load_document(package_path)
    submission_path, state_path = tmp_path / "submission.json", tmp_path / "state.json"
    _write(submission_path, _submission(package, "2026-09-13T12:00:00Z"))
    result = score_submission(package_path=package_path, submission_path=submission_path, state_path=state_path)
    state = json.loads(state_path.read_text(encoding="utf-8"))
    assert result["score"] == 1.0
    assert [row["concept_id"] for row in state] == sorted(row["concept_id"] for row in state)
    assert all(set(row) == {"concept_id", "attempts", "correct", "incorrect", "mastery", "last_seen", "next_review"} for row in state)
    assert all(row["attempts"] == row["correct"] + row["incorrect"] and row["mastery"] == 1.0 for row in state)
    assert all(row["next_review"] == "2026-09-16T12:00:00Z" for row in state)


def test_successive_updates_apply_review_schedule(tmp_path: Path) -> None:
    package_path = _package("lesson-quiz-m16a1-v1-a1-u01-l01.json")
    package = load_document(package_path)
    submission_path, state_path = tmp_path / "submission.json", tmp_path / "state.json"
    _write(submission_path, _submission(package, "2026-09-13T12:00:00Z"))
    score_submission(package_path=package_path, submission_path=submission_path, state_path=state_path)
    wrong = ["definitely wrong" for _ in package["items"]]
    _write(submission_path, _submission(package, "2026-09-14T12:00:00Z", answers=wrong))
    result = score_submission(package_path=package_path, submission_path=submission_path, state_path=state_path)
    assert result["score"] == 0.0
    state = json.loads(state_path.read_text(encoding="utf-8"))
    assert all(row["mastery"] == 0.5 and row["next_review"] == "2026-09-14T12:00:00Z" for row in state)


def test_text_order_and_matching_answer_forms(tmp_path: Path) -> None:
    manifest = load_document(RUN / "manifest.json")
    wanted = {"fill_blank", "ordering", "matching"}
    chosen: dict[str, tuple[Path, dict[str, object]]] = {}
    for entry in manifest["package_inventory"]:
        if entry["assessment_type"] != "LESSON_QUIZ":
            continue
        path = RUN / entry["path"]
        package = load_document(path)
        for item in package["items"]:
            if item["item_type"] in wanted and item["item_type"] not in chosen:
                chosen[item["item_type"]] = (path, package)
        if set(chosen) == wanted:
            break
    for index, (kind, (path, package)) in enumerate(sorted(chosen.items())):
        answers = [_answer(item) for item in package["items"]]
        target_index = next(i for i, item in enumerate(package["items"]) if item["item_type"] == kind)
        answer = answers[target_index]
        if kind == "fill_blank":
            answers[target_index] = f"  {str(answer).swapcase()}  "
        elif kind == "matching":
            answers[target_index] = list(reversed(answer))
        submission = _submission(package, f"2026-09-{20 + index:02d}T00:00:00Z", answers=answers)
        submission_path = tmp_path / f"{kind}.json"
        _write(submission_path, submission)
        assert score_submission(package_path=path, submission_path=submission_path, state_path=tmp_path / f"{kind}-state.json")["score"] == 1.0


def test_duplicate_and_incomplete_submissions_roll_back(tmp_path: Path) -> None:
    package_path = _package("lesson-quiz-m16a1-v1-a1-u01-l01.json")
    package = load_document(package_path)
    state_path = tmp_path / "state.json"
    original = [{"concept_id": "kg_a1_1_functions", "attempts": 1, "correct": 1, "incorrect": 0, "mastery": 1.0, "last_seen": "2026-09-10T00:00:00Z", "next_review": "2026-09-13T00:00:00Z"}]
    _write(state_path, original)
    for mode in ("duplicate", "incomplete"):
        submission = _submission(package, "2026-09-13T00:00:00Z")
        if mode == "duplicate":
            submission["responses"].append(deepcopy(submission["responses"][0]))
        else:
            submission["responses"].pop()
        submission["submission_sha256"] = sha256_json({key: value for key, value in submission.items() if key != "submission_sha256"})
        submission_path = tmp_path / f"{mode}.json"
        _write(submission_path, submission)
        with pytest.raises((SchemaValidationError, ValueError)):
            score_submission(package_path=package_path, submission_path=submission_path, state_path=state_path)
        assert json.loads(state_path.read_text(encoding="utf-8")) == original


def test_atomic_replace_failure_preserves_existing_state(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    package_path = _package("lesson-quiz-m16a1-v1-a1-u01-l01.json")
    package = load_document(package_path)
    submission_path, state_path = tmp_path / "submission.json", tmp_path / "state.json"
    original = [{"concept_id": "kg_a1_1_functions", "attempts": 1, "correct": 1, "incorrect": 0, "mastery": 1.0, "last_seen": "2026-09-10T00:00:00Z", "next_review": "2026-09-13T00:00:00Z"}]
    _write(state_path, original)
    _write(submission_path, _submission(package, "2026-09-13T00:00:00Z"))
    monkeypatch.setattr("english_master.assessment_mastery.learner_state.os.replace", lambda *_: (_ for _ in ()).throw(OSError("replace failed")))
    with pytest.raises(OSError, match="replace failed"):
        score_submission(package_path=package_path, submission_path=submission_path, state_path=state_path)
    assert json.loads(state_path.read_text(encoding="utf-8")) == original
    assert not list(tmp_path.glob("*.tmp"))


def test_placement_returns_first_tier_below_threshold(tmp_path: Path) -> None:
    package_path = _package("placement-a1-c2.json")
    package = load_document(package_path)
    answers = [_answer(item) if item["source"]["tier"] == "A1.1" else "wrong" for item in package["items"]]
    submission_path = tmp_path / "placement.json"
    _write(submission_path, _submission(package, "2026-09-13T00:00:00Z", answers=answers))
    result = score_submission(package_path=package_path, submission_path=submission_path, state_path=tmp_path / "state.json")
    assert result["suggested_start_tier"] == "A1.2"
    assert result["tier_scores"][0] == {"tier": "A1.1", "correct": 2, "total": 2, "met_threshold": True}
