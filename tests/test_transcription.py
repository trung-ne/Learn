from __future__ import annotations

import hashlib
import io
import json
import wave
from pathlib import Path

import pytest

from english_master.lesson_generation.canonical import identity, sha256_json
from english_master.media_ingestion.evidence_v2 import assess_evidence, prepare_v2, run_v2
from english_master.media_ingestion.service import prepare as prepare_media_v1
from english_master.media_ingestion.service import run as run_media_v1
from english_master.schema_validation import SchemaValidationError, validate_instance
from english_master.transcription.__main__ import main
from english_master.transcription.service import TranscriptionError, run, verify

ROOT = Path(__file__).resolve().parents[1]
REGISTRY = ROOT / "sources" / "registry.yaml"


def _wav_bytes() -> bytes:
    output = io.BytesIO()
    with wave.open(output, "wb") as stream:
        stream.setnchannels(1)
        stream.setsampwidth(2)
        stream.setframerate(8000)
        stream.writeframes(b"\x00\x00" * 800)
    return output.getvalue()


def _parent_media_v2(tmp_path: Path, *, transcript_allowed: bool = True) -> Path:
    payload = _wav_bytes()
    payload_path = tmp_path / "fixture.wav"
    payload_path.write_bytes(payload)
    true_operations = ["can_download_audio", "can_store", "can_generate_timestamps"]
    if transcript_allowed:
        true_operations.append("can_generate_transcript")
    permissions = {
        "can_download_audio": True,
        "can_download_video": False,
        "can_store": True,
        "can_clip": False,
        "can_transform": False,
        "can_extract_audio": False,
        "can_generate_transcript": transcript_allowed,
        "can_generate_timestamps": True,
        "can_redistribute": False,
    }
    evidence_payload = json.dumps(
        {"permissions": {key: True for key in true_operations}}, sort_keys=True
    ).encode()
    evidence_root = tmp_path / "evidence"
    evidence_root.mkdir()
    (evidence_root / "permission.json").write_bytes(evidence_payload)
    evidence_hash = hashlib.sha256(evidence_payload).hexdigest()
    authorization: dict[str, object] = {
        "schema_version": "2.0",
        "record_type": "media_source_authorization",
        "authorization_id": "PENDING",
        "authorization_mode": "OFFLINE_TEST_FIXTURE_ONLY",
        "fixture_only": True,
        "registry_path": "sources/registry.yaml",
        "registry_sha256": hashlib.sha256(REGISTRY.read_bytes()).hexdigest(),
        "source_id": "src_tatoeba_audio_cc_by_4",
        "source_status": "APPROVED",
        "source_url": "https://tatoeba.org/en/downloads",
        "source_record_id": f"m13-v2-fixture-{int(transcript_allowed)}",
        "official_record_url": f"https://tatoeba.org/en/downloads/m13-v2-fixture-{int(transcript_allowed)}",
        "media_kind": "AUDIO",
        "expected_filename": "fixture.wav",
        "expected_payload_sha256": hashlib.sha256(payload).hexdigest(),
        "expected_payload_bytes": len(payload),
        "expected_mime_type": "audio/wav",
        "expected_metadata": {"duration_ms": 100, "container": "WAV", "codecs": ["PCM_S16LE"], "width": None, "height": None},
        "license": "CC-BY-4.0",
        "license_url": "https://creativecommons.org/licenses/by/4.0/legalcode.en",
        "attribution": "M13 local test fixture.",
        "permissions": permissions,
        "permission_evidence": [
            {
                "operation": operation,
                "snapshot_path": "permission.json",
                "snapshot_sha256": evidence_hash,
                "snapshot_bytes": len(evidence_payload),
                "locator": {"kind": "JSON_POINTER", "pointer": f"/permissions/{operation}"},
                "located_value_sha256": hashlib.sha256(b"true").hexdigest(),
                "evidence_note": "Record-specific local fixture evidence only.",
            }
            for operation in true_operations
        ],
        "authorized_at": "2026-09-08T00:00:00Z",
        "expires_at": "2026-09-10T00:00:00Z",
    }
    authorization["authorization_id"] = identity("mediaauth", authorization, "authorization_id")
    authorization_path = tmp_path / "media-authorization-v2.json"
    authorization_path.write_text(json.dumps(authorization), encoding="utf-8")
    assessment_path = tmp_path / "media-assessment.json"
    receipt_path = tmp_path / "media-receipt-v2.json"
    assess_evidence(
        authorization_path=authorization_path,
        evidence_root=evidence_root,
        assessment_path=assessment_path,
        assessed_at="2026-09-08T00:20:00Z",
    )
    prepare_v2(
        authorization_path=authorization_path,
        payload_path=payload_path,
        registry_path=REGISTRY,
        assessment_path=assessment_path,
        receipt_path=receipt_path,
        acquired_at="2026-09-08T00:30:00Z",
    )
    return run_v2(
        authorization_path=authorization_path,
        receipt_path=receipt_path,
        payload_path=payload_path,
        registry_path=REGISTRY,
        assessment_path=assessment_path,
        evidence_root=evidence_root,
        data_root=tmp_path / "media-data",
        completed_at="2026-09-08T01:00:00Z",
    )


def _permission_bindings(parent_authorization: dict[str, object], assessment: dict[str, object]) -> list[dict[str, object]]:
    parent_entries = {item["operation"]: item for item in parent_authorization["permission_evidence"]}  # type: ignore[index]
    assessment_entries = {item["operation"]: item for item in assessment["operation_results"]}  # type: ignore[index]
    result = []
    for operation, parent_key in (("transcript_generation", "can_generate_transcript"), ("timestamp_generation", "can_generate_timestamps")):
        parent_entry = parent_entries[parent_key]
        assessment_entry = assessment_entries[parent_key]
        result.append({
            "operation": operation,
            "parent_permission_key": parent_key,
            "parent_permission_evidence_sha256": sha256_json(parent_entry),
            "snapshot_path": parent_entry["snapshot_path"],
            "snapshot_sha256": parent_entry["snapshot_sha256"],
            "snapshot_bytes": parent_entry["snapshot_bytes"],
            "locator": parent_entry["locator"],
            "located_value_sha256": parent_entry["located_value_sha256"],
            "parent_assessment_result_sha256": sha256_json(assessment_entry),
            "retained_snapshot_path": f"evidence-{'transcript' if operation == 'transcript_generation' else 'timestamp'}.snapshot",
        })
    return result


def _inputs(tmp_path: Path, *, transcript_allowed: bool = True, segments: list[dict[str, object]] | None = None) -> tuple[Path, Path, Path]:
    media = _parent_media_v2(tmp_path, transcript_allowed=transcript_allowed)
    report = json.loads((media / "run-report.json").read_text(encoding="utf-8"))
    asset = json.loads((media / "asset-metadata.json").read_text(encoding="utf-8"))
    receipt = json.loads((media / "acquisition-receipt.json").read_text(encoding="utf-8"))
    verification = json.loads((media / "verification-report.json").read_text(encoding="utf-8"))
    parent_authorization = json.loads((media / "authorization.json").read_text(encoding="utf-8"))
    assessment = json.loads((media / "evidence-assessment.json").read_text(encoding="utf-8"))
    permission_evidence = _permission_bindings(parent_authorization, assessment) if transcript_allowed else []
    authorization: dict[str, object] = {
        "schema_version": "2.0", "record_type": "transcription_authorization", "authorization_id": "PENDING",
        "authorization_mode": "OFFLINE_TEST_FIXTURE_ONLY", "fixture_only": True,
        "registry_path": "sources/registry.yaml", "registry_sha256": hashlib.sha256(REGISTRY.read_bytes()).hexdigest(),
        "media_run_path": f"media-data/media/originals/{media.name}", "media_schema_version": "2.0",
        "media_run_id": report["run_id"], "media_run_report_sha256": sha256_json(report),
        "media_acquisition_receipt_id": receipt["receipt_id"], "media_acquisition_receipt_sha256": sha256_json(receipt),
        "media_verification_id": verification["verification_id"], "media_verification_sha256": sha256_json(verification),
        "media_evidence_assessment_id": assessment["assessment_id"], "media_evidence_assessment_sha256": sha256_json(assessment),
        "media_asset_id": asset["asset_id"], "media_asset_sha256": sha256_json(asset), "media_payload_sha256": asset["payload_sha256"],
        "source_id": asset["source_id"], "source_record_id": asset["source_record_id"], "media_kind": "AUDIO", "media_duration_ms": 100,
        "permissions": {"transcript_generation": True, "timestamp_generation": True},
        "permission_evidence": permission_evidence, "permission_basis": "M12_V2_RECORD_EVIDENCE_AND_ASSESSMENT",
        "authorized_at": "2026-09-08T02:00:00Z", "expires_at": "2026-09-08T06:00:00Z",
    }
    authorization["authorization_id"] = identity("transauth", authorization, "authorization_id")
    authorization_path = tmp_path / "transcription-authorization.json"
    authorization_path.write_text(json.dumps(authorization), encoding="utf-8")
    fixture_segments = segments or [
        {"sequence": 1, "start_ms": 0, "end_ms": 40, "speaker_label": "SPEAKER_01", "text": "Hello there."},
        {"sequence": 2, "start_ms": 40, "end_ms": 90, "speaker_label": "SPEAKER_02", "text": "Hello!"},
    ]
    request: dict[str, object] = {
        "schema_version": "2.0", "record_type": "transcription_request", "request_id": "PENDING",
        "authorization_id": authorization["authorization_id"], "authorization_sha256": sha256_json(authorization),
        "media_run_id": report["run_id"], "media_asset_id": asset["asset_id"], "media_payload_sha256": asset["payload_sha256"],
        "language": "en", "speaker_label_policy": "ANONYMIZED_SEQUENTIAL", "transcription_method": "DETERMINISTIC_INLINE_FIXTURE",
        "processing_constraints": {"read_parent_media": False, "decode_media": False, "extract_audio": False, "transform_media": False, "invoke_external_process": False, "access_network": False},
        "fixture_segments": fixture_segments, "fixture_segments_sha256": sha256_json(fixture_segments),
        "requested_at": "2026-09-08T03:00:00Z", "fixture_only": True,
    }
    request["request_id"] = identity("transreq", request, "request_id")
    request_path = tmp_path / "transcription-request.json"
    request_path.write_text(json.dumps(request), encoding="utf-8")
    return authorization_path, request_path, media


def _run(tmp_path: Path) -> Path:
    authorization, request, media = _inputs(tmp_path)
    return run(authorization_path=authorization, request_path=request, media_run_directory=media, registry_path=REGISTRY, data_root=tmp_path / "transcript-data", started_at="2026-09-08T04:00:00Z", completed_at="2026-09-08T05:00:00Z")


def test_hardened_fixture_run_and_read_only_verification(tmp_path: Path) -> None:
    directory = _run(tmp_path)
    assert verify(run_directory=directory)["result"] == "PASS"
    artifact = json.loads((directory / "transcript-artifact.json").read_text(encoding="utf-8"))
    plan = json.loads((directory / "processing-plan.json").read_text(encoding="utf-8"))
    manifest = json.loads((directory / "run-manifest.json").read_text(encoding="utf-8"))
    assert artifact["full_text"] == "Hello there. Hello!"
    assert artifact["speaker_labels"] == ["SPEAKER_01", "SPEAKER_02"]
    assert artifact["tool"] == plan["tool"]
    assert artifact["model"] == {"invoked": False, "provider": None, "name": None, "version": None, "model_file_sha256": None}
    assert not any(plan["operations"].values())
    assert artifact["parent_media_read"] is False and artifact["media_transformed"] is False
    roles = {item["role"] for item in manifest["inventory"]}
    assert {"PROCESSING_PLAN", "PARENT_PERMISSION_EVIDENCE"} <= roles
    assert len(manifest["stage_receipts"]) == 5


def test_new_run_rejects_m12_v1_parent(tmp_path: Path) -> None:
    payload = _wav_bytes(); payload_path = tmp_path / "legacy.wav"; payload_path.write_bytes(payload)
    permissions = {"can_download_audio": True, "can_download_video": False, "can_store": True, "can_clip": False, "can_transform": False, "can_extract_audio": False, "can_generate_transcript": True, "can_redistribute": False}
    auth: dict[str, object] = {
        "schema_version": "1.0", "record_type": "media_source_authorization", "authorization_id": "PENDING", "authorization_mode": "OFFLINE_TEST_FIXTURE_ONLY", "fixture_only": True,
        "registry_path": "sources/registry.yaml", "registry_sha256": hashlib.sha256(REGISTRY.read_bytes()).hexdigest(), "source_id": "src_tatoeba_audio_cc_by_4", "source_status": "APPROVED", "source_url": "https://tatoeba.org/en/downloads",
        "source_record_id": "legacy-m13", "official_record_url": "https://tatoeba.org/en/downloads/legacy-m13", "media_kind": "AUDIO", "expected_filename": "legacy.wav",
        "expected_payload_sha256": hashlib.sha256(payload).hexdigest(), "expected_payload_bytes": len(payload), "expected_mime_type": "audio/wav", "expected_metadata": {"duration_ms": 100, "container": "WAV", "codecs": ["PCM_S16LE"], "width": None, "height": None},
        "license": "CC-BY-4.0", "license_url": "https://creativecommons.org/licenses/by/4.0/legalcode.en", "attribution": "legacy fixture", "permissions": permissions,
        "permission_evidence": [{"operation": key, "evidence_url": "https://tatoeba.org/en/downloads", "evidence_note": "fixture"} for key in permissions],
        "authorized_at": "2026-09-08T00:00:00Z", "expires_at": "2026-09-10T00:00:00Z",
    }
    auth["authorization_id"] = identity("mediaauth", auth, "authorization_id")
    auth_path = tmp_path / "legacy-auth.json"; auth_path.write_text(json.dumps(auth), encoding="utf-8")
    receipt_path = tmp_path / "legacy-receipt.json"
    prepare_media_v1(authorization_path=auth_path, payload_path=payload_path, registry_path=REGISTRY, receipt_path=receipt_path, acquired_at="2026-09-08T00:30:00Z")
    parent = run_media_v1(authorization_path=auth_path, receipt_path=receipt_path, payload_path=payload_path, registry_path=REGISTRY, data_root=tmp_path / "legacy-data", completed_at="2026-09-08T01:00:00Z")
    new_root = tmp_path / "new"; new_root.mkdir()
    good_auth, request, _ = _inputs(new_root)
    hardened = json.loads(good_auth.read_text(encoding="utf-8"))
    hardened["media_run_path"] = f"legacy-data/media/originals/{parent.name}"
    hardened["authorization_id"] = identity("transauth", hardened, "authorization_id")
    good_auth.write_text(json.dumps(hardened), encoding="utf-8")
    request_value = json.loads(request.read_text(encoding="utf-8"))
    request_value["authorization_id"] = hardened["authorization_id"]
    request_value["authorization_sha256"] = sha256_json(hardened)
    request_value["request_id"] = identity("transreq", request_value, "request_id")
    request.write_text(json.dumps(request_value), encoding="utf-8")
    with pytest.raises(TranscriptionError, match="M12 v2 parent"):
        run(authorization_path=good_auth, request_path=request, media_run_directory=parent, registry_path=REGISTRY, data_root=tmp_path / "out", started_at="2026-09-08T04:00:00Z", completed_at="2026-09-08T05:00:00Z")


def test_record_level_transcript_permission_evidence_is_required(tmp_path: Path) -> None:
    authorization, request, media = _inputs(tmp_path, transcript_allowed=False)
    with pytest.raises(TranscriptionError, match="permission_evidence"):
        run(authorization_path=authorization, request_path=request, media_run_directory=media, registry_path=REGISTRY, data_root=tmp_path / "out", started_at="2026-09-08T04:00:00Z", completed_at="2026-09-08T05:00:00Z")


def test_tampered_record_permission_binding_fails_closed(tmp_path: Path) -> None:
    authorization, request, media = _inputs(tmp_path)
    value = json.loads(authorization.read_text(encoding="utf-8"))
    value["permission_evidence"][0]["located_value_sha256"] = "0" * 64
    value["authorization_id"] = identity("transauth", value, "authorization_id")
    authorization.write_text(json.dumps(value), encoding="utf-8")
    request_value = json.loads(request.read_text(encoding="utf-8"))
    request_value["authorization_id"] = value["authorization_id"]
    request_value["authorization_sha256"] = sha256_json(value)
    request_value["request_id"] = identity("transreq", request_value, "request_id")
    request.write_text(json.dumps(request_value), encoding="utf-8")
    with pytest.raises(TranscriptionError, match="evidence binding drift"):
        run(authorization_path=authorization, request_path=request, media_run_directory=media, registry_path=REGISTRY, data_root=tmp_path / "out", started_at="2026-09-08T04:00:00Z", completed_at="2026-09-08T05:00:00Z")


def test_request_cannot_enable_media_read_or_transform(tmp_path: Path) -> None:
    authorization, request, media = _inputs(tmp_path)
    value = json.loads(request.read_text(encoding="utf-8"))
    value["processing_constraints"]["read_parent_media"] = True
    value["request_id"] = identity("transreq", value, "request_id")
    request.write_text(json.dumps(value), encoding="utf-8")
    with pytest.raises(TranscriptionError, match="read_parent_media"):
        run(authorization_path=authorization, request_path=request, media_run_directory=media, registry_path=REGISTRY, data_root=tmp_path / "out", started_at="2026-09-08T04:00:00Z", completed_at="2026-09-08T05:00:00Z")


@pytest.mark.parametrize("segments", [
    [{"sequence": 1, "start_ms": 0, "end_ms": 60, "speaker_label": "SPEAKER_01", "text": "One."}, {"sequence": 2, "start_ms": 50, "end_ms": 80, "speaker_label": "SPEAKER_01", "text": "Two."}],
    [{"sequence": 1, "start_ms": 0, "end_ms": 40, "speaker_label": "SPEAKER_02", "text": "Not sequential."}],
])
def test_segment_order_and_anonymized_speaker_policy(tmp_path: Path, segments: list[dict[str, object]]) -> None:
    authorization, request, media = _inputs(tmp_path, segments=segments)
    with pytest.raises(TranscriptionError, match="segment timestamps|speaker labels"):
        run(authorization_path=authorization, request_path=request, media_run_directory=media, registry_path=REGISTRY, data_root=tmp_path / "out", started_at="2026-09-08T04:00:00Z", completed_at="2026-09-08T05:00:00Z")


def test_immutable_closed_inventory_permission_snapshot_and_no_overwrite(tmp_path: Path) -> None:
    authorization, request, media = _inputs(tmp_path)
    kwargs = dict(authorization_path=authorization, request_path=request, media_run_directory=media, registry_path=REGISTRY, data_root=tmp_path / "out", started_at="2026-09-08T04:00:00Z", completed_at="2026-09-08T05:00:00Z")
    directory = run(**kwargs)
    with pytest.raises(FileExistsError):
        run(**kwargs)
    evidence = directory / "evidence-transcript.snapshot"
    evidence.write_bytes(evidence.read_bytes() + b"drift")
    with pytest.raises(TranscriptionError, match="inventoried file drift"):
        verify(run_directory=directory)


def test_closed_inventory_rejects_unexpected_file(tmp_path: Path) -> None:
    directory = _run(tmp_path)
    (directory / "extra.txt").write_text("drift", encoding="utf-8")
    with pytest.raises(TranscriptionError, match="closed inventory"):
        verify(run_directory=directory)


def test_cli_rejects_url_paths() -> None:
    with pytest.raises(SystemExit):
        main(["verify", "--run-directory", "https://example.test/run"])


def test_v2_schema_rejects_invented_model_provenance() -> None:
    plan_schema_candidate = {
        "schema_version": "2.0", "record_type": "transcription_processing_plan", "plan_id": "transplan_" + "0" * 64,
        "authorization_id": "transauth_" + "0" * 64, "authorization_sha256": "0" * 64,
        "request_id": "transreq_" + "0" * 64, "request_sha256": "0" * 64,
        "planned_at": "2026-09-08T00:00:00Z", "processing_mode": "INLINE_FIXTURE_COPY_NO_MEDIA_ACCESS", "input_kind": "CALLER_AUTHORED_INLINE_SEGMENTS",
        "operations": {"read_parent_media": False, "decode_media": False, "extract_audio": False, "transform_media": False, "invoke_external_process": False, "access_network": False},
        "tool": {"name": "english_master.transcription.fixture_copy", "version": "2.0", "implementation": "PROJECT_PYTHON"},
        "model": {"invoked": False, "provider": "claimed-provider", "name": None, "version": None, "model_file_sha256": None},
        "parameters": {"segment_source": "INLINE_REQUEST", "text_join_separator": " ", "timestamp_unit": "MILLISECONDS", "text_normalization": "NONE_EXACT_COPY", "speaker_label_policy": "ANONYMIZED_SEQUENTIAL"},
        "fixture_segments_sha256": "0" * 64, "fixture_only": True,
    }
    with pytest.raises(SchemaValidationError):
        validate_instance(plan_schema_candidate, "transcription-processing-plan-v2")
