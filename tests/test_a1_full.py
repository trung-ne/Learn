from __future__ import annotations

import copy
import hashlib
import json
import shutil
from pathlib import Path

import pytest

from english_master.a1_full import service
from english_master.a1_full.authoring import compile_authoring_source, seed_authoring_source
from english_master.a1_full.service import audit_full_a1, build_full_a1, sample_full_a1, verify_full_a1
from english_master.lesson_generation.canonical import sha256_json

ROOT = Path(__file__).parents[1]
COMMITTED = ROOT / "curriculum" / "a1-full" / "v1"
BUILT_AT = "2026-09-12T12:00:00Z"


def _write(path: Path, value: dict) -> None:
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _copy_sources(tmp_path: Path) -> Path:
    source = tmp_path / "source"
    source.mkdir(parents=True)
    shutil.copy2(COMMITTED / "m15-population.json", source / "m15-population.json")
    shutil.copy2(COMMITTED / "m16-blueprint.json", source / "m16-blueprint.json")
    shutil.copy2(COMMITTED / "allocation.json", source / "allocation.json")
    shutil.copy2(COMMITTED / "content-manifest.json", source / "content-manifest.json")
    shutil.copytree(COMMITTED / "units", source / "units")
    return source


def _paths(source: Path) -> dict[str, Path]:
    return {
        "population_path": source / "m15-population.json",
        "blueprint_path": source / "m16-blueprint.json",
        "allocation_path": source / "allocation.json",
        "content_manifest_path": source / "content-manifest.json",
    }


def _build(tmp_path: Path, source: Path) -> Path:
    return build_full_a1(**_paths(source), output_root=tmp_path / "runs", built_at=BUILT_AT)


def _refresh_content_manifest(source: Path) -> None:
    manifest = json.loads((source / "content-manifest.json").read_text(encoding="utf-8"))
    for item in manifest["units"]:
        item["sha256"] = hashlib.sha256((source / item["path"]).read_bytes()).hexdigest()
    manifest["manifest_sha256"] = sha256_json({key: value for key, value in manifest.items() if key != "manifest_sha256"})
    _write(source / "content-manifest.json", manifest)


def _mutate_allocation(source: Path, operation) -> None:
    allocation = json.loads((source / "allocation.json").read_text(encoding="utf-8"))
    operation(allocation)
    _write(source / "allocation.json", allocation)


def test_build_verify_audit_and_sample_complete_full_a1(tmp_path: Path) -> None:
    source = _copy_sources(tmp_path)
    run = _build(tmp_path, source)
    manifest, packets = verify_full_a1(run, **_paths(source))
    report = audit_full_a1(run_dir=run, output_path=tmp_path / "audit.json", **_paths(source))
    sample = sample_full_a1(run_dir=run, audit_report_path=tmp_path / "audit.json", seed="focused-test", output_path=tmp_path / "sample.json", **_paths(source))

    assert len(packets) == 50
    assert len(manifest["inventory"]) == 50
    assert report["result"] == "PASS"
    assert len(sample["selected_lesson_ids"]) == 12
    selected_units = {packet["unit_id"] for packet in packets if packet["lesson_id"] in sample["selected_lesson_ids"]}
    assert len(selected_units) == 10
    assert {exercise["type"] for packet in packets for exercise in packet["exercises"]} == service.EXERCISE_TYPES
    assert all(packet["content_status"] == "UNREVIEWED" for packet in packets)


def test_verify_rejects_inventory_drift(tmp_path: Path) -> None:
    source = _copy_sources(tmp_path)
    run = _build(tmp_path, source)
    next((run / "packets").glob("*.json")).write_text("{}", encoding="utf-8")
    with pytest.raises(ValueError, match="inventory hash mismatch"):
        verify_full_a1(run, **_paths(source))


def test_verify_rejects_source_drift(tmp_path: Path) -> None:
    source = _copy_sources(tmp_path)
    run = _build(tmp_path, source)
    allocation = json.loads((source / "allocation.json").read_text(encoding="utf-8"))
    allocation["lessons"][0]["topic"] += " changed"
    _write(source / "allocation.json", allocation)
    with pytest.raises(ValueError, match="allocation binding drift"):
        verify_full_a1(run, **_paths(source))


def test_allocation_must_match_m16_order_and_prerequisites(tmp_path: Path) -> None:
    source = _copy_sources(tmp_path)
    _mutate_allocation(source, lambda value: value["lessons"][1].__setitem__("lesson_id", value["lessons"][0]["lesson_id"]))
    with pytest.raises(ValueError, match="unique"):
        _build(tmp_path, source)

    source = _copy_sources(tmp_path / "second")
    _mutate_allocation(source, lambda value: value["lessons"][1].__setitem__("prerequisite_lesson_ids", []))
    with pytest.raises(ValueError, match="prerequisite drift"):
        _build(tmp_path / "second", source)


def test_target_cycle_forward_use_and_tier_jump_fail_closed(tmp_path: Path) -> None:
    cycle = _copy_sources(tmp_path / "cycle")
    _mutate_allocation(cycle, lambda value: value["targets"][0].__setitem__("prerequisites", [value["targets"][1]["id"]]))
    with pytest.raises(ValueError, match="cyclic"):
        _build(tmp_path / "cycle", cycle)

    forward = _copy_sources(tmp_path / "forward")
    _mutate_allocation(forward, lambda value: value["lessons"][0]["target_usage"].append({"target_id": value["targets"][1]["id"], "usage": "PRACTISE"}))
    with pytest.raises(ValueError, match="not previously introduced"):
        _build(tmp_path / "forward", forward)

    tier = _copy_sources(tmp_path / "tier")
    _mutate_allocation(tier, lambda value: value["targets"][0].__setitem__("tier", "A1.2"))
    with pytest.raises(ValueError, match="tier/dimension drift"):
        _build(tmp_path / "tier", tier)


def test_target_prerequisite_must_be_introduced_first(tmp_path: Path) -> None:
    source = _copy_sources(tmp_path)
    _mutate_allocation(source, lambda value: value["targets"][0].__setitem__("prerequisites", [value["targets"][2]["id"]]))
    with pytest.raises(ValueError, match="not introduced before|cyclic"):
        _build(tmp_path, source)


@pytest.mark.parametrize("projection", ["section", "prompt", "answer", "protocol"])
def test_audit_reports_every_duplicate_projection(tmp_path: Path, projection: str) -> None:
    source = _copy_sources(tmp_path)
    path = source / "units" / "unit-01.json"
    unit = json.loads(path.read_text(encoding="utf-8"))
    first, second = unit["lessons"][0], unit["lessons"][4]
    expected = {
        "section": "A1F_DUPLICATE_SECTION",
        "prompt": "A1F_DUPLICATE_EXERCISE_PROMPT",
        "answer": "A1F_DUPLICATE_ANSWER",
        "protocol": "A1F_DUPLICATE_PROTOCOL",
    }[projection]
    if projection == "section":
        second["content_sections"][0]["body"] = first["content_sections"][0]["body"]
    elif projection == "prompt":
        second["exercises"][0]["prompt"] = first["exercises"][0]["prompt"]
    elif projection == "answer":
        # Lessons 1 and 5 both use the multiple-choice contract.
        second["exercises"][0]["options"][0] = first["exercises"][0]["correct_answer"]
        second["exercises"][0]["correct_answer"] = first["exercises"][0]["correct_answer"]
    else:
        second["practice"]["speaking"]["instruction"] = first["practice"]["speaking"]["instruction"]
    _write(path, unit)
    _refresh_content_manifest(source)
    run = _build(tmp_path, source)
    report = audit_full_a1(run_dir=run, **_paths(source))
    assert report["result"] == "FAIL"
    assert expected in {finding["code"] for finding in report["findings"]}


@pytest.mark.parametrize(
    ("lesson_index", "exercise_index", "mutation", "message"),
    [
        (0, 0, lambda exercise: exercise.__setitem__("correct_answer", "not an option"), "not one of its options"),
        (1, 0, lambda exercise: exercise.__setitem__("acceptable_answers", []), "non-empty|should be non-empty"),
        (4, 1, lambda exercise: exercise["pairs"].__setitem__(1, {"left": exercise["pairs"][0]["left"], "right": "other"}), "one-to-one"),
        (1, 1, lambda exercise: exercise.__setitem__("correct_order", ["wrong", "order"]), "permutation"),
        (2, 0, lambda exercise: exercise.pop("questions"), "invalid fields|required property"),
        (3, 0, lambda exercise: exercise.__setitem__("media_required", True), "False was expected"),
        (4, 2, lambda exercise: exercise["rubric"].__setitem__("criteria", ["only one criterion"]), "too short"),
        (5, 2, lambda exercise: exercise["rubric"].__setitem__("criteria", ["only one criterion"]), "too short"),
    ],
)
def test_every_exercise_contract_rejects_invalid_data(tmp_path: Path, lesson_index: int, exercise_index: int, mutation, message: str) -> None:
    source = _copy_sources(tmp_path)
    unit_number = lesson_index // 5 + 1
    local_index = lesson_index % 5
    path = source / "units" / f"unit-{unit_number:02d}.json"
    unit = json.loads(path.read_text(encoding="utf-8"))
    exercise = unit["lessons"][local_index]["exercises"][exercise_index]
    mutation(exercise)
    _write(path, unit)
    _refresh_content_manifest(source)
    with pytest.raises(Exception, match=message):
        _build(tmp_path, source)


def test_sampling_is_stable_seed_sensitive_and_order_independent(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    source = _copy_sources(tmp_path)
    run = _build(tmp_path, source)
    report_path = tmp_path / "audit.json"
    audit_full_a1(run_dir=run, output_path=report_path, **_paths(source))
    first = sample_full_a1(run_dir=run, audit_report_path=report_path, seed="stable-seed", **_paths(source))
    again = sample_full_a1(run_dir=run, audit_report_path=report_path, seed="stable-seed", **_paths(source))
    changed = sample_full_a1(run_dir=run, audit_report_path=report_path, seed="different-seed", **_paths(source))
    assert first == again
    assert first["selected_lesson_ids"] != changed["selected_lesson_ids"]

    original = service.verify_full_a1
    monkeypatch.setattr(service, "verify_full_a1", lambda *args, **kwargs: (lambda result: (result[0], list(reversed(result[1]))))(original(*args, **kwargs)))
    reordered = sample_full_a1(run_dir=run, audit_report_path=report_path, seed="stable-seed", **_paths(source))
    assert reordered == first


@pytest.mark.parametrize("size", [9, 16])
def test_sampling_enforces_size_bounds(tmp_path: Path, size: int) -> None:
    source = _copy_sources(tmp_path)
    run = _build(tmp_path, source)
    report_path = tmp_path / "audit.json"
    audit_full_a1(run_dir=run, output_path=report_path, **_paths(source))
    with pytest.raises(ValueError, match="between 10 and 15"):
        sample_full_a1(run_dir=run, audit_report_path=report_path, seed="bounds", sample_size=size, **_paths(source))


def test_sampling_rejects_failed_audit(tmp_path: Path) -> None:
    source = _copy_sources(tmp_path)
    run = _build(tmp_path, source)
    report = audit_full_a1(run_dir=run, **_paths(source))
    report["result"] = "FAIL"
    report["report_sha256"] = sha256_json({key: value for key, value in report.items() if key != "report_sha256"})
    report_path = tmp_path / "failed-audit.json"
    _write(report_path, report)
    with pytest.raises(ValueError, match="passing audit"):
        sample_full_a1(run_dir=run, audit_report_path=report_path, seed="blocked", **_paths(source))


def test_practical_authoring_compiles_as_successor_without_changing_v1(tmp_path: Path) -> None:
    source_path = tmp_path / "lesson-source.json"
    seed_authoring_source(predecessor_units=COMMITTED / "units", output_path=source_path)
    content_root = tmp_path / "v2-content"
    manifest_path = compile_authoring_source(
        source_path=source_path,
        allocation_path=COMMITTED / "allocation.json",
        output_root=content_root,
    )
    v1_run = COMMITTED / "runs" / "a1full_a45a6b574127a4328b518da37be8f15ac83696d3ae77b0af4ff1e637740edc87"
    verify_full_a1(v1_run, **_paths(COMMITTED))
    run = build_full_a1(
        population_path=COMMITTED / "m15-population.json",
        blueprint_path=COMMITTED / "m16-blueprint.json",
        allocation_path=COMMITTED / "allocation.json",
        content_manifest_path=manifest_path,
        output_root=tmp_path / "runs",
        built_at=BUILT_AT,
    )
    _, packets = verify_full_a1(
        run,
        population_path=COMMITTED / "m15-population.json",
        blueprint_path=COMMITTED / "m16-blueprint.json",
        allocation_path=COMMITTED / "allocation.json",
        content_manifest_path=manifest_path,
    )
    assert len(packets) == 50
    assert manifest_path != COMMITTED / "content-manifest.json"


def test_practical_authoring_rejects_legacy_boilerplate(tmp_path: Path) -> None:
    source_path = tmp_path / "lesson-source.json"
    seed_authoring_source(predecessor_units=COMMITTED / "units", output_path=source_path)
    source = json.loads(source_path.read_text(encoding="utf-8"))
    source["lessons"][0]["content_sections"][0]["body"] += " No detail is provided."
    source["source_sha256"] = sha256_json({key: value for key, value in source.items() if key != "source_sha256"})
    _write(source_path, source)
    with pytest.raises(ValueError, match="rejected legacy boilerplate"):
        compile_authoring_source(
            source_path=source_path,
            allocation_path=COMMITTED / "allocation.json",
            output_root=tmp_path / "v2-content",
        )


def test_practical_authoring_rejects_visible_listening_transcript(tmp_path: Path) -> None:
    source_path = tmp_path / "lesson-source.json"
    seed_authoring_source(predecessor_units=COMMITTED / "units", output_path=source_path)
    source = json.loads(source_path.read_text(encoding="utf-8"))
    lesson = source["lessons"][0]
    lesson["content_sections"][0]["body"] += " " + lesson["practice"]["listening"]["transcript"]
    source["source_sha256"] = sha256_json({key: value for key, value in source.items() if key != "source_sha256"})
    _write(source_path, source)
    with pytest.raises(ValueError, match="transcript is visible"):
        compile_authoring_source(
            source_path=source_path,
            allocation_path=COMMITTED / "allocation.json",
            output_root=tmp_path / "v2-content",
        )
