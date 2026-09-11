"""Small deterministic metric surface for an M14 local transcript pilot.

This module intentionally computes descriptive transcript metrics only.  It does
not assign CEFR levels, produce a difficulty/composite score, or invoke models.
"""

from __future__ import annotations

import argparse
import json
import re
from copy import deepcopy
from pathlib import Path
from typing import Any, Mapping, Sequence

from english_master.schema_validation import (
    SchemaValidationError,
    load_document,
    validate_instance,
)

JsonObject = dict[str, Any]
_TOKEN_RE = re.compile(r"[A-Za-z]+(?:['’-][A-Za-z]+)*")
_SENTENCE_END_RE = re.compile(r"[.!?]+")
_SPEAKER_RE = re.compile(r"SPEAKER_[0-9]{2}")
_SUBORDINATORS = frozenset(
    {
        "after",
        "although",
        "as",
        "because",
        "before",
        "if",
        "once",
        "since",
        "though",
        "unless",
        "until",
        "when",
        "whenever",
        "whereas",
        "while",
    }
)


class LocalMetricsError(ValueError):
    """Raised for malformed transcripts or non-reproducible metrics."""


def _rounded(value: float) -> float:
    return round(value, 6)


def _tokens(text: str) -> list[str]:
    return [match.group(0).casefold() for match in _TOKEN_RE.finditer(text)]


def _segments(transcript: Mapping[str, Any]) -> Sequence[Mapping[str, Any]]:
    language = transcript.get("language")
    segments = transcript.get("segments")
    if not isinstance(language, str) or not language.casefold().startswith("en"):
        raise LocalMetricsError("local-pilot metrics require an English transcript")
    if not isinstance(segments, list) or not segments:
        raise LocalMetricsError("transcript.segments must be a non-empty array")

    previous_start = -1
    for index, segment in enumerate(segments):
        if not isinstance(segment, Mapping):
            raise LocalMetricsError(f"segment {index} must be an object")
        text = segment.get("text")
        start = segment.get("start_ms")
        end = segment.get("end_ms")
        speaker = segment.get("speaker_label")
        if not isinstance(text, str) or not text.strip():
            raise LocalMetricsError(f"segment {index} must contain non-empty text")
        if isinstance(start, bool) or not isinstance(start, int) or start < 0:
            raise LocalMetricsError(f"segment {index} has invalid start_ms")
        if isinstance(end, bool) or not isinstance(end, int) or end <= start:
            raise LocalMetricsError(f"segment {index} has invalid end_ms")
        if start < previous_start:
            raise LocalMetricsError("segments must be ordered by start_ms")
        if not isinstance(speaker, str) or _SPEAKER_RE.fullmatch(speaker) is None:
            raise LocalMetricsError(
                f"segment {index} requires an anonymous SPEAKER_NN label"
            )
        previous_start = start
    return segments


def compute_metrics(transcript: Mapping[str, Any]) -> JsonObject:
    """Compute the deliberately narrow local-pilot metrics from a transcript.

    ``transcript`` may be a full M13 transcript artifact or a clearly shaped
    local fixture with ``language`` and ``segments``. Extra artifact fields are
    ignored; each segment must provide text, timestamps, and ``SPEAKER_NN``.
    """
    segments = _segments(transcript)
    token_groups = [_tokens(str(segment["text"])) for segment in segments]
    if any(not group for group in token_groups):
        raise LocalMetricsError("every segment must contain at least one English word token")
    tokens = [token for group in token_groups for token in group]
    word_count = len(tokens)
    timed_span_ms = int(segments[-1]["end_ms"]) - int(segments[0]["start_ms"])
    if timed_span_ms <= 0:
        raise LocalMetricsError("the complete transcript timed span must be positive")

    text = " ".join(str(segment["text"]) for segment in segments)
    sentence_count = len(_SENTENCE_END_RE.findall(text))
    if sentence_count == 0:
        # Segment boundaries are an explicit deterministic fallback, not a parse.
        sentence_count = len(segments)
    unique_word_count = len(set(tokens))
    long_word_count = sum(len(token) >= 7 for token in tokens)
    subordinator_count = sum(token in _SUBORDINATORS for token in tokens)
    segment_lengths = [len(group) for group in token_groups]
    timed_span_seconds = timed_span_ms / 1000

    metrics: JsonObject = {
        "speech_rate": {
            "word_count": word_count,
            "timed_span_seconds": _rounded(timed_span_seconds),
            "words_per_minute": _rounded(word_count * 60 / timed_span_seconds),
        },
        "vocabulary_proxies": {
            "unique_word_count": unique_word_count,
            "type_token_ratio": _rounded(unique_word_count / word_count),
            "mean_word_length": _rounded(sum(map(len, tokens)) / word_count),
            "long_word_ratio": _rounded(long_word_count / word_count),
        },
        "grammar_proxies": {
            "sentence_count": sentence_count,
            "mean_words_per_sentence": _rounded(word_count / sentence_count),
            "subordinator_count": subordinator_count,
            "subordinator_ratio": _rounded(subordinator_count / word_count),
        },
        "length_measures": {
            "segment_count": len(segments),
            "total_word_count": word_count,
            "mean_words_per_segment": _rounded(word_count / len(segments)),
            "max_words_per_segment": max(segment_lengths),
        },
        "anonymous_speaker_count": len(
            {str(segment["speaker_label"]) for segment in segments}
        ),
    }
    validate_metrics(metrics)
    return metrics


def validate_metrics(metrics: Mapping[str, Any]) -> None:
    """Validate the shape and bounds of a local-pilot metrics object."""
    try:
        validate_instance(dict(metrics), "m14-local-pilot-metrics")
    except SchemaValidationError as error:
        raise LocalMetricsError(f"invalid local-pilot metrics: {error}") from error


def recompute_and_validate(
    transcript: Mapping[str, Any], metrics: Mapping[str, Any]
) -> JsonObject:
    """Recompute metrics and fail if the supplied object differs exactly."""
    validate_metrics(metrics)
    recomputed = compute_metrics(transcript)
    if dict(metrics) != recomputed:
        raise LocalMetricsError("stored metrics differ from deterministic recomputation")
    return deepcopy(recomputed)


def _load_object(path: Path) -> JsonObject:
    try:
        value = load_document(path)
    except (OSError, UnicodeError, json.JSONDecodeError, ValueError) as error:
        raise LocalMetricsError(f"cannot load JSON object from {path}: {error}") from error
    if not isinstance(value, dict):
        raise LocalMetricsError(f"{path} must contain a JSON object")
    return value


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)
    compute = subparsers.add_parser("compute", help="compute metrics as JSON")
    compute.add_argument("transcript", type=Path)
    verify = subparsers.add_parser("verify", help="recompute and verify stored metrics")
    verify.add_argument("transcript", type=Path)
    verify.add_argument("metrics", type=Path)
    args = parser.parse_args(argv)
    try:
        transcript = _load_object(args.transcript)
        result = (
            compute_metrics(transcript)
            if args.command == "compute"
            else recompute_and_validate(transcript, _load_object(args.metrics))
        )
    except LocalMetricsError as error:
        parser.exit(1, f"error: {error}\n")
    print(json.dumps(result, ensure_ascii=False, sort_keys=True, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
