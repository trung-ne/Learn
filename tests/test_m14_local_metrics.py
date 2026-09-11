from __future__ import annotations

import json
from pathlib import Path

import pytest

from english_master.listening_difficulty.local_metrics import (
    LocalMetricsError,
    compute_metrics,
    main,
    recompute_and_validate,
    validate_metrics,
)


def _transcript() -> dict[str, object]:
    # Deliberately shaped like the relevant projection of an M13 artifact.
    return {
        "language": "en",
        "segments": [
            {
                "segment_id": "segment_0001",
                "sequence": 1,
                "start_ms": 0,
                "end_ms": 5000,
                "speaker_label": "SPEAKER_01",
                "text": "I cook dinner because my family is hungry.",
            },
            {
                "segment_id": "segment_0002",
                "sequence": 2,
                "start_ms": 6000,
                "end_ms": 12000,
                "speaker_label": "SPEAKER_02",
                "text": "We eat together, and we talk.",
            },
        ],
    }


def test_compute_metrics_has_only_the_narrow_local_pilot_surface() -> None:
    metrics = compute_metrics(_transcript())

    assert set(metrics) == {
        "speech_rate",
        "vocabulary_proxies",
        "grammar_proxies",
        "length_measures",
        "anonymous_speaker_count",
    }
    assert metrics == {
        "speech_rate": {
            "word_count": 14,
            "timed_span_seconds": 12.0,
            "words_per_minute": 70.0,
        },
        "vocabulary_proxies": {
            "unique_word_count": 13,
            "type_token_ratio": 0.928571,
            "mean_word_length": 4.0,
            "long_word_ratio": 0.142857,
        },
        "grammar_proxies": {
            "sentence_count": 2,
            "mean_words_per_sentence": 7.0,
            "subordinator_count": 1,
            "subordinator_ratio": 0.071429,
        },
        "length_measures": {
            "segment_count": 2,
            "total_word_count": 14,
            "mean_words_per_segment": 7.0,
            "max_words_per_segment": 8,
        },
        "anonymous_speaker_count": 2,
    }
    serialized = json.dumps(metrics).casefold()
    assert "cefr" not in serialized
    assert "composite" not in serialized
    assert "score" not in serialized


def test_recomputation_detects_metric_drift() -> None:
    metrics = compute_metrics(_transcript())
    assert recompute_and_validate(_transcript(), metrics) == metrics

    metrics["speech_rate"]["words_per_minute"] = 71.0  # type: ignore[index]
    with pytest.raises(LocalMetricsError, match="deterministic recomputation"):
        recompute_and_validate(_transcript(), metrics)


def test_schema_rejects_scope_expansion() -> None:
    metrics = compute_metrics(_transcript())
    metrics["composite"] = {"score": 42}
    with pytest.raises(LocalMetricsError, match="invalid local-pilot metrics"):
        validate_metrics(metrics)


def test_rejects_non_anonymous_speaker_label() -> None:
    transcript = _transcript()
    transcript["segments"][0]["speaker_label"] = "Alice"  # type: ignore[index]
    with pytest.raises(LocalMetricsError, match="anonymous SPEAKER_NN"):
        compute_metrics(transcript)


def test_cli_computes_and_verifies(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    transcript_path = tmp_path / "transcript.json"
    metrics_path = tmp_path / "metrics.json"
    transcript_path.write_text(json.dumps(_transcript()), encoding="utf-8")

    assert main(["compute", str(transcript_path)]) == 0
    computed = json.loads(capsys.readouterr().out)
    metrics_path.write_text(json.dumps(computed), encoding="utf-8")

    assert main(["verify", str(transcript_path), str(metrics_path)]) == 0
    assert json.loads(capsys.readouterr().out) == computed
