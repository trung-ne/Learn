"""Minimal offline M13 transcription tooling for an M12 local-pilot manifest.

This module performs no downloads, network requests, model loading, or process
execution. A caller supplies a local backend implementation; tests can use a
pure-Python fake.
"""

from __future__ import annotations

import hashlib
import json
import math
import re
from dataclasses import asdict, dataclass
from pathlib import Path, PurePosixPath
from typing import Any, Protocol, Sequence

from .m12_local_pilot import validate_local_pilot_manifest
from .schema_validation import load_document, validate_instance

_SPEAKER_LABEL = re.compile(r"^SPEAKER_[0-9]{2,}$")


class M13LocalPilotError(ValueError):
    """Raised when selection, backend output, or transcript lineage is invalid."""


@dataclass(frozen=True, slots=True)
class ToolProvenance:
    """Factual local tool identity supplied by the caller."""

    name: str
    version: str


@dataclass(frozen=True, slots=True)
class ModelProvenance:
    """Factual model identity; use ``UNKNOWN`` when a fact is unavailable."""

    provider: str
    name: str
    version: str


@dataclass(frozen=True, slots=True)
class TranscriptSegment:
    """One timestamped segment returned by a local backend."""

    start_seconds: float
    end_seconds: float
    text: str
    speaker_label: str | None = None


@dataclass(frozen=True, slots=True)
class BackendTranscript:
    """Backend output plus an explicit offline-execution assertion."""

    segments: Sequence[TranscriptSegment]
    network_accessed: bool = False


class LocalASRBackend(Protocol):
    """Pluggable interface for caller-controlled local ASR implementations."""

    def transcribe(
        self, *, media_path: Path, record_id: str, duration_seconds: float
    ) -> BackendTranscript:
        """Return timestamped segments without network access."""


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _identity(value: dict[str, Any]) -> str:
    payload = dict(value)
    payload.pop("artifact_id", None)
    encoded = json.dumps(
        payload, ensure_ascii=False, allow_nan=False, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")
    return f"m13local_{hashlib.sha256(encoded).hexdigest()}"


def _nonempty(value: str, field: str) -> None:
    if not isinstance(value, str) or not value.strip():
        raise M13LocalPilotError(f"{field} must be a non-empty string")


def _validate_provenance(
    tool: ToolProvenance, model: ModelProvenance
) -> None:
    _nonempty(tool.name, "tool name")
    _nonempty(tool.version, "tool version")
    _nonempty(model.provider, "model provider")
    _nonempty(model.name, "model name")
    _nonempty(model.version, "model version")


def _normalize_segments(
    segments: Sequence[TranscriptSegment], *, record_id: str, duration_seconds: float
) -> list[dict[str, Any]]:
    if not segments:
        raise M13LocalPilotError(f"{record_id}: at least one segment is required")
    normalized: list[dict[str, Any]] = []
    previous_end = 0.0
    for index, segment in enumerate(segments):
        start = segment.start_seconds
        end = segment.end_seconds
        if (
            isinstance(start, bool)
            or isinstance(end, bool)
            or not isinstance(start, (int, float))
            or not isinstance(end, (int, float))
            or not math.isfinite(start)
            or not math.isfinite(end)
        ):
            raise M13LocalPilotError(
                f"{record_id} segment {index}: timestamps must be finite numbers"
            )
        if start < previous_end:
            raise M13LocalPilotError(
                f"{record_id} segment {index}: segments overlap or are out of order"
            )
        if start < 0 or end <= start or end > duration_seconds:
            raise M13LocalPilotError(
                f"{record_id} segment {index}: timestamps are outside declared duration"
            )
        text = segment.text
        if not isinstance(text, str) or not text.strip() or text != text.strip():
            raise M13LocalPilotError(
                f"{record_id} segment {index}: text must be non-empty and trimmed"
            )
        speaker = segment.speaker_label or "SPEAKER_01"
        if not _SPEAKER_LABEL.fullmatch(speaker):
            raise M13LocalPilotError(
                f"{record_id} segment {index}: speaker label must be anonymous SPEAKER_NN"
            )
        normalized.append(
            {
                "start_seconds": start,
                "end_seconds": end,
                "text": text,
                "speaker_label": speaker,
            }
        )
        previous_end = end
    return normalized


def _load_valid_manifest(manifest_path: Path, input_root: Path) -> dict[str, Any]:
    validate_local_pilot_manifest(manifest_path=manifest_path, input_root=input_root)
    manifest = load_document(manifest_path)
    if not isinstance(manifest, dict):  # Defensive; the schema already requires this.
        raise M13LocalPilotError("M12 local-pilot manifest must be an object")
    return manifest


def transcribe_local_pilot(
    *,
    manifest_path: Path,
    input_root: Path,
    selected_record_ids: Sequence[str],
    backend: LocalASRBackend,
    tool_provenance: ToolProvenance,
    model_provenance: ModelProvenance,
) -> dict[str, Any]:
    """Validate M12 authority and build transcripts for 10-20 selected records."""

    _validate_provenance(tool_provenance, model_provenance)
    selected = list(selected_record_ids)
    if not 10 <= len(selected) <= 20:
        raise M13LocalPilotError("selected_record_ids must contain 10-20 IDs")
    if len(set(selected)) != len(selected):
        raise M13LocalPilotError("selected_record_ids must be unique")

    manifest = _load_valid_manifest(manifest_path, input_root)
    records = {record["id"]: record for record in manifest["records"]}
    missing = [record_id for record_id in selected if record_id not in records]
    if missing:
        raise M13LocalPilotError(f"selected record IDs are absent from M12 manifest: {missing}")

    transcripts: list[dict[str, Any]] = []
    root = input_root.resolve(strict=True)
    for record_id in selected:
        record = records[record_id]
        permissions = record["permissions"]
        if not permissions["transcript"] or not permissions["timestamp"]:
            raise M13LocalPilotError(
                f"{record_id}: transcript and timestamp permissions must both be true"
            )
        duration = record["duration_seconds"]
        media_path = root.joinpath(*PurePosixPath(record["path"].replace("\\", "/")).parts)
        result = backend.transcribe(
            media_path=media_path,
            record_id=record_id,
            duration_seconds=duration,
        )
        if not isinstance(result, BackendTranscript):
            raise M13LocalPilotError(
                f"{record_id}: backend must return BackendTranscript"
            )
        if result.network_accessed:
            raise M13LocalPilotError(f"{record_id}: network-backed ASR is prohibited")
        segments = _normalize_segments(
            result.segments, record_id=record_id, duration_seconds=duration
        )
        transcripts.append(
            {
                "record_id": record_id,
                "parent_media_sha256": record["sha256"],
                "declared_duration_seconds": duration,
                "text": " ".join(segment["text"] for segment in segments),
                "segments": segments,
            }
        )

    artifact: dict[str, Any] = {
        "schema_version": "1.0",
        "record_type": "m13_local_pilot_transcript_batch",
        "artifact_id": "PENDING",
        "m12_manifest_sha256": _sha256_file(manifest_path),
        "tool_provenance": asdict(tool_provenance),
        "model_provenance": asdict(model_provenance),
        "transcripts": transcripts,
        "network_accessed": False,
        "content_lifecycle_status": "UNREVIEWED",
    }
    artifact["artifact_id"] = _identity(artifact)
    validate_instance(artifact, "m13-local-pilot-transcript-batch")
    return artifact


def validate_transcript_artifact(
    *, manifest_path: Path, input_root: Path, artifact: dict[str, Any]
) -> None:
    """Validate a supplied transcript artifact and its exact M12 lineage."""

    manifest = _load_valid_manifest(manifest_path, input_root)
    validate_instance(artifact, "m13-local-pilot-transcript-batch")
    if artifact["artifact_id"] != _identity(artifact):
        raise M13LocalPilotError("artifact_id does not match canonical artifact content")
    if artifact["m12_manifest_sha256"] != _sha256_file(manifest_path):
        raise M13LocalPilotError("M12 manifest hash does not match")

    records = {record["id"]: record for record in manifest["records"]}
    seen: set[str] = set()
    for transcript in artifact["transcripts"]:
        record_id = transcript["record_id"]
        if record_id in seen:
            raise M13LocalPilotError(f"duplicate transcript record ID: {record_id}")
        seen.add(record_id)
        record = records.get(record_id)
        if record is None:
            raise M13LocalPilotError(f"transcript record absent from M12 manifest: {record_id}")
        if not record["permissions"]["transcript"] or not record["permissions"]["timestamp"]:
            raise M13LocalPilotError(f"{record_id}: required permissions are false")
        if (
            transcript["parent_media_sha256"] != record["sha256"]
            or transcript["declared_duration_seconds"] != record["duration_seconds"]
        ):
            raise M13LocalPilotError(f"{record_id}: M12 media lineage does not match")
        segments = [
            TranscriptSegment(
                start_seconds=item["start_seconds"],
                end_seconds=item["end_seconds"],
                text=item["text"],
                speaker_label=item["speaker_label"],
            )
            for item in transcript["segments"]
        ]
        normalized = _normalize_segments(
            segments,
            record_id=record_id,
            duration_seconds=record["duration_seconds"],
        )
        if transcript["text"] != " ".join(item["text"] for item in normalized):
            raise M13LocalPilotError(f"{record_id}: transcript text does not match segments")
