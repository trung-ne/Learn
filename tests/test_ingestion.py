from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pytest
import yaml

from english_master import ingest
from english_master.ingestion import default_adapter_registry
from english_master.ingestion.adapters.tatoeba_text import TatoebaTextAdapter
from english_master.ingestion.base import FetchOptions, SourceAdapter
from english_master.ingestion.pipeline import (
    IngestionPipeline,
    IngestionRunError,
    PipelinePaths,
)
from english_master.ingestion.registry import AdapterRegistry, AdapterRegistryError
from english_master.schema_validation import SourcePermissionError, validate_instance

ROOT = Path(__file__).resolve().parents[1]
REGISTRY = ROOT / "sources" / "registry.yaml"
VALID_FIXTURE = ROOT / "tests" / "fixtures" / "ingestion" / "tatoeba_text_valid.tsv"
MALFORMED_FIXTURE = ROOT / "tests" / "fixtures" / "ingestion" / "tatoeba_text_malformed.tsv"
RETRIEVED_AT = datetime(2026, 8, 31, 12, 0, tzinfo=timezone.utc)


def options(path: Path = VALID_FIXTURE, max_records: int = 2) -> FetchOptions:
    return FetchOptions(path, max_records, RETRIEVED_AT)


def pipeline(data_root: Path, registry_path: Path = REGISTRY) -> IngestionPipeline:
    return IngestionPipeline(
        default_adapter_registry(), registry_path, PipelinePaths(data_root)
    )


def altered_registry(tmp_path: Path, source_id: str, mutator: Any) -> Path:
    document = yaml.safe_load(REGISTRY.read_text(encoding="utf-8"))
    source = next(item for item in document["sources"] if item["source_id"] == source_id)
    mutator(source)
    path = tmp_path / "registry.yaml"
    path.write_text(yaml.safe_dump(document, sort_keys=False), encoding="utf-8")
    return path


def test_adapter_contract_is_abstract_and_tatoeba_is_complete() -> None:
    with pytest.raises(TypeError):
        SourceAdapter()  # type: ignore[abstract]
    adapter = TatoebaTextAdapter()
    assert adapter.source_id == "src_tatoeba_text"
    assert set(adapter.required_operations) >= {
        "fetch_source",
        "ingest_text",
        "store_text",
        "transform_text",
    }


def test_adapter_registry_lists_and_rejects_unknown_duplicate_and_mismatch() -> None:
    adapter = TatoebaTextAdapter()
    registry = AdapterRegistry()
    registry.register(adapter.source_id, adapter)  # type: ignore[arg-type]
    assert registry.available_source_ids() == ("src_tatoeba_text",)
    assert registry.get("src_tatoeba_text") is adapter
    with pytest.raises(AdapterRegistryError, match="already registered"):
        registry.register(adapter.source_id, adapter)  # type: ignore[arg-type]
    with pytest.raises(AdapterRegistryError, match="No adapter"):
        registry.get("src_unknown")
    with pytest.raises(AdapterRegistryError, match="declares"):
        AdapterRegistry().register("src_wrong", adapter)  # type: ignore[arg-type]


def test_fetch_is_bounded_and_preserves_exact_bytes() -> None:
    adapter = TatoebaTextAdapter()
    payload = adapter.fetch(options())
    assert payload.content == VALID_FIXTURE.read_bytes()
    assert payload.input_description["record_count"] == 2
    with pytest.raises(ValueError, match="exceeding --max-records"):
        adapter.fetch(options(max_records=1))
    with pytest.raises(ValueError, match="between 1 and 100"):
        adapter.fetch(options(max_records=0))


def test_parse_reports_malformed_and_duplicate_rows_without_silent_drop() -> None:
    adapter = TatoebaTextAdapter()
    result = adapter.parse(adapter.fetch(options(MALFORMED_FIXTURE, 3)))
    assert [record.sentence_id for record in result.records] == ["100003"]
    assert [error.code for error in result.errors] == [
        "wrong_field_count",
        "duplicate_source_record_id",
    ]
    assert all(error.raw_record for error in result.errors)


def test_provenance_hash_and_normalized_id_are_complete_and_deterministic() -> None:
    adapter = TatoebaTextAdapter()
    payload = adapter.fetch(options())
    record = adapter.parse(payload).records[0]
    source_document = yaml.safe_load(REGISTRY.read_text(encoding="utf-8"))
    source = next(
        item for item in source_document["sources"] if item["source_id"] == adapter.source_id
    )
    provenance = adapter.provenance(record, source, options())
    expected_fields = {
        "source_id",
        "source_name",
        "source_url",
        "source_record_id",
        "retrieved_at",
        "retrieved_by",
        "license",
        "license_url",
        "attribution",
        "content_hash",
        "ingestion_version",
    }
    assert set(provenance) == expected_fields
    assert provenance["content_hash"] == hashlib.sha256(record.raw_line).hexdigest()
    normalized = adapter.normalize(record, provenance)
    assert normalized == adapter.normalize(record, provenance)
    assert "cefr_level" not in normalized
    validate_instance(normalized, "normalized-text")


def test_pipeline_retains_raw_writes_valid_records_and_auditable_report(tmp_path: Path) -> None:
    report = pipeline(tmp_path / "data").run("src_tatoeba_text", options())
    assert report["outcome"] == "COMPLETED"
    assert report["counts"] == {
        "fetched": 2,
        "parsed": 2,
        "normalized": 2,
        "rejected": 0,
        "quarantined": 0,
    }
    raw_path = tmp_path / report["output_paths"]["raw_payload"]
    report_path = tmp_path / report["output_paths"]["report"]
    run_path = tmp_path / report["output_paths"]["normalized_run"]
    assert raw_path.read_bytes() == VALID_FIXTURE.read_bytes()
    assert json.loads(report_path.read_text(encoding="utf-8")) == report
    record_paths = sorted((run_path / "records").glob("*.json"))
    assert len(record_paths) == 2
    for record_path in record_paths:
        validate_instance(json.loads(record_path.read_text(encoding="utf-8")), "normalized-text")


def test_pipeline_rerun_is_idempotent(tmp_path: Path) -> None:
    runner = pipeline(tmp_path / "data")
    first = runner.run("src_tatoeba_text", options())
    second = runner.run("src_tatoeba_text", options())
    assert first == second
    assert len(list((tmp_path / "data" / "normalized" / "src_tatoeba_text" / "runs").iterdir())) == 1


@pytest.mark.parametrize("status", ["REFERENCE_ONLY", "QUARANTINED", "REJECTED"])
def test_pipeline_rejects_nonapproved_source_before_fetch(tmp_path: Path, status: str) -> None:
    registry_path = altered_registry(
        tmp_path,
        "src_tatoeba_text",
        lambda source: source.__setitem__("status", status),
    )
    with pytest.raises(SourcePermissionError, match="APPROVED is required"):
        pipeline(tmp_path / "data", registry_path).run("src_tatoeba_text", options())
    assert not (tmp_path / "data").exists()


def test_pipeline_rejects_denied_operation_before_fetch(tmp_path: Path) -> None:
    registry_path = altered_registry(
        tmp_path,
        "src_tatoeba_text",
        lambda source: source["media_permissions"]["text"].__setitem__(
            "transform_allowed", False
        ),
    )
    with pytest.raises(SourcePermissionError, match="does not permit transform_text"):
        pipeline(tmp_path / "data", registry_path).run("src_tatoeba_text", options())
    assert not (tmp_path / "data").exists()


def test_pipeline_rejects_unregistered_or_adapterless_source(tmp_path: Path) -> None:
    with pytest.raises(SourcePermissionError, match="not registered"):
        pipeline(tmp_path / "data").run("src_not_registered", options())
    with pytest.raises(AdapterRegistryError, match="No adapter"):
        pipeline(tmp_path / "data").run("src_wiktionary_en_text", options())


def test_record_errors_are_quarantined_and_cli_semantics_are_nonzero(tmp_path: Path) -> None:
    runner = pipeline(tmp_path / "data")
    with pytest.raises(IngestionRunError) as captured:
        runner.run("src_tatoeba_text", options(MALFORMED_FIXTURE, 3))
    report = captured.value.report
    assert report["outcome"] == "COMPLETED_WITH_ERRORS"
    assert report["counts"] == {
        "fetched": 3,
        "parsed": 1,
        "normalized": 1,
        "rejected": 2,
        "quarantined": 2,
    }
    quarantine_path = tmp_path / report["output_paths"]["quarantine"]
    quarantined = json.loads(quarantine_path.read_text(encoding="utf-8"))
    assert len(quarantined["errors"]) == 2


def test_atomic_run_publish_cleans_staging_directory_on_write_failure(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    original_replace = Path.replace

    def fail_run_publish(path: Path, target: Path) -> Path:
        if path.name.startswith(".run_"):
            raise OSError("simulated publish failure")
        return original_replace(path, target)

    monkeypatch.setattr(Path, "replace", fail_run_publish)
    with pytest.raises(OSError, match="simulated publish failure"):
        pipeline(tmp_path / "data").run("src_tatoeba_text", options())
    runs = tmp_path / "data" / "normalized" / "src_tatoeba_text" / "runs"
    assert runs.is_dir()
    assert list(runs.iterdir()) == []


def test_cli_success_and_failure_exit_codes(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    common = [
        "--source",
        "src_tatoeba_text",
        "--input",
        str(VALID_FIXTURE),
        "--max-records",
        "2",
        "--retrieved-at",
        "2026-08-31T12:00:00Z",
        "--offline-fixture",
        "--data-root",
        str(tmp_path / "success" / "data"),
    ]
    assert ingest.main(common) == 0
    assert "COMPLETED" in capsys.readouterr().out

    denied = common.copy()
    denied[denied.index(str(tmp_path / "success" / "data"))] = str(tmp_path / "denied" / "data")
    denied[denied.index("src_tatoeba_text")] = "src_cefr_companion_volume"
    assert ingest.main(denied) == 1
    assert "INGESTION FAILED" in capsys.readouterr().err

    malformed = common.copy()
    malformed[malformed.index(str(VALID_FIXTURE))] = str(MALFORMED_FIXTURE)
    malformed[malformed.index("2")] = "3"
    malformed[malformed.index(str(tmp_path / "success" / "data"))] = str(
        tmp_path / "malformed" / "data"
    )
    assert ingest.main(malformed) == 1
    assert "COMPLETED_WITH_ERRORS" in capsys.readouterr().err
