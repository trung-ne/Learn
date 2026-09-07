from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

import pytest

from english_master.ingestion_pilot.service import PilotError, prepare, run, verify
from english_master.lesson_generation.canonical import identity, sha256_json
from english_master.schema_validation import load_source_registry

ROOT = Path(__file__).resolve().parents[1]
REGISTRY = ROOT / "sources" / "registry.yaml"


def _write(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, sort_keys=True), encoding="utf-8")


def _bundle(tmp_path: Path, *, count: int = 1000) -> tuple[Path, Path, Path, Path, Path]:
    data_root = tmp_path / "data"
    bundle = data_root / "raw" / "src_tatoeba_text" / "acquisitions" / "test"
    source = next(item for item in load_source_registry(REGISTRY)["sources"] if item["source_id"] == "src_tatoeba_text")
    license_data = source["license"]
    rows = ["sentence_id\tlanguage\ttext\tauthor\tlicense\tlicense_url"]
    rows.extend(f"{index}\teng\tA real-format test sentence number {index}.\ttest-author-{index}\t{license_data['name']}\t{license_data['url']}" for index in range(1, count + 1))
    payload = bundle / "official" / "sentences.tsv"
    payload.parent.mkdir(parents=True, exist_ok=True)
    payload.write_text("\n".join(rows) + "\n", encoding="utf-8")
    content = payload.read_bytes()
    authorization: dict[str, object] = {
        "schema_version": "1.0", "record_type": "ingestion_pilot_authorization", "authorization_id": "PENDING", "status": "AUTHORIZED", "source_id": "src_tatoeba_text", "registry_sha256": hashlib.sha256(REGISTRY.read_bytes()).hexdigest(), "official_download_url": "https://tatoeba.org/en/downloads", "official_documentation_url": "https://tatoeba.org/en/downloads", "expected_filename": payload.name, "expected_payload_sha256": hashlib.sha256(content).hexdigest(), "expected_payload_bytes": len(content), "checksum_origin": "LOCALLY_OBSERVED", "target_records": count, "language": "eng", "license": license_data["name"], "license_url": license_data["url"], "authorized_operations": ["fetch_source", "ingest_source", "store_source", "transform_source", "ingest_text", "store_text", "transform_text"], "authorized_by": "TEST_ONLY", "authorized_at": "2026-09-07T00:00:00Z", "content_lifecycle_status": "UNREVIEWED", "approved_corpus": False, "lesson_material": False, "release_eligible": False,
    }
    authorization["authorization_id"] = identity("pilotauth", authorization, "authorization_id")
    receipt: dict[str, object] = {
        "schema_version": "1.0", "record_type": "ingestion_pilot_receipt", "receipt_id": "PENDING", "authorization": {"id": authorization["authorization_id"], "sha256": sha256_json(authorization)}, "source_id": "src_tatoeba_text", "official_download_url": authorization["official_download_url"], "filename": payload.name, "payload_sha256": authorization["expected_payload_sha256"], "payload_bytes": len(content), "acquired_at": "2026-09-07T00:00:00Z", "acquired_by": "TEST_ONLY", "acquisition_method": "OFFICIAL_DOWNLOAD", "checksum_verified": True, "content_lifecycle_status": "UNREVIEWED", "approved_corpus": False, "lesson_material": False, "release_eligible": False,
    }
    receipt["receipt_id"] = identity("pilotreceipt", receipt, "receipt_id")
    authorization_path = bundle / "authorization.json"
    receipt_path = bundle / "receipt.json"
    _write(authorization_path, authorization)
    _write(receipt_path, receipt)
    return data_root, authorization_path, receipt_path, payload, bundle


def test_authorized_pilot_prepare_verify_and_run_offline(tmp_path: Path) -> None:
    data_root, authorization, receipt, payload, bundle = _bundle(tmp_path)
    report = prepare(authorization_path=authorization, receipt_path=receipt, payload_path=payload, registry_path=REGISTRY, output_directory=bundle, data_root=data_root)
    prepared = bundle / "prepared" / "english-authorized-records.tsv"
    assert report["records_selected"] == 1000
    verified = verify(authorization_path=authorization, receipt_path=receipt, preparation_report_path=bundle / "preparation-report.json", prepared_tsv_path=prepared, registry_path=REGISTRY)
    assert verified["verified"] is True
    output = run(authorization_path=authorization, receipt_path=receipt, preparation_report_path=bundle / "preparation-report.json", prepared_tsv_path=prepared, registry_path=REGISTRY, data_root=data_root, retrieved_at=datetime(2026, 9, 7, tzinfo=timezone.utc), processed_at=datetime(2026, 9, 7, tzinfo=timezone.utc))
    assert output["ingestion_report"]["counts"]["normalized"] == 1000
    assert output["approved_corpus"] is False


def test_pilot_rejects_tampered_prepared_tsv(tmp_path: Path) -> None:
    data_root, authorization, receipt, payload, bundle = _bundle(tmp_path)
    prepare(authorization_path=authorization, receipt_path=receipt, payload_path=payload, registry_path=REGISTRY, output_directory=bundle, data_root=data_root)
    prepared = bundle / "prepared" / "english-authorized-records.tsv"
    prepared.write_text(prepared.read_text(encoding="utf-8").replace("test sentence", "tampered sentence", 1), encoding="utf-8")
    with pytest.raises(PilotError, match="hash drift"):
        verify(authorization_path=authorization, receipt_path=receipt, preparation_report_path=bundle / "preparation-report.json", prepared_tsv_path=prepared, registry_path=REGISTRY)


def test_pilot_rejects_less_than_minimum_records(tmp_path: Path) -> None:
    data_root, authorization, receipt, payload, bundle = _bundle(tmp_path, count=999)
    with pytest.raises(PilotError):
        prepare(authorization_path=authorization, receipt_path=receipt, payload_path=payload, registry_path=REGISTRY, output_directory=bundle, data_root=data_root)
