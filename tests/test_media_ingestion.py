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
from english_master.media_ingestion.service import MediaIngestionError, prepare, run, verify
from english_master.schema_validation import SchemaValidationError, validate_instance

ROOT = Path(__file__).resolve().parents[1]
REGISTRY = ROOT / "sources" / "registry.yaml"


def _wav_bytes() -> bytes:
    output = io.BytesIO()
    with wave.open(output, "wb") as stream:
        stream.setnchannels(1)
        stream.setsampwidth(2)
        stream.setframerate(8000)
        stream.writeframes(b"\x00\x00" * 80)
    return output.getvalue()


def _authorization(payload: bytes, filename: str = "fixture.wav") -> dict[str, object]:
    permissions = {
        "can_download_audio": True,
        "can_download_video": False,
        "can_store": True,
        "can_clip": False,
        "can_transform": False,
        "can_extract_audio": False,
        "can_generate_transcript": False,
        "can_redistribute": False,
    }
    value: dict[str, object] = {
        "schema_version": "1.0",
        "record_type": "media_source_authorization",
        "authorization_id": "PENDING",
        "authorization_mode": "OFFLINE_TEST_FIXTURE_ONLY",
        "fixture_only": True,
        "registry_path": "sources/registry.yaml",
        "registry_sha256": hashlib.sha256(REGISTRY.read_bytes()).hexdigest(),
        "source_id": "src_tatoeba_audio_cc_by_4",
        "source_status": "APPROVED",
        "source_url": "https://tatoeba.org/en/downloads",
        "source_record_id": "fixture-audio-001",
        "official_record_url": "https://tatoeba.org/en/downloads/fixture-audio-001",
        "media_kind": "AUDIO",
        "expected_filename": filename,
        "expected_payload_sha256": hashlib.sha256(payload).hexdigest(),
        "expected_payload_bytes": len(payload),
        "expected_mime_type": "audio/wav",
        "expected_metadata": {"duration_ms": 10, "container": "WAV", "codecs": ["PCM_S16LE"], "width": None, "height": None},
        "license": "CC-BY-4.0",
        "license_url": "https://creativecommons.org/licenses/by/4.0/legalcode.en",
        "attribution": "Offline test fixture attributed to the test suite; not an external media record.",
        "permissions": permissions,
        "permission_evidence": [
            {"operation": operation, "evidence_url": "https://tatoeba.org/en/downloads", "evidence_note": "Explicit fixture-record test authorization."}
            for operation in permissions
        ],
        "authorized_at": "2026-09-08T00:00:00Z",
        "expires_at": "2026-09-09T00:00:00Z",
    }
    value["authorization_id"] = identity("mediaauth", value, "authorization_id")
    return value


def _prepared(tmp_path: Path) -> tuple[Path, Path, Path, bytes]:
    payload = _wav_bytes()
    payload_path = tmp_path / "fixture.wav"
    payload_path.write_bytes(payload)
    authorization_path = tmp_path / "authorization.json"
    authorization_path.write_text(json.dumps(_authorization(payload)), encoding="utf-8")
    receipt_path = tmp_path / "receipt.json"
    prepare(
        authorization_path=authorization_path,
        payload_path=payload_path,
        registry_path=REGISTRY,
        receipt_path=receipt_path,
        acquired_at="2026-09-08T01:00:00Z",
    )
    return authorization_path, receipt_path, payload_path, payload


def test_prepare_run_verify_offline_fixture(tmp_path: Path) -> None:
    authorization, receipt, payload, _ = _prepared(tmp_path)
    directory = run(
        authorization_path=authorization,
        receipt_path=receipt,
        payload_path=payload,
        registry_path=REGISTRY,
        data_root=tmp_path / "data",
        completed_at="2026-09-08T02:00:00Z",
    )
    assert directory.parent.name == "originals"
    assert verify(run_directory=directory)["result"] == "PASS"
    report = json.loads((directory / "run-report.json").read_text(encoding="utf-8"))
    assert report["outcome"] == "STORED"
    assert report["fixture_only"] is True
    assert report["network_accessed"] is False
    assert report["content_lifecycle_status"] == "UNREVIEWED"
    assert "human_reviewed" not in json.dumps(report)
    assert "release_approved" not in json.dumps(report)


def test_changed_payload_is_quarantined(tmp_path: Path) -> None:
    authorization, receipt, payload, content = _prepared(tmp_path)
    payload.write_bytes(content + b"changed")
    directory = run(authorization_path=authorization, receipt_path=receipt, payload_path=payload, registry_path=REGISTRY, data_root=tmp_path / "data", completed_at="2026-09-08T02:00:00Z")
    assert directory.parent.name == "quarantine"
    report = json.loads((directory / "run-report.json").read_text(encoding="utf-8"))
    assert report["outcome"] == "QUARANTINED"
    assert verify(run_directory=directory)["result"] == "PASS"


def test_record_permission_must_not_exceed_registry(tmp_path: Path) -> None:
    payload = _wav_bytes()
    authorization = _authorization(payload)
    authorization["permissions"]["can_download_video"] = True  # type: ignore[index]
    authorization["authorization_id"] = identity("mediaauth", authorization, "authorization_id")
    authorization_path = tmp_path / "authorization.json"
    authorization_path.write_text(json.dumps(authorization), encoding="utf-8")
    payload_path = tmp_path / "fixture.wav"
    payload_path.write_bytes(payload)
    with pytest.raises(MediaIngestionError, match="exceeds source registry"):
        prepare(authorization_path=authorization_path, payload_path=payload_path, registry_path=REGISTRY, receipt_path=tmp_path / "receipt.json", acquired_at="2026-09-08T01:00:00Z")


def test_schema_rejects_traversal_filename() -> None:
    authorization = _authorization(_wav_bytes())
    authorization["expected_filename"] = "../fixture.wav"
    authorization["authorization_id"] = identity("mediaauth", authorization, "authorization_id")
    with pytest.raises(SchemaValidationError):
        validate_instance(authorization, "media-source-authorization")


def test_duplicate_source_identity_is_quarantined(tmp_path: Path) -> None:
    authorization, receipt, payload, _ = _prepared(tmp_path)
    first = run(authorization_path=authorization, receipt_path=receipt, payload_path=payload, registry_path=REGISTRY, data_root=tmp_path / "data", completed_at="2026-09-08T02:00:00Z")
    second = run(authorization_path=authorization, receipt_path=receipt, payload_path=payload, registry_path=REGISTRY, data_root=tmp_path / "data", completed_at="2026-09-08T03:00:00Z")
    assert first.parent.name == "originals"
    assert second.parent.name == "quarantine"


def test_verifier_rejects_hash_drift_and_extra_files(tmp_path: Path) -> None:
    authorization, receipt, payload, _ = _prepared(tmp_path)
    directory = run(authorization_path=authorization, receipt_path=receipt, payload_path=payload, registry_path=REGISTRY, data_root=tmp_path / "data", completed_at="2026-09-08T02:00:00Z")
    (directory / "extra.txt").write_text("orphan", encoding="utf-8")
    with pytest.raises(MediaIngestionError, match="closed inventory"):
        verify(run_directory=directory)
    (directory / "extra.txt").unlink()
    stored_payload = next((directory / "payload").iterdir())
    stored_payload.write_bytes(stored_payload.read_bytes() + b"drift")
    with pytest.raises(MediaIngestionError, match="inventoried file drift"):
        verify(run_directory=directory)


def test_no_overwrite_and_cli_rejects_urls(tmp_path: Path) -> None:
    authorization, receipt, payload, _ = _prepared(tmp_path)
    kwargs = dict(authorization_path=authorization, receipt_path=receipt, payload_path=payload, registry_path=REGISTRY, data_root=tmp_path / "data", completed_at="2026-09-08T02:00:00Z")
    run(**kwargs)
    duplicate = dict(kwargs)
    duplicate["completed_at"] = "2026-09-08T03:00:00Z"
    run(**duplicate)
    with pytest.raises(FileExistsError):
        run(**duplicate)
    with pytest.raises(SystemExit):
        main(["verify", "--run-directory", "https://example.test/run"])


def test_symlink_payload_is_rejected_when_supported(tmp_path: Path) -> None:
    _, _, payload, _ = _prepared(tmp_path)
    link = tmp_path / "linked.wav"
    try:
        link.symlink_to(payload)
    except OSError:
        pytest.skip("symlinks unavailable")
    authorization = _authorization(payload.read_bytes(), filename="linked.wav")
    authorization_path = tmp_path / "linked-authorization.json"
    authorization_path.write_text(json.dumps(authorization), encoding="utf-8")
    with pytest.raises(MediaIngestionError, match="regular local file"):
        prepare(authorization_path=authorization_path, payload_path=link, registry_path=REGISTRY, receipt_path=tmp_path / "linked-receipt.json", acquired_at="2026-09-08T01:00:00Z")
