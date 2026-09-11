from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

from english_master.m13_local_pilot import (
    BackendTranscript,
    M13LocalPilotError,
    ModelProvenance,
    ToolProvenance,
    TranscriptSegment,
    transcribe_local_pilot,
    validate_transcript_artifact,
)
from english_master.schema_validation import validate_instance


class FakeLocalBackend:
    def __init__(
        self,
        segments: tuple[TranscriptSegment, ...] | None = None,
        *,
        network_accessed: bool = False,
    ) -> None:
        self.segments = segments or (
            TranscriptSegment(0.0, 1.0, "Hello."),
            TranscriptSegment(1.0, 2.0, "How are you?", "SPEAKER_02"),
        )
        self.network_accessed = network_accessed
        self.calls: list[tuple[Path, str, float]] = []

    def transcribe(
        self, *, media_path: Path, record_id: str, duration_seconds: float
    ) -> BackendTranscript:
        self.calls.append((media_path, record_id, duration_seconds))
        return BackendTranscript(self.segments, self.network_accessed)


def _manifest(tmp_path: Path, *, count: int = 12) -> tuple[Path, Path, list[str]]:
    input_root = tmp_path / "media-root"
    records: list[dict[str, object]] = []
    ids: list[str] = []
    for index in range(count):
        record_id = f"pilot-media-{index:02d}"
        ids.append(record_id)
        relative = f"audio/{index:02d}.wav"
        payload = f"local-audio-{index}".encode()
        path = input_root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(payload)
        records.append(
            {
                "id": record_id,
                "path": relative,
                "sha256": hashlib.sha256(payload).hexdigest(),
                "duration_seconds": 5.0,
                "source_url": f"https://example.test/audio/{index}",
                "license": "CC0-1.0",
                "attribution": f"Test audio {index}",
                "permissions": {
                    "storage": True,
                    "transcript": True,
                    "timestamp": True,
                },
            }
        )
    manifest = {
        "schema_version": "1.0",
        "record_type": "m12_operational_local_pilot_manifest",
        "records": records,
    }
    manifest_path = tmp_path / "m12-manifest.json"
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
    return manifest_path, input_root, ids


def _run(
    tmp_path: Path,
    backend: FakeLocalBackend,
    *,
    selected_count: int = 10,
) -> tuple[dict[str, object], Path, Path, list[str]]:
    manifest_path, input_root, ids = _manifest(tmp_path)
    artifact = transcribe_local_pilot(
        manifest_path=manifest_path,
        input_root=input_root,
        selected_record_ids=ids[:selected_count],
        backend=backend,
        tool_provenance=ToolProvenance("fake-local-asr", "1.2.3"),
        model_provenance=ModelProvenance("TEST_ONLY", "fake-model", "v1"),
    )
    return artifact, manifest_path, input_root, ids


def test_builds_structured_offline_transcripts_with_fake_backend(tmp_path: Path) -> None:
    backend = FakeLocalBackend()
    artifact, manifest_path, input_root, ids = _run(tmp_path, backend)

    validate_instance(artifact, "m13-local-pilot-transcript-batch")
    validate_transcript_artifact(
        manifest_path=manifest_path, input_root=input_root, artifact=artifact
    )
    assert [item["record_id"] for item in artifact["transcripts"]] == ids[:10]  # type: ignore[index]
    assert artifact["network_accessed"] is False
    assert artifact["tool_provenance"] == {"name": "fake-local-asr", "version": "1.2.3"}
    first = artifact["transcripts"][0]  # type: ignore[index]
    assert first["text"] == "Hello. How are you?"
    assert [segment["speaker_label"] for segment in first["segments"]] == [
        "SPEAKER_01",
        "SPEAKER_02",
    ]
    assert len(backend.calls) == 10
    assert all(path.is_file() and duration == 5.0 for path, _, duration in backend.calls)


@pytest.mark.parametrize("selected_count", [9, 21])
def test_requires_ten_to_twenty_selected_ids(
    tmp_path: Path, selected_count: int
) -> None:
    manifest_path, input_root, ids = _manifest(tmp_path, count=max(21, selected_count))
    with pytest.raises(M13LocalPilotError, match="10-20"):
        transcribe_local_pilot(
            manifest_path=manifest_path,
            input_root=input_root,
            selected_record_ids=ids[:selected_count],
            backend=FakeLocalBackend(),
            tool_provenance=ToolProvenance("tool", "1"),
            model_provenance=ModelProvenance("UNKNOWN", "model", "UNKNOWN"),
        )


def test_rejects_unknown_duplicate_and_unpermitted_selection(tmp_path: Path) -> None:
    manifest_path, input_root, ids = _manifest(tmp_path)
    common = {
        "manifest_path": manifest_path,
        "input_root": input_root,
        "backend": FakeLocalBackend(),
        "tool_provenance": ToolProvenance("tool", "1"),
        "model_provenance": ModelProvenance("UNKNOWN", "model", "UNKNOWN"),
    }
    with pytest.raises(M13LocalPilotError, match="unique"):
        transcribe_local_pilot(selected_record_ids=[ids[0]] * 10, **common)
    with pytest.raises(M13LocalPilotError, match="absent"):
        transcribe_local_pilot(
            selected_record_ids=[*ids[:9], "missing-record"], **common
        )

    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["records"][0]["permissions"]["timestamp"] = False
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
    with pytest.raises(M13LocalPilotError, match="permissions"):
        transcribe_local_pilot(selected_record_ids=ids[:10], **common)


@pytest.mark.parametrize(
    "segments",
    [
        (
            TranscriptSegment(0.0, 2.0, "First"),
            TranscriptSegment(1.5, 3.0, "Overlap"),
        ),
        (TranscriptSegment(0.0, 6.0, "Past duration"),),
        (TranscriptSegment(0.0, 1.0, "Named", "ALICE"),),
        (TranscriptSegment(0.0, 1.0, " padded "),),
    ],
)
def test_rejects_invalid_timestamps_speakers_and_text(
    tmp_path: Path, segments: tuple[TranscriptSegment, ...]
) -> None:
    with pytest.raises(M13LocalPilotError):
        _run(tmp_path, FakeLocalBackend(segments))


def test_rejects_backend_that_reports_network_access(tmp_path: Path) -> None:
    with pytest.raises(M13LocalPilotError, match="network-backed"):
        _run(tmp_path, FakeLocalBackend(network_accessed=True))


def test_requires_explicit_nonempty_tool_and_model_provenance(tmp_path: Path) -> None:
    manifest_path, input_root, ids = _manifest(tmp_path)
    with pytest.raises(M13LocalPilotError, match="tool name"):
        transcribe_local_pilot(
            manifest_path=manifest_path,
            input_root=input_root,
            selected_record_ids=ids[:10],
            backend=FakeLocalBackend(),
            tool_provenance=ToolProvenance("", "1"),
            model_provenance=ModelProvenance("UNKNOWN", "model", "UNKNOWN"),
        )
