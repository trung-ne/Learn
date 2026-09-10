from __future__ import annotations

import hashlib
import io
import json
import shutil
import wave
from pathlib import Path

import pytest

from english_master.lesson_generation.canonical import identity
from english_master.media_ingestion.__main__ import main
from english_master.media_ingestion.evidence_v2 import assess_evidence, prepare_v2, run_v2, verify_v2
from english_master.media_ingestion.service import MediaIngestionError
from english_master.schema_validation import SchemaValidationError, validate_instance

ROOT = Path(__file__).resolve().parents[1]
REGISTRY = ROOT / "sources" / "registry.yaml"


def _wav_bytes() -> bytes:
    output = io.BytesIO()
    with wave.open(output, "wb") as stream:
        stream.setnchannels(1); stream.setsampwidth(2); stream.setframerate(8000); stream.writeframes(b"\x00\x00" * 80)
    return output.getvalue()


def _authorization(payload: bytes, evidence: bytes) -> dict[str, object]:
    permissions = {
        "can_download_audio": True, "can_download_video": False, "can_store": True,
        "can_clip": False, "can_transform": False, "can_extract_audio": False,
        "can_generate_transcript": False, "can_generate_timestamps": True,
        "can_redistribute": False,
    }
    evidence_hash = hashlib.sha256(evidence).hexdigest()
    value: dict[str, object] = {
        "schema_version": "2.0", "record_type": "media_source_authorization", "authorization_id": "PENDING",
        "authorization_mode": "OFFLINE_TEST_FIXTURE_ONLY", "fixture_only": True,
        "registry_path": "sources/registry.yaml", "registry_sha256": hashlib.sha256(REGISTRY.read_bytes()).hexdigest(),
        "source_id": "src_tatoeba_audio_cc_by_4", "source_status": "APPROVED", "source_url": "https://tatoeba.org/en/downloads",
        "source_record_id": "fixture-audio-v2-001", "official_record_url": "https://tatoeba.org/en/downloads/fixture-audio-v2-001",
        "media_kind": "AUDIO", "expected_filename": "fixture.wav", "expected_payload_sha256": hashlib.sha256(payload).hexdigest(),
        "expected_payload_bytes": len(payload), "expected_mime_type": "audio/wav",
        "expected_metadata": {"duration_ms": 10, "container": "WAV", "codecs": ["PCM_S16LE"], "width": None, "height": None},
        "license": "CC-BY-4.0", "license_url": "https://creativecommons.org/licenses/by/4.0/legalcode.en",
        "attribution": "Offline test fixture attributed to the test suite; not an external media record.",
        "permissions": permissions,
        "permission_evidence": [
            {
                "operation": operation, "snapshot_path": "permission.json", "snapshot_sha256": evidence_hash,
                "snapshot_bytes": len(evidence), "locator": {"kind": "JSON_POINTER", "pointer": f"/permissions/{operation}"},
                "located_value_sha256": hashlib.sha256(b"true").hexdigest(), "evidence_note": "Local fixture evidence only.",
            }
            for operation, allowed in permissions.items() if allowed
        ],
        "authorized_at": "2026-09-08T00:00:00Z", "expires_at": "2026-09-10T00:00:00Z",
    }
    value["authorization_id"] = identity("mediaauth", value, "authorization_id")
    return value


def _inputs(tmp_path: Path) -> tuple[Path, Path, Path, Path, Path, bytes]:
    payload = _wav_bytes(); payload_path = tmp_path / "fixture.wav"; payload_path.write_bytes(payload)
    evidence_root = tmp_path / "evidence"; evidence_root.mkdir()
    evidence = json.dumps({"permissions": {"can_download_audio": True, "can_store": True, "can_generate_timestamps": True}}, sort_keys=True).encode()
    (evidence_root / "permission.json").write_bytes(evidence)
    authorization_path = tmp_path / "authorization-v2.json"; authorization_path.write_text(json.dumps(_authorization(payload, evidence)), encoding="utf-8")
    assessment_path = tmp_path / "assessment.json"
    receipt_path = tmp_path / "receipt-v2.json"
    return authorization_path, evidence_root, assessment_path, receipt_path, payload_path, payload


def _prepared(tmp_path: Path) -> tuple[Path, Path, Path, Path, Path]:
    authorization, evidence_root, assessment, receipt, payload, _ = _inputs(tmp_path)
    result = assess_evidence(authorization_path=authorization, evidence_root=evidence_root, assessment_path=assessment, assessed_at="2026-09-08T00:30:00Z")
    assert result["overall_result"] == "CONSISTENT"
    assert result["rights_granted"] is False
    prepare_v2(authorization_path=authorization, payload_path=payload, registry_path=REGISTRY, assessment_path=assessment, receipt_path=receipt, acquired_at="2026-09-08T01:00:00Z")
    return authorization, evidence_root, assessment, receipt, payload


def test_v2_assess_prepare_run_verify_retains_registry_and_evidence(tmp_path: Path) -> None:
    authorization, evidence_root, assessment, receipt, payload = _prepared(tmp_path)
    directory = run_v2(authorization_path=authorization, receipt_path=receipt, payload_path=payload, registry_path=REGISTRY, assessment_path=assessment, evidence_root=evidence_root, data_root=tmp_path / "data", completed_at="2026-09-08T02:00:00Z")
    verification = verify_v2(run_directory=directory)
    assert verification["result"] == "PASS"
    assert verification["payload_matches_authorization"] is True
    assert (directory / "registry-snapshot.yaml").read_bytes() == REGISTRY.read_bytes()
    assert (directory / "evidence" / "permission.json").is_file()
    report = json.loads((directory / "run-report.json").read_text(encoding="utf-8"))
    assert report["schema_version"] == "2.0"
    assert {item["role"] for item in report["inventory"]} >= {"SOURCE_REGISTRY_SNAPSHOT", "EVIDENCE_SNAPSHOT", "EVIDENCE_ASSESSMENT", "PAYLOAD"}
    assert "human_reviewed" not in json.dumps(report)
    assert "release_approved" not in json.dumps(report)


def test_v1_schema_is_unchanged_and_v2_requires_timestamp_permission() -> None:
    legacy_schema = json.loads((ROOT / "schemas" / "media-source-authorization.schema.json").read_text(encoding="utf-8"))
    assert legacy_schema["properties"]["schema_version"]["const"] == "1.0"
    assert "can_generate_timestamps" not in legacy_schema["$defs"]["permissions"]["required"]
    value = _authorization(_wav_bytes(), b"{}")
    del value["permissions"]["can_generate_timestamps"]  # type: ignore[index]
    value["authorization_id"] = identity("mediaauth", value, "authorization_id")
    with pytest.raises(SchemaValidationError):
        validate_instance(value, "media-source-authorization-v2")


def test_assessor_tampered_snapshot_is_unverified_and_prepare_fails_closed(tmp_path: Path) -> None:
    authorization, evidence_root, assessment, receipt, payload, _ = _inputs(tmp_path)
    (evidence_root / "permission.json").write_text("{}", encoding="utf-8")
    result = assess_evidence(authorization_path=authorization, evidence_root=evidence_root, assessment_path=assessment, assessed_at="2026-09-08T00:30:00Z")
    assert result["overall_result"] == "UNVERIFIED"
    assert {item["result"] for item in result["operation_results"]} == {"UNVERIFIED"}
    with pytest.raises(MediaIngestionError, match="UNVERIFIED"):
        prepare_v2(authorization_path=authorization, payload_path=payload, registry_path=REGISTRY, assessment_path=assessment, receipt_path=receipt, acquired_at="2026-09-08T01:00:00Z")


def test_malformed_external_runner_capture_degrades_to_unverified(tmp_path: Path) -> None:
    authorization, evidence_root, assessment, _, _, _ = _inputs(tmp_path)
    capture = tmp_path / "capture.json"; capture.write_text('{"overall_result":"APPROVED"}', encoding="utf-8")
    result = assess_evidence(authorization_path=authorization, evidence_root=evidence_root, assessment_path=assessment, assessed_at="2026-09-08T00:30:00Z", external_capture_path=capture)
    assert result["overall_result"] == "UNVERIFIED"
    assert result["rights_granted"] is False
    assert all(item["external_result"] == "UNVERIFIED" for item in result["operation_results"])


def test_run_v2_quarantines_payload_hash_size_drift_and_verifier_records_mismatch(tmp_path: Path) -> None:
    authorization, evidence_root, assessment, receipt, payload = _prepared(tmp_path)
    payload.write_bytes(payload.read_bytes() + b"changed")
    directory = run_v2(authorization_path=authorization, receipt_path=receipt, payload_path=payload, registry_path=REGISTRY, assessment_path=assessment, evidence_root=evidence_root, data_root=tmp_path / "data", completed_at="2026-09-08T02:00:00Z")
    assert directory.parent.name == "quarantine"
    verification = verify_v2(run_directory=directory)
    assert verification["payload_matches_authorization"] is False
    assert verification["expected_payload_bytes"] != verification["observed_payload_bytes"]


def test_verifier_reloads_retained_registry_and_rejects_tampering(tmp_path: Path) -> None:
    authorization, evidence_root, assessment, receipt, payload = _prepared(tmp_path)
    directory = run_v2(authorization_path=authorization, receipt_path=receipt, payload_path=payload, registry_path=REGISTRY, assessment_path=assessment, evidence_root=evidence_root, data_root=tmp_path / "data", completed_at="2026-09-08T02:00:00Z")
    registry = directory / "registry-snapshot.yaml"; registry.write_bytes(registry.read_bytes() + b"\n# drift\n")
    with pytest.raises(MediaIngestionError, match="inventoried file drift"):
        verify_v2(run_directory=directory)


def test_cli_assesses_local_v2_evidence(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    authorization, evidence_root, assessment, _, _, _ = _inputs(tmp_path)
    assert main([
        "assess-evidence-v2", "--authorization", str(authorization), "--evidence-root", str(evidence_root),
        "--assessment", str(assessment), "--assessed-at", "2026-09-08T00:30:00Z",
    ]) == 0
    output = json.loads(capsys.readouterr().out)
    assert output["overall_result"] == "CONSISTENT"
    assert output["rights_granted"] is False


def test_v2_authorization_requires_evidence_exactly_for_true_operations(tmp_path: Path) -> None:
    authorization, evidence_root, assessment, _, _, _ = _inputs(tmp_path)
    value = json.loads(authorization.read_text(encoding="utf-8")); value["permission_evidence"] = value["permission_evidence"][:-1]
    value["authorization_id"] = identity("mediaauth", value, "authorization_id"); authorization.write_text(json.dumps(value), encoding="utf-8")
    with pytest.raises(MediaIngestionError, match="exactly the true operations"):
        assess_evidence(authorization_path=authorization, evidence_root=evidence_root, assessment_path=assessment, assessed_at="2026-09-08T00:30:00Z")
