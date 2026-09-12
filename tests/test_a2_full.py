from __future__ import annotations

import json
import shutil
from pathlib import Path

import pytest

from english_master.a2_full import service
from english_master.a2_full.service import audit_full_a2, build_full_a2, sample_full_a2, verify_full_a2
from english_master.lesson_generation.canonical import sha256_json

ROOT = Path(__file__).parents[1]
COMMITTED = ROOT / "curriculum" / "a2-full" / "v1"
POPULATION = ROOT / "curriculum" / "a1-full" / "v1" / "m15-population.json"
BLUEPRINT = ROOT / "curriculum" / "a2-blueprint" / "m16-a2-blueprint.json"


def _write(path: Path, value: dict) -> None:
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _copy_sources(tmp_path: Path) -> Path:
    source = tmp_path / "source"
    source.mkdir(parents=True)
    shutil.copy2(POPULATION, source / "m15-population.json")
    shutil.copy2(BLUEPRINT, source / "m16-blueprint.json")
    for name in ("allocation.json", "content-manifest.json"):
        shutil.copy2(COMMITTED / name, source / name)
    shutil.copytree(COMMITTED / "units", source / "units")
    return source


def _paths(source: Path) -> dict[str, Path]:
    return {"population_path": source / "m15-population.json", "blueprint_path": source / "m16-blueprint.json", "allocation_path": source / "allocation.json", "content_manifest_path": source / "content-manifest.json"}


def _build(tmp_path: Path, source: Path) -> Path:
    return build_full_a2(**_paths(source), output_root=tmp_path / "runs", built_at="2026-09-13T12:00:00Z")


def test_build_verify_audit_sample_complete(tmp_path: Path) -> None:
    source = _copy_sources(tmp_path)
    run = _build(tmp_path, source)
    manifest, packets = verify_full_a2(run, **_paths(source))
    report = audit_full_a2(run_dir=run, output_path=tmp_path / "audit.json", **_paths(source))
    sample = sample_full_a2(run_dir=run, audit_report_path=tmp_path / "audit.json", seed="test", output_path=tmp_path / "sample.json", **_paths(source))
    assert len(packets) == len(manifest["inventory"]) == 50
    assert report["result"] == "PASS"
    assert len(sample["selected_lesson_ids"]) == 12
    assert {p["unit_id"] for p in packets if p["lesson_id"] in sample["selected_lesson_ids"]} == {f"m16a2-v1-a2-u{i:02d}" for i in range(1, 11)}
    assert {e["type"] for p in packets for e in p["exercises"]} == {"multiple_choice", "fill_blank", "reading", "speaking"}
    assert {p["tier"] for p in packets} == {"A2.1", "A2.2"}
    assert all(p["content_status"] == "UNREVIEWED" for p in packets)
    assert any(p["lesson_kind"] == "REVIEW" for p in packets)


def test_verify_rejects_packet_and_source_drift(tmp_path: Path) -> None:
    source = _copy_sources(tmp_path)
    run = _build(tmp_path, source)
    next((run / "packets").glob("*.json")).write_text("{}", encoding="utf-8")
    with pytest.raises(ValueError, match="inventory hash mismatch"):
        verify_full_a2(run, **_paths(source))
    source = _copy_sources(tmp_path / "source-drift")
    run = _build(tmp_path / "source-drift", source)
    allocation = json.loads((source / "allocation.json").read_text(encoding="utf-8"))
    allocation["lessons"][0]["topic"] += " changed"
    _write(source / "allocation.json", allocation)
    with pytest.raises(ValueError, match="allocation binding drift"):
        verify_full_a2(run, **_paths(source))


@pytest.mark.parametrize("mutation,message", [
    (lambda e: e.__setitem__("correct_answer", "not an option"), "not one of its options"),
    (lambda e: e.__setitem__("prompt", "Complete the model."), "visible blank"),
])
def test_exercise_answer_contracts_fail_closed(tmp_path: Path, mutation, message: str) -> None:
    source = _copy_sources(tmp_path)
    path = source / "units" / "unit-01.json"
    unit = json.loads(path.read_text(encoding="utf-8"))
    mutation(unit["lessons"][0]["exercises"][0 if "option" in message else 1])
    _write(path, unit)
    manifest = json.loads((source / "content-manifest.json").read_text(encoding="utf-8"))
    import hashlib
    for item in manifest["units"]:
        item["sha256"] = hashlib.sha256((source / item["path"]).read_bytes()).hexdigest()
    manifest["manifest_sha256"] = sha256_json({k: v for k, v in manifest.items() if k != "manifest_sha256"})
    _write(source / "content-manifest.json", manifest)
    with pytest.raises(Exception, match=message):
        _build(tmp_path, source)


def test_sample_is_deterministic_and_failed_audit_blocks(tmp_path: Path) -> None:
    source = _copy_sources(tmp_path)
    run = _build(tmp_path, source)
    audit_path = tmp_path / "audit.json"
    audit = audit_full_a2(run_dir=run, output_path=audit_path, **_paths(source))
    first = sample_full_a2(run_dir=run, audit_report_path=audit_path, seed="same", **_paths(source))
    second = sample_full_a2(run_dir=run, audit_report_path=audit_path, seed="same", **_paths(source))
    assert first == second
    audit["result"] = "FAIL"
    audit["report_sha256"] = sha256_json({k: v for k, v in audit.items() if k != "report_sha256"})
    _write(tmp_path / "failed.json", audit)
    with pytest.raises(ValueError, match="passing audit"):
        sample_full_a2(run_dir=run, audit_report_path=tmp_path / "failed.json", seed="blocked", **_paths(source))
