"""Shared constants and types for fixture-only transcription."""
from __future__ import annotations

from typing import Any

JsonObject = dict[str, Any]

LEGACY_STAGES: tuple[tuple[int, str, str, tuple[str, ...]], ...] = (
    (1, "AUTHORIZATION", "receipts/1-authorization.json", ("M12_BINDING", "SOURCE_REGISTRY", "TRANSCRIPT_PERMISSION", "TIMESTAMP_PERMISSION", "SCHEMA")),
    (2, "REQUEST", "receipts/2-request.json", ("REQUEST_BINDING", "FIXTURE_BOUNDARY", "SCHEMA")),
    (3, "SEGMENTS", "receipts/3-segments.json", ("SEGMENT_SEQUENCE", "TIMESTAMP_BOUNDS", "SPEAKER_ANONYMIZATION", "TEXT_CONSISTENCY")),
    (4, "ARTIFACT", "receipts/4-artifact.json", ("TEXT_CONSISTENCY", "SCHEMA")),
)

STAGES: tuple[tuple[int, str, str, tuple[str, ...]], ...] = (
    (1, "AUTHORIZATION", "receipts/1-authorization.json", ("M12_V2_BINDING", "SOURCE_REGISTRY", "RECORD_PERMISSION_EVIDENCE", "TRANSCRIPT_PERMISSION", "TIMESTAMP_PERMISSION", "SCHEMA")),
    (2, "REQUEST", "receipts/2-request.json", ("REQUEST_BINDING", "FIXTURE_BOUNDARY", "SCHEMA")),
    (3, "PROCESSING_PLAN", "receipts/3-processing-plan.json", ("NO_MEDIA_ACCESS", "NO_TRANSFORM", "TOOL_MODEL_PROVENANCE", "PARAMETER_BINDING", "SCHEMA")),
    (4, "SEGMENTS", "receipts/4-segments.json", ("SEGMENT_SEQUENCE", "TIMESTAMP_BOUNDS", "SPEAKER_ANONYMIZATION", "TEXT_CONSISTENCY")),
    (5, "ARTIFACT", "receipts/5-artifact.json", ("TEXT_CONSISTENCY", "PROCESSING_PLAN_BINDING", "SCHEMA")),
)

LEGACY_CHECKS = [
    "CANONICAL_IDENTITIES", "CLOSED_INVENTORY", "FIXTURE_BOUNDARY", "M12_BINDING",
    "PATH_SAFETY", "SCHEMA", "SEGMENT_CONSISTENCY", "SOURCE_REGISTRY",
    "TIMESTAMP_ORDER", "TRANSCRIPT_PERMISSION", "TIMESTAMP_PERMISSION",
]

CHECKS = [
    "CANONICAL_IDENTITIES",
    "CLOSED_INVENTORY",
    "FIXTURE_BOUNDARY",
    "M12_V2_BINDING",
    "NO_MEDIA_ACCESS",
    "NO_TRANSFORM",
    "PARAMETER_BINDING",
    "PATH_SAFETY",
    "PROCESSING_PLAN_BINDING",
    "RECORD_PERMISSION_EVIDENCE",
    "SCHEMA",
    "SEGMENT_CONSISTENCY",
    "SOURCE_REGISTRY",
    "TIMESTAMP_ORDER",
    "TOOL_MODEL_PROVENANCE",
    "TRANSCRIPT_PERMISSION",
    "TIMESTAMP_PERMISSION",
]

LIMITATIONS = [
    "This run copies caller-authored inline transcript fixture text; it does not read, decode, transform, extract audio from, or transcribe parent media bytes.",
    "No ASR model, model file, provider, network service, or external process was invoked.",
    "Static fixture validation is not transcript-accuracy evidence, provider behavior, redistribution authority, or public-release authority.",
]

FIXTURE_TOOL = {
    "name": "english_master.transcription.fixture_copy",
    "version": "2.0",
    "implementation": "PROJECT_PYTHON",
}
FIXTURE_MODEL = {
    "invoked": False,
    "provider": None,
    "name": None,
    "version": None,
    "model_file_sha256": None,
}
FIXTURE_PARAMETERS = {
    "segment_source": "INLINE_REQUEST",
    "text_join_separator": " ",
    "timestamp_unit": "MILLISECONDS",
    "text_normalization": "NONE_EXACT_COPY",
    "speaker_label_policy": "ANONYMIZED_SEQUENTIAL",
}


class TranscriptionError(ValueError):
    """Raised when fixture authority, transcript data, or an immutable run is invalid."""
