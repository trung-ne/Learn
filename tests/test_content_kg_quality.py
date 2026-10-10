from __future__ import annotations

import json
from pathlib import Path

import pytest

from english_master.content_kg_quality.service import build_request, run_quality, verify_report

ROOT = Path(__file__).resolve().parents[1]
POPULATION = "curriculum/a1-full/v1/m15-population.json"
SOURCES = (
    ("A1", "curriculum/a1-full/v1/runs/a1full_a45a6b574127a4328b518da37be8f15ac83696d3ae77b0af4ff1e637740edc87", "curriculum/a1-full/v1/m16-blueprint.json"),
    ("A2", "curriculum/a2-full/v1/runs/a2full_9855332711d456bd54e38eea6d83400629e1dd29725533f22687a98c23499833", "curriculum/a2-blueprint/m16-a2-blueprint.json"),
    ("B1", "curriculum/b1-full/v1/runs/b1full_e374b17202742db639b0a4dcda188995b9366ab01b3f5f897bb128b4d543b95c", "curriculum/b1-blueprint/m16-b1-blueprint.json"),
    ("B2", "curriculum/b2-full/v1/runs/b2full_2baff83eaca7c530d364fcc81f6d69261dbe3a1e3a2bb1c1009c1411e4a0d2ec", "curriculum/b2-blueprint/m16-b2-blueprint.json"),
    ("C1", "curriculum/c1-full/v1/runs/c1full_17d6807f312a392a98fb6fac4d83f84e75e9b24f19faa3b420bbc9f03ccd9f1c", "curriculum/c1-blueprint/m16-c1-blueprint.json"),
    ("C2", "curriculum/c2-full/v1/runs/c2full_770443bc0757a702f6d273de7fbf26e41bca701ad0123662b7f0aefb33369b83", "curriculum/c2-blueprint/m16-c2-blueprint.json"),
)


def _levels() -> list[dict[str, str]]:
    rows = []
    for level, run_dir, blueprint in SOURCES:
        base = f"curriculum/{level.lower()}-full/v1"
        rows.append({
            "level": level,
            "run_dir": str(ROOT / run_dir),
            "population_path": str(ROOT / POPULATION),
            "blueprint_path": str(ROOT / blueprint),
            "allocation_path": str(ROOT / base / "allocation.json"),
            "content_manifest_path": str(ROOT / base / "content-manifest.json"),
        })
    return rows


def test_quality_report_is_hash_bound_and_classifies_expected_boundaries(tmp_path: Path) -> None:
    request_path = tmp_path / "request.json"
    report_path = tmp_path / "report.json"
    request = build_request(_levels(), output_path=request_path)
    report = run_quality(request_path=request_path, output_path=report_path)

    assert request["content_status"] == "UNREVIEWED"
    assert report["lesson_count"] == 300
    assert report["result"] in {"PASS", "PASS_WITH_FLAGS"}
    assert report == verify_report(request_path=request_path, report_path=report_path)
    assert any(item["code"] == "CKQ_MEDIA_AVAILABILITY" and item["disposition"] == "EXPECTED" for item in report["findings"])
    assert any(item["code"] == "CKQ_EXAMPLE_AVAILABILITY" and item["disposition"] == "UNAVAILABLE" for item in report["findings"])
    with pytest.raises(FileExistsError):
        run_quality(request_path=request_path, output_path=report_path)


def test_request_rejects_out_of_order_levels() -> None:
    levels = _levels()
    levels[0], levels[1] = levels[1], levels[0]
    with pytest.raises(ValueError, match="exactly ordered"):
        build_request(levels)


def test_explicit_vocabulary_lane_checks_supplied_examples(tmp_path: Path) -> None:
    request_path = tmp_path / "request.json"
    build_request(_levels(), web_validation_scope=("vocabulary",), output_path=request_path)
    report = run_quality(request_path=request_path)
    assert any(item["code"] == "CKQ_WEB_LANE_SCOPE" and item["disposition"] == "EXPECTED" for item in report["findings"])
    assert not any(item["code"] == "CKQ_MISSING_EXAMPLE" for item in report["findings"])


def test_report_verification_rejects_tampering(tmp_path: Path) -> None:
    request_path = tmp_path / "request.json"
    report_path = tmp_path / "report.json"
    build_request(_levels(), output_path=request_path)
    run_quality(request_path=request_path, output_path=report_path)
    report = json.loads(report_path.read_text(encoding="utf-8"))
    report["result"] = "FAIL"
    report_path.write_text(json.dumps(report), encoding="utf-8")
    with pytest.raises(ValueError, match="hash mismatch"):
        verify_report(request_path=request_path, report_path=report_path)
