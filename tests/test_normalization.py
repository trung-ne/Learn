from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path

import pytest

from english_master.normalize import main as normalize_main
from english_master.normalization.models import NearDuplicatePolicy
from english_master.normalization.pipeline import NormalizationError, NormalizationPipeline, PipelineConfig

ROOT = Path(__file__).resolve().parents[1]
REGISTRY = ROOT / "sources" / "registry.yaml"
NOW = datetime(2026, 8, 31, 12, 0, tzinfo=UTC)


def m3_record(suffix: str, text: str, *, language: str = "en", source_record_id: str | None = None) -> dict[str, object]:
    source_record_id = source_record_id or suffix
    return {
        "schema_version": "1.0", "record_type": "normalized_text",
        "id": f"text_src_tatoeba_text_{int(suffix):016x}", "language": language,
        "text": text, "ingestion_version": "1.0",
        "provenance": {
            "source_id": "src_tatoeba_text", "source_name": "Tatoeba sentence text",
            "source_url": f"https://tatoeba.org/en/sentences/show/{source_record_id}",
            "source_record_id": source_record_id, "retrieved_at": "2026-08-31T10:00:00Z",
            "retrieved_by": "tatoeba_text_v1", "license": "CC-BY-2.0-FR",
            "license_url": "https://creativecommons.org/licenses/by/2.0/fr/",
            "attribution": "Original test author", "content_hash": "a" * 64,
            "ingestion_version": "1.0",
        },
    }


def write_records(directory: Path, records: list[dict[str, object]]) -> None:
    directory.mkdir(parents=True)
    for index, record in enumerate(records):
        (directory / f"record-{index}.json").write_text(json.dumps(record), encoding="utf-8")


def test_pipeline_preserves_provenance_groups_candidates_and_is_idempotent(tmp_path: Path) -> None:
    input_dir = tmp_path / "input"
    records = [
        m3_record("1", "The quick brown fox jumps over the log."),
        m3_record("2", "  THE quick brown fox jumps over the log!  "),
        m3_record("3", "The quick brown fox jumped over the log."),
        m3_record("4", "Con cáo nâu nhanh nhẹn nhảy qua khúc gỗ.", language="vi"),
    ]
    write_records(input_dir, records)
    config = PipelineConfig(
        input_path=input_dir,
        output_root=tmp_path / "output",
        source_registry_path=REGISTRY,
        processed_at=NOW,
        max_records=4,
        near_policy=NearDuplicatePolicy(threshold=0.7),
    )
    report = NormalizationPipeline().run(config)
    rerun = NormalizationPipeline().run(config)
    assert report == rerun
    assert report["counts"]["normalized_duplicate_groups"] == 1
    assert report["counts"]["near_duplicate_candidates"] >= 1
    run = Path(report["output_paths"]["run"])
    output_records = [json.loads(path.read_text(encoding="utf-8")) for path in sorted((run / "records").glob("*.json"))]
    assert len(output_records) == 4
    assert all(record["raw_hash"] and record["normalized_hash"] for record in output_records)
    assert all(record["provenance"]["attribution"] == "Original test author" for record in output_records)
    assert all(record["source_content_hash_verification"]["status"] == "NOT_VERIFIABLE_FROM_M3_RECORD" for record in output_records)
    groups = [json.loads(path.read_text(encoding="utf-8")) for path in (run / "groups").glob("*.json")]
    assert any(len(group["source_record_ids"]) == 2 for group in groups)
    queue = json.loads((run / "review" / "queue.json").read_text(encoding="utf-8"))
    assert queue["status"] == "REVIEW_REQUIRED"
    first_output = sorted((run / "records").glob("*.json"))[0]
    first_output.write_text("{}", encoding="utf-8")
    with pytest.raises(Exception, match="content hash mismatch"):
        NormalizationPipeline().run(config)


def test_pipeline_rejects_bounds_malformed_provenance_and_identity_conflict(tmp_path: Path) -> None:
    input_dir = tmp_path / "input"
    write_records(input_dir, [m3_record("1", "one long enough sentence"), m3_record("2", "another long enough sentence")])
    with pytest.raises(NormalizationError, match="exceeding max_records"):
        NormalizationPipeline().run(PipelineConfig(input_dir, tmp_path / "out", REGISTRY, NOW, max_records=1))

    malformed_dir = tmp_path / "malformed"
    malformed = m3_record("3", "valid text")
    del malformed["provenance"]["attribution"]  # type: ignore[index]
    write_records(malformed_dir, [malformed])
    with pytest.raises(NormalizationError, match="Invalid M3 normalized record"):
        NormalizationPipeline().run(PipelineConfig(malformed_dir, tmp_path / "out2", REGISTRY, NOW))

    conflict_dir = tmp_path / "conflict"
    first = m3_record("4", "first version", source_record_id="same")
    second = m3_record("5", "changed version", source_record_id="same")
    write_records(conflict_dir, [first, second])
    with pytest.raises(NormalizationError, match="Inconsistent raw content"):
        NormalizationPipeline().run(PipelineConfig(conflict_dir, tmp_path / "out3", REGISTRY, NOW))


def test_pipeline_detects_incomplete_output_conflict(tmp_path: Path) -> None:
    input_dir = tmp_path / "input"
    write_records(input_dir, [m3_record("1", "a sufficiently long record")])
    output = tmp_path / "output"
    config = PipelineConfig(input_dir, output, REGISTRY, NOW)
    report = NormalizationPipeline().run(config)
    report_path = Path(report["output_paths"]["report"])
    report_path.unlink()
    with pytest.raises(Exception, match="Incomplete run directory"):
        NormalizationPipeline().run(config)


def test_atomic_publish_failure_removes_staging(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    input_dir = tmp_path / "input"
    write_records(input_dir, [m3_record("1", "a sufficiently long record")])
    output = tmp_path / "output"

    def fail_replace(self: Path, target: Path) -> Path:
        raise OSError("simulated publish failure")

    monkeypatch.setattr(Path, "replace", fail_replace)
    with pytest.raises(OSError, match="simulated publish failure"):
        NormalizationPipeline().run(PipelineConfig(input_dir, output, REGISTRY, NOW))
    runs = output / "runs"
    assert not runs.exists() or list(runs.iterdir()) == []


def test_cli_success_and_nonzero_failures(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    input_dir = tmp_path / "input"
    write_records(input_dir, [m3_record("1", "the quick brown fox jumps")])
    args = [
        "--input", str(input_dir),
        "--output-root", str(tmp_path / "output"),
        "--processed-at", "2026-08-31T12:00:00Z",
        "--max-records", "1",
        "--source-registry", str(REGISTRY),
    ]
    assert normalize_main(args) == 0
    assert "review candidates" in capsys.readouterr().out
    assert normalize_main([*args, "--ngram-size", "1"]) == 1
    assert "Normalization failed" in capsys.readouterr().err
    assert normalize_main([*args[:-1], str(tmp_path / "missing.yaml")]) == 1
