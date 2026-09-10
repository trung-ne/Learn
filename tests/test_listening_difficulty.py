from __future__ import annotations

import json
from copy import deepcopy
from pathlib import Path

import pytest

from english_master.lesson_generation.canonical import identity, sha256_json
from english_master.listening_difficulty.__main__ import main
from english_master.listening_difficulty.service import (
    FEATURE_ORDER,
    ListeningDifficultyError,
    analyze,
    bind_acoustic_sidecar,
    bind_fixture,
    project_m13,
    run,
    verify,
)

ROOT = Path(__file__).resolve().parents[1]
REGISTRY = ROOT / "sources" / "registry.yaml"


def _fixture() -> dict[str, object]:
    value: dict[str, object] = {
        "schema_version": "1.0",
        "record_type": "listening_transcription_fixture",
        "transcription_id": "PENDING",
        "payload_sha256": "0" * 64,
        "fixture_only": True,
        "network_accessed": False,
        "media_accessed": False,
        "model_accessed": False,
        "verification": {
            "result": "PASS",
            "method": "VERIFIED_M13_FIXTURE_PROJECTION",
            "transcription_run_id": "transrun_" + "1" * 64,
            "transcription_manifest_sha256": "2" * 64,
            "transcription_verification_id": "transverify_" + "3" * 64,
            "transcription_verification_sha256": "4" * 64,
            "transcript_artifact_id": "transcript_" + "5" * 64,
            "transcript_artifact_sha256": "6" * 64,
            "media_schema_version": "1.0",
            "media_run_id": "mediarun_" + "7" * 64,
            "media_asset_id": "mediaasset_" + "8" * 64,
            "media_payload_sha256": "9" * 64,
        },
        "transcript": {
            "language": "en",
            "utterances": [
                {"text": "First, I called because the train was late.", "speaker_id": "speaker_a", "start_ms": 0, "end_ms": 4000},
                {"text": "However, we can meet after it arrives.", "speaker_id": "speaker_b", "start_ms": 3500, "end_ms": 7500},
            ],
        },
        "limitations": ["Internal synthetic JSON fixture; not publication authority."],
    }
    return bind_fixture(value)


def _sidecar(fixture: dict[str, object]) -> dict[str, object]:
    return bind_acoustic_sidecar({
        "schema_version": "1.0",
        "record_type": "listening_acoustic_fixture_sidecar",
        "sidecar_id": "PENDING",
        "payload_sha256": "PENDING",
        "evidence_origin": "SYNTHETIC_ACOUSTIC_FIXTURE",
        "feature_annotations": [{
            "feature": "noise",
            "score": 35,
            "confidence": "LOW",
            "fixture_evidence": [{
                "fixture_record_id": "m14_test_tone_001",
                "locator": "annotation.noise",
                "statement": "Synthetic fixture specification declares steady background noise.",
            }],
            "method": {"name": "fixed_fixture_annotation", "version": "1.0", "parameters": {}},
            "limitations": ["No audio was accessed or measured."],
        }],
        "fixture_only": True,
        "network_accessed": False,
        "media_accessed": False,
        "model_accessed": False,
        "limitations": ["Synthetic sidecar only; not an observed acoustic measurement."],
    }, fixture)


def _m13_run(tmp_path: Path) -> Path:
    from english_master.transcription.service import run as run_transcription
    from test_transcription import _inputs

    authorization, request, media = _inputs(tmp_path)
    return run_transcription(
        authorization_path=authorization,
        request_path=request,
        media_run_directory=media,
        registry_path=REGISTRY,
        data_root=tmp_path / "transcription-runs",
        started_at="2026-09-08T04:00:00Z",
        completed_at="2026-09-08T05:00:00Z",
    )


def _write(path: Path, value: dict[str, object]) -> None:
    path.write_text(json.dumps(value, ensure_ascii=False, sort_keys=True), encoding="utf-8")


def _rebind_fixture(value: dict[str, object]) -> dict[str, object]:
    rebound = deepcopy(value)
    payload = deepcopy(rebound)
    payload.pop("transcription_id", None)
    payload.pop("payload_sha256", None)
    rebound["payload_sha256"] = sha256_json(payload)
    rebound["transcription_id"] = identity("ldtx", rebound, "transcription_id")
    return rebound


def test_internal_analysis_has_provenance_confidence_contribution_and_lifecycle() -> None:
    fixture = _fixture()
    profile = analyze(fixture, _sidecar(fixture))
    assert profile["composite"]["status"] == "SCORED"
    assert profile["composite"]["confidence"] == "LOW"
    assert profile["content_status"] == "UNREVIEWED"
    assert profile["publication_status"] == "INTERNAL_ANALYSIS_ONLY"
    assert profile["validation_tier"] == "INTERNAL_ANALYSIS_ONLY"
    assert profile["human_reviewed"] is False
    assert profile["release_approved"] is False
    assert [entry["feature"] for entry in profile["feature_ledger"]] == list(FEATURE_ORDER)
    assert all(entry["evidence"][0]["source_sha256"] for entry in profile["feature_ledger"])
    included = [entry for entry in profile["feature_ledger"] if entry["contribution"]["included_in_composite"]]
    assert sum(entry["contribution"]["weight"] for entry in included) == pytest.approx(1.0)


def test_arbitrary_json_can_be_analyzed_but_cannot_be_published(tmp_path: Path) -> None:
    assert analyze(_fixture())["composite"]["status"] == "SCORED"
    input_path = tmp_path / "arbitrary.json"
    _write(input_path, _fixture())
    with pytest.raises(TypeError, match="input_path"):
        run(input_path=input_path, output_root=tmp_path / "runs")  # type: ignore[call-arg]


def test_vocabulary_only_internal_analysis_withholds_composite() -> None:
    value = _fixture()
    value["transcript"] = {"language": "en", "utterances": [{"text": "apple banana station ticket"}]}
    profile = analyze(_rebind_fixture(value))
    assert profile["composite"]["status"] == "INSUFFICIENT_EVIDENCE"
    assert profile["composite"]["score"] is None
    assert profile["composite"]["confidence"] == "NOT_ASSESSED"
    assert profile["composite"]["missing_required_features"] == [
        "grammar", "speech_rate", "discourse_complexity", "nonlexical_audio_or_interaction"
    ]
    assert not any(entry["contribution"]["included_in_composite"] for entry in profile["feature_ledger"])


def test_direct_acoustic_observations_are_rejected() -> None:
    value = _fixture()
    value["acoustic_observations"] = [{"feature": "noise", "score": 20}]
    value = _rebind_fixture(value)
    with pytest.raises(ListeningDifficultyError, match="invalid M14 analysis input"):
        analyze(value)


def test_sidecar_is_hash_bound_and_drift_fails_closed() -> None:
    fixture = _fixture()
    sidecar = _sidecar(fixture)
    drifted_fixture = deepcopy(fixture)
    drifted_fixture["limitations"] = ["changed"]
    drifted_fixture = _rebind_fixture(drifted_fixture)
    with pytest.raises(ListeningDifficultyError, match="sidecar lineage"):
        analyze(drifted_fixture, sidecar)


def test_publish_requires_verified_m13_and_inventories_receipt(tmp_path: Path) -> None:
    m13 = _m13_run(tmp_path)
    fixture = project_m13(m13)
    sidecar_path = tmp_path / "sidecar.json"
    _write(sidecar_path, _sidecar(fixture))
    directory = run(transcription_run_directory=m13, acoustic_sidecar_path=sidecar_path, output_root=tmp_path / "runs")
    receipt = verify(run_directory=directory)
    manifest = json.loads((directory / "manifest.json").read_text(encoding="utf-8"))
    assert receipt["result"] == "PASS"
    assert receipt["verification_id"] == manifest["verification_id"]
    assert (directory / "verification.json").is_file()
    assert [entry["path"] for entry in manifest["inventory"]] == ["input.json", "acoustic-sidecar.json", "profile.json", "verification.json"]
    assert manifest["content_status"] == "UNREVIEWED"
    assert manifest["validation_tier"] == "MACHINE_VALIDATED"

    second = run(transcription_run_directory=m13, acoustic_sidecar_path=sidecar_path, output_root=tmp_path / "second-runs")
    assert second.name == directory.name
    assert {path.name: path.read_bytes() for path in sorted(directory.iterdir())} == {path.name: path.read_bytes() for path in sorted(second.iterdir())}


def test_project_m13_preserves_lineage_and_has_no_acoustics(tmp_path: Path) -> None:
    m13 = _m13_run(tmp_path)
    fixture = project_m13(m13)
    assert fixture["verification"]["method"] == "VERIFIED_M13_FIXTURE_PROJECTION"
    assert fixture["verification"]["media_schema_version"] == "2.0"
    assert fixture["transcript"]["utterances"][0]["speaker_id"] == "speaker_01"
    assert "acoustic_observations" not in fixture


def test_publish_rejects_non_m13_directory(tmp_path: Path) -> None:
    fake = tmp_path / "fake-m13"
    fake.mkdir()
    _write(fake / "arbitrary.json", _fixture())
    with pytest.raises(ListeningDifficultyError, match="M13 transcription verification failed"):
        run(transcription_run_directory=fake, output_root=tmp_path / "runs")


def test_verify_rejects_receipt_tamper_and_run_refuses_overwrite(tmp_path: Path) -> None:
    m13 = _m13_run(tmp_path)
    output_root = tmp_path / "runs"
    directory = run(transcription_run_directory=m13, output_root=output_root)
    with pytest.raises(FileExistsError, match="overwrite"):
        run(transcription_run_directory=m13, output_root=output_root)
    receipt_path = directory / "verification.json"
    receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
    receipt["limitations"][0] = "tampered"
    receipt_path.write_text(json.dumps(receipt), encoding="utf-8")
    with pytest.raises(ListeningDifficultyError, match="inventoried file drift"):
        verify(run_directory=directory)


def test_cli_runs_verifies_and_rejects_urls(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    m13 = _m13_run(tmp_path)
    output_root = tmp_path / "runs"
    assert main(["run", "--transcription-run-directory", str(m13), "--output-root", str(output_root)]) == 0
    run_directory = Path(json.loads(capsys.readouterr().out)["run_directory"])
    assert main(["verify", "--run-directory", str(run_directory)]) == 0
    assert json.loads(capsys.readouterr().out)["result"] == "PASS"
    with pytest.raises(SystemExit):
        main(["run", "--transcription-run-directory", "https://example.test/run", "--output-root", str(output_root)])
