"""Deterministic, fixture-only M14 listening-difficulty analysis."""

from __future__ import annotations

import hashlib
import json
import re
import shutil
import tempfile
from copy import deepcopy
from pathlib import Path
from typing import Any, Mapping, Sequence

from english_master.lesson_generation.canonical import identity, sha256_json
from english_master.lesson_generation.storage import _fsync_directory, _rename_directory_noreplace
from english_master.schema_validation import SchemaValidationError, load_document, validate_instance
from english_master.transcription.service import verify as verify_transcription

JsonObject = dict[str, Any]
ALGORITHM_VERSION = "listening_difficulty_fixture_v2"
FEATURE_ORDER = (
    "lexical", "grammar", "speech_rate", "utterance_length", "reductions",
    "connected_speech", "accent", "speaker_count", "speaker_overlap", "noise",
    "discourse_complexity",
)
CORE_FEATURES = ("lexical", "grammar", "speech_rate", "utterance_length", "discourse_complexity")
NONLEXICAL_FEATURES = ("reductions", "connected_speech", "accent", "speaker_count", "speaker_overlap", "noise")
ACOUSTIC_FEATURES = ("reductions", "connected_speech", "accent", "noise")
LIMITATIONS = [
    "Scores are deterministic development proxies over a verified M13 fixture, not learner-performance claims.",
    "Acoustic properties are accepted only from a hash-bound synthetic fixture sidecar and are never inferred from text.",
    "No provider, model, media file, or network resource is accessed by M14.",
]
_TOKEN_RE = re.compile(r"[A-Za-z]+(?:['’-][A-Za-z]+)*")
_SENTENCE_END_RE = re.compile(r"[.!?]")
_SUBORDINATORS = frozenset({"although", "because", "before", "if", "once", "since", "though", "unless", "until", "when", "whenever", "whereas", "while"})
_DISCOURSE_MARKERS = frozenset({"also", "although", "because", "but", "finally", "first", "however", "instead", "meanwhile", "next", "otherwise", "so", "then", "therefore"})


class ListeningDifficultyError(ValueError):
    """Raised when M14 input or immutable evidence fails closed."""


def _json_bytes(value: Mapping[str, Any]) -> bytes:
    return (json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2, allow_nan=False) + "\n").encode("utf-8")


def _sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _is_link(path: Path) -> bool:
    return path.is_symlink() or (hasattr(path, "is_junction") and path.is_junction())


def _regular_local_file(path: Path) -> None:
    if "://" in str(path):
        raise ListeningDifficultyError("network URLs are prohibited; provide a local fixture")
    if _is_link(path) or not path.is_file():
        raise ListeningDifficultyError(f"input must be a regular local file: {path}")
    if any(_is_link(parent) for parent in path.absolute().parents if parent.exists()):
        raise ListeningDifficultyError("input path has a link-like ancestor")


def _load(path: Path, schema_name: str) -> JsonObject:
    _regular_local_file(path)
    try:
        value = load_document(path)
        validate_instance(value, schema_name)
    except (OSError, UnicodeError, json.JSONDecodeError, SchemaValidationError, ValueError) as error:
        raise ListeningDifficultyError(f"invalid {schema_name}: {error}") from error
    return value


def _load_m13_versioned(path: Path, schema_name: str) -> JsonObject:
    """Load supported M13 evidence without weakening its versioned schema."""
    _regular_local_file(path)
    try:
        value = load_document(path)
        version = value.get("schema_version") if isinstance(value, dict) else None
        selected = f"{schema_name}-v2" if version == "2.0" else schema_name
        validate_instance(value, selected)
    except (OSError, UnicodeError, json.JSONDecodeError, SchemaValidationError, ValueError) as error:
        raise ListeningDifficultyError(f"invalid versioned {schema_name}: {error}") from error
    return value


def _identity_projection(value: Mapping[str, Any], *fields: str) -> JsonObject:
    projected = deepcopy(dict(value))
    for field in fields:
        projected.pop(field, None)
    return projected


def bind_fixture(value: Mapping[str, Any]) -> JsonObject:
    """Bind an internal fixture. This does not authorize publication."""
    fixture = deepcopy(dict(value))
    fixture["payload_sha256"] = sha256_json(_identity_projection(fixture, "transcription_id", "payload_sha256"))
    fixture["transcription_id"] = identity("ldtx", fixture, "transcription_id")
    validate_instance(fixture, "listening-transcription-fixture")
    _verify_fixture(fixture)
    return fixture


def _verify_fixture(fixture: Mapping[str, Any]) -> None:
    if fixture.get("payload_sha256") != sha256_json(_identity_projection(fixture, "transcription_id", "payload_sha256")):
        raise ListeningDifficultyError("transcription payload hash does not reconstruct canonically")
    if fixture.get("transcription_id") != identity("ldtx", fixture, "transcription_id"):
        raise ListeningDifficultyError("transcription_id does not reconstruct canonically")
    previous_start = -1
    for index, utterance in enumerate(fixture["transcript"]["utterances"]):
        if not utterance["text"].strip():
            raise ListeningDifficultyError(f"utterance {index} has no non-whitespace transcript text")
        if "start_ms" in utterance:
            if utterance["end_ms"] <= utterance["start_ms"]:
                raise ListeningDifficultyError(f"utterance {index} has a non-positive time interval")
            if utterance["start_ms"] < previous_start:
                raise ListeningDifficultyError("timed utterances must be ordered by start_ms")
            previous_start = utterance["start_ms"]


def bind_acoustic_sidecar(value: Mapping[str, Any], fixture: Mapping[str, Any]) -> JsonObject:
    """Bind synthetic acoustic annotations to one exact M13 fixture projection."""
    sidecar = deepcopy(dict(value))
    lineage = fixture["verification"]
    sidecar.update({
        "transcription_id": fixture["transcription_id"],
        "transcription_sha256": sha256_json(fixture),
        "transcription_run_id": lineage["transcription_run_id"],
        "transcription_manifest_sha256": lineage["transcription_manifest_sha256"],
        "transcription_verification_id": lineage["transcription_verification_id"],
        "transcription_verification_sha256": lineage["transcription_verification_sha256"],
        "transcript_artifact_id": lineage["transcript_artifact_id"],
        "transcript_artifact_sha256": lineage["transcript_artifact_sha256"],
        "media_run_id": lineage["media_run_id"],
        "media_asset_id": lineage["media_asset_id"],
        "media_payload_sha256": lineage["media_payload_sha256"],
    })
    sidecar["payload_sha256"] = sha256_json(_identity_projection(sidecar, "sidecar_id", "payload_sha256"))
    sidecar["sidecar_id"] = identity("ldacoustic", sidecar, "sidecar_id")
    validate_instance(sidecar, "listening-acoustic-fixture-sidecar")
    _verify_sidecar(sidecar, fixture)
    return sidecar


def _verify_sidecar(sidecar: Mapping[str, Any], fixture: Mapping[str, Any]) -> None:
    if sidecar.get("payload_sha256") != sha256_json(_identity_projection(sidecar, "sidecar_id", "payload_sha256")):
        raise ListeningDifficultyError("acoustic sidecar payload hash does not reconstruct canonically")
    if sidecar.get("sidecar_id") != identity("ldacoustic", sidecar, "sidecar_id"):
        raise ListeningDifficultyError("acoustic sidecar id does not reconstruct canonically")
    lineage = fixture["verification"]
    expected = {
        "transcription_id": fixture["transcription_id"], "transcription_sha256": sha256_json(fixture),
        "transcription_run_id": lineage["transcription_run_id"],
        "transcription_manifest_sha256": lineage["transcription_manifest_sha256"],
        "transcription_verification_id": lineage["transcription_verification_id"],
        "transcription_verification_sha256": lineage["transcription_verification_sha256"],
        "transcript_artifact_id": lineage["transcript_artifact_id"],
        "transcript_artifact_sha256": lineage["transcript_artifact_sha256"],
        "media_run_id": lineage["media_run_id"], "media_asset_id": lineage["media_asset_id"],
        "media_payload_sha256": lineage["media_payload_sha256"],
    }
    if any(sidecar.get(key) != value for key, value in expected.items()):
        raise ListeningDifficultyError("acoustic sidecar lineage does not match the exact M13 fixture")
    names = [item["feature"] for item in sidecar["feature_annotations"]]
    if len(names) != len(set(names)):
        raise ListeningDifficultyError("acoustic sidecar feature annotations must be unique")


def _tokens(text: str) -> list[str]:
    return [match.group(0).casefold() for match in _TOKEN_RE.finditer(text)]


def _clamp_score(value: float) -> float:
    return round(min(100.0, max(0.0, value)), 2)


def _evidence(kind: str, fixture: Mapping[str, Any], locator: str, detail: str, *, sidecar: Mapping[str, Any] | None = None) -> JsonObject:
    source = sidecar or fixture
    return {
        "evidence_type": kind,
        "source_record_id": str(source.get("sidecar_id") or fixture["transcription_id"]),
        "source_sha256": sha256_json(source),
        "locator": locator,
        "detail": detail,
    }


def _assessed(feature: str, score: float, evidence: Sequence[JsonObject], method: str, confidence: str, limitations: Sequence[str]) -> JsonObject:
    return {
        "feature": feature, "status": "ASSESSED", "score": _clamp_score(score),
        "confidence": confidence, "evidence": list(evidence), "method": method,
        "method_version": ALGORITHM_VERSION,
        "contribution": {"included_in_composite": False, "weight": 0.0, "weighted_score": None, "rationale": "Composite eligibility has not yet been established."},
        "limitations": list(limitations),
    }


def _not_assessed(feature: str, fixture: Mapping[str, Any], reason: str, limitation: str) -> JsonObject:
    return {
        "feature": feature, "status": "NOT_ASSESSED", "score": None, "confidence": "NOT_ASSESSED",
        "evidence": [_evidence("ABSENCE", fixture, f"feature:{feature}", reason)],
        "method": "NOT_AVAILABLE", "method_version": ALGORITHM_VERSION,
        "contribution": {"included_in_composite": False, "weight": 0.0, "weighted_score": None, "rationale": "No score is available for composite contribution."},
        "limitations": [limitation],
    }


def _text_features(fixture: Mapping[str, Any]) -> dict[str, JsonObject]:
    utterances = fixture["transcript"]["utterances"]
    token_lists = [_tokens(str(item["text"])) for item in utterances]
    tokens = [token for group in token_lists for token in group]
    text = " ".join(str(item["text"]) for item in utterances)
    entries: dict[str, JsonObject] = {}
    if tokens:
        mean_chars = sum(map(len, tokens)) / len(tokens)
        long_ratio = sum(len(token) >= 7 for token in tokens) / len(tokens)
        type_ratio = len(set(tokens)) / len(tokens)
        entries["lexical"] = _assessed("lexical", 8 * (mean_chars - 3) + 25 * long_ratio + 15 * type_ratio, [
            _evidence("TRANSCRIPT_TEXT", fixture, "transcript.utterances[*].text", f"token_count={len(tokens)}"),
            _evidence("DERIVED_STATISTIC", fixture, "lexical-proxy", f"mean_token_characters={mean_chars:.3f};long_token_ratio={long_ratio:.3f};type_token_ratio={type_ratio:.3f}"),
        ], "ASCII-token lexical surface proxy", "MEDIUM", ["Surface statistics do not establish word sense, frequency band, or learner familiarity."])
    else:
        entries["lexical"] = _not_assessed("lexical", fixture, "No English word tokens were found.", "Non-word content cannot support lexical scoring.")
    if len(tokens) >= 4 and _SENTENCE_END_RE.search(text):
        subordinate_count = sum(token in _SUBORDINATORS for token in tokens)
        sentence_count = max(1, len(_SENTENCE_END_RE.findall(text)))
        entries["grammar"] = _assessed("grammar", 10 + 25 * subordinate_count / sentence_count + 2 * len(tokens) / sentence_count, [
            _evidence("TRANSCRIPT_TEXT", fixture, "transcript.utterances[*].text", f"sentence_boundary_count={sentence_count}"),
            _evidence("DERIVED_STATISTIC", fixture, "grammar-proxy", f"subordinator_count={subordinate_count};tokens_per_sentence={len(tokens)/sentence_count:.3f}"),
        ], "Sentence-boundary and fixed-subordinator proxy", "LOW", ["This is not a parser and cannot establish correctness or CEFR alignment."])
    else:
        entries["grammar"] = _not_assessed("grammar", fixture, "Four tokens and an explicit sentence boundary are required.", "A list or fragment is insufficient grammar evidence.")
    nonempty = [len(group) for group in token_lists if group]
    if len(nonempty) == len(utterances):
        average = sum(nonempty) / len(nonempty)
        entries["utterance_length"] = _assessed("utterance_length", average * 4, [
            _evidence("TRANSCRIPT_TEXT", fixture, "transcript.utterances[*]", f"utterance_count={len(utterances)}"),
            _evidence("DERIVED_STATISTIC", fixture, "utterance-length-proxy", f"mean_words_per_utterance={average:.3f}"),
        ], "Mean word-token count per utterance", "MEDIUM", ["Transcript segmentation quality directly affects this measure."])
    else:
        entries["utterance_length"] = _not_assessed("utterance_length", fixture, "An utterance has no English tokens.", "Every utterance must be tokenizable.")
    if len(utterances) >= 2 and tokens:
        markers = sum(token in _DISCOURSE_MARKERS for token in tokens)
        sentences = max(1, len(_SENTENCE_END_RE.findall(text)))
        entries["discourse_complexity"] = _assessed("discourse_complexity", 8 * min(len(utterances), 8) + 10 * markers + 3 * sentences, [
            _evidence("TRANSCRIPT_TEXT", fixture, "transcript.utterances[*].text", f"utterance_count={len(utterances)}"),
            _evidence("DERIVED_STATISTIC", fixture, "discourse-proxy", f"discourse_marker_count={markers};sentence_boundary_count={sentences}"),
        ], "Utterance and fixed discourse-marker proxy", "LOW", ["Marker counts do not capture coherence, implicature, topic structure, or pragmatics."])
    else:
        entries["discourse_complexity"] = _not_assessed("discourse_complexity", fixture, "Two tokenized utterances are required.", "A list or single fragment cannot support discourse scoring.")
    return entries


def _timing_features(fixture: Mapping[str, Any]) -> dict[str, JsonObject]:
    utterances = fixture["transcript"]["utterances"]
    timed = all("start_ms" in item and "end_ms" in item for item in utterances)
    speakers = all(isinstance(item.get("speaker_id"), str) for item in utterances)
    token_count = sum(len(_tokens(str(item["text"]))) for item in utterances)
    entries: dict[str, JsonObject] = {}
    if timed and token_count:
        start = min(int(item["start_ms"]) for item in utterances)
        end = max(int(item["end_ms"]) for item in utterances)
        duration = end - start
        if duration > 0:
            wpm = token_count * 60000 / duration
            entries["speech_rate"] = _assessed("speech_rate", (wpm - 70) / 1.3, [
                _evidence("TIMESTAMP", fixture, "transcript.utterances[*].start_ms/end_ms", f"timed_span_ms={duration}"),
                _evidence("DERIVED_STATISTIC", fixture, "speech-rate-proxy", f"token_count={token_count};words_per_minute={wpm:.3f}"),
            ], "Timestamp-span words-per-minute proxy", "MEDIUM", ["This includes pauses and is not acoustic articulation rate."])
        else:
            entries["speech_rate"] = _not_assessed("speech_rate", fixture, "Timestamp span is not positive.", "Positive complete timing is required.")
    else:
        entries["speech_rate"] = _not_assessed("speech_rate", fixture, "Complete timestamps and tokenized text are required.", "Rate is not inferred from untimed text.")
    if speakers:
        unique = sorted({str(item["speaker_id"]) for item in utterances})
        entries["speaker_count"] = _assessed("speaker_count", (len(unique) - 1) * 25, [
            _evidence("SPEAKER_LABEL", fixture, "transcript.utterances[*].speaker_id", f"speaker_count={len(unique)};speaker_ids={','.join(unique)}")
        ], "Count of anonymous M13 fixture labels", "MEDIUM", ["Labels are not independently diarized and do not identify people."])
    else:
        entries["speaker_count"] = _not_assessed("speaker_count", fixture, "Complete speaker labels were not supplied.", "Speaker count is not guessed from wording.")
    unique_set = {str(item.get("speaker_id")) for item in utterances} if speakers else set()
    if timed and speakers and len(unique_set) >= 2:
        intervals = [(int(item["start_ms"]), int(item["end_ms"]), str(item["speaker_id"])) for item in utterances]
        overlap = sum(max(0, min(left[1], right[1]) - max(left[0], right[0])) for i, left in enumerate(intervals) for right in intervals[i + 1:] if left[2] != right[2])
        span = max(item[1] for item in intervals) - min(item[0] for item in intervals)
        ratio = min(1.0, overlap / span) if span else 0.0
        entries["speaker_overlap"] = _assessed("speaker_overlap", ratio * 100, [
            _evidence("TIMESTAMP", fixture, "transcript.utterances[*]", f"cross_speaker_overlap_ms={overlap};timed_span_ms={span}"),
            _evidence("DERIVED_STATISTIC", fixture, "speaker-overlap-proxy", f"overlap_ratio={ratio:.3f}"),
        ], "Pairwise overlap across anonymous speaker labels", "MEDIUM", ["Pairwise overlap can overcount simultaneous intervals."])
    else:
        entries["speaker_overlap"] = _not_assessed("speaker_overlap", fixture, "Two fully timed labeled speakers are required.", "Overlap is not inferred from punctuation or wording.")
    return entries


def _acoustic_features(fixture: Mapping[str, Any], sidecar: Mapping[str, Any] | None) -> dict[str, JsonObject]:
    annotations = {item["feature"]: item for item in sidecar["feature_annotations"]} if sidecar else {}
    entries: dict[str, JsonObject] = {}
    for feature in ACOUSTIC_FEATURES:
        item = annotations.get(feature)
        if item is None:
            entries[feature] = _not_assessed(feature, fixture, "No hash-bound synthetic acoustic fixture sidecar annotation was supplied.", f"{feature} cannot be inferred from transcript text.")
            continue
        details = [f"fixture_record_id={e['fixture_record_id']};locator={e['locator']};statement={e['statement']}" for e in item["fixture_evidence"]]
        entries[feature] = _assessed(feature, float(item["score"]), [
            _evidence("ACOUSTIC_FIXTURE_SIDECAR", fixture, f"feature_annotations[{feature}]", detail, sidecar=sidecar) for detail in details
        ], f"{item['method']['name']} ({item['method']['version']})", item["confidence"], item["limitations"])
    return entries


def _set_contributions(ledger: list[JsonObject], enough: bool, qualifying: Sequence[str]) -> None:
    weights = {feature: 0.16 for feature in CORE_FEATURES}
    if qualifying:
        weights.update({feature: 0.2 / len(qualifying) for feature in qualifying})
    for entry in ledger:
        included = enough and entry["feature"] in weights
        weight = weights.get(entry["feature"], 0.0) if included else 0.0
        entry["contribution"] = {
            "included_in_composite": included,
            "weight": weight,
            "weighted_score": float(entry["score"]) * weight if included else None,
            "rationale": "Included under the fixed 80% core / 20% qualifying nonlexical rule." if included else "Excluded because the composite is withheld or this feature is not selected by the fixed rule.",
        }


def _validate_profile_semantics(profile: Mapping[str, Any]) -> None:
    ledger = profile["feature_ledger"]
    if [entry["feature"] for entry in ledger] != list(FEATURE_ORDER):
        raise ListeningDifficultyError("feature ledger must use the exact canonical order")
    assessed = {entry["feature"] for entry in ledger if entry["status"] == "ASSESSED"}
    for entry in ledger:
        is_assessed = entry["status"] == "ASSESSED"
        if is_assessed != (entry["score"] is not None) or is_assessed != (entry["confidence"] != "NOT_ASSESSED"):
            raise ListeningDifficultyError("feature score, status, and confidence conflict")
    missing = [feature for feature in CORE_FEATURES if feature not in assessed]
    qualifying = [feature for feature in NONLEXICAL_FEATURES if feature in assessed]
    if not qualifying:
        missing.append("nonlexical_audio_or_interaction")
    composite = profile["composite"]
    if composite["missing_required_features"] != missing or composite["qualifying_nonlexical_features"] != qualifying:
        raise ListeningDifficultyError("composite evidence inventory differs from feature ledger")
    enough = not missing
    if enough != (composite["status"] == "SCORED") or enough != (composite["score"] is not None):
        raise ListeningDifficultyError("composite status conflicts with evidence")
    expected_confidence = "LOW" if enough else "NOT_ASSESSED"
    if composite["confidence"] != expected_confidence:
        raise ListeningDifficultyError("composite confidence conflicts with fixture evidence")
    included = [entry for entry in ledger if entry["contribution"]["included_in_composite"]]
    if enough:
        if abs(sum(float(entry["contribution"]["weight"]) for entry in included) - 1.0) > 1e-9:
            raise ListeningDifficultyError("composite contribution weights must sum to one")
        total = _clamp_score(sum(float(entry["contribution"]["weighted_score"]) for entry in included))
        if abs(total - float(composite["score"])) > 0.02:
            raise ListeningDifficultyError("feature contributions do not reconstruct composite score")
    elif included:
        raise ListeningDifficultyError("withheld composite cannot include feature contributions")


def analyze(
    fixture: Mapping[str, Any],
    acoustic_sidecar: Mapping[str, Any] | None = None,
    *,
    _verified_m13_publication: bool = False,
) -> JsonObject:
    """Analyze arbitrary schema-valid fixture JSON internally; never publish it directly."""
    try:
        validate_instance(dict(fixture), "listening-transcription-fixture")
        _verify_fixture(fixture)
        if acoustic_sidecar is not None:
            validate_instance(dict(acoustic_sidecar), "listening-acoustic-fixture-sidecar")
            _verify_sidecar(acoustic_sidecar, fixture)
    except (SchemaValidationError, ListeningDifficultyError) as error:
        raise ListeningDifficultyError(f"invalid M14 analysis input: {error}") from error
    entries = _text_features(fixture)
    entries.update(_timing_features(fixture))
    entries.update(_acoustic_features(fixture, acoustic_sidecar))
    ledger = [entries[name] for name in FEATURE_ORDER]
    scores = {entry["feature"]: float(entry["score"]) for entry in ledger if entry["status"] == "ASSESSED"}
    missing = [feature for feature in CORE_FEATURES if feature not in scores]
    qualifying = [feature for feature in NONLEXICAL_FEATURES if feature in scores]
    if not qualifying:
        missing.append("nonlexical_audio_or_interaction")
    enough = not missing
    _set_contributions(ledger, enough, qualifying)
    score = _clamp_score(sum(float(entry["contribution"]["weighted_score"]) for entry in ledger if entry["contribution"]["included_in_composite"])) if enough else None
    lineage = fixture["verification"]
    profile: JsonObject = {
        "schema_version": "1.0", "record_type": "listening_difficulty_profile", "profile_id": "PENDING",
        "transcription_id": fixture["transcription_id"], "transcription_sha256": sha256_json(fixture),
        "transcription_run_id": lineage["transcription_run_id"], "transcription_manifest_sha256": lineage["transcription_manifest_sha256"],
        "transcription_verification_id": lineage["transcription_verification_id"], "transcription_verification_sha256": lineage["transcription_verification_sha256"],
        "transcript_artifact_id": lineage["transcript_artifact_id"], "transcript_artifact_sha256": lineage["transcript_artifact_sha256"],
        "media_run_id": lineage["media_run_id"], "media_asset_id": lineage["media_asset_id"], "media_payload_sha256": lineage["media_payload_sha256"],
        "algorithm_version": ALGORITHM_VERSION, "feature_ledger": ledger,
        "composite": {
            "status": "SCORED" if enough else "INSUFFICIENT_EVIDENCE", "score": score,
            "confidence": "LOW" if enough else "NOT_ASSESSED", "required_core_features": list(CORE_FEATURES),
            "qualifying_nonlexical_features": qualifying, "missing_required_features": missing,
            "rationale": "Composite uses all core features with a fixed 80% weight and qualifying nonlexical evidence with 20%." if enough else "Composite withheld; missing required evidence: " + ", ".join(missing) + ".",
        },
        "content_status": "UNREVIEWED",
        "publication_status": "VERIFIED_M13_FIXTURE_RUN" if _verified_m13_publication else "INTERNAL_ANALYSIS_ONLY",
        "validation_tier": "MACHINE_VALIDATED" if _verified_m13_publication else "INTERNAL_ANALYSIS_ONLY",
        "human_reviewed": False, "release_approved": False,
        "fixture_only": True, "network_accessed": False, "media_accessed": False, "model_accessed": False, "limitations": LIMITATIONS,
    }
    if acoustic_sidecar is not None:
        profile.update({"acoustic_sidecar_id": acoustic_sidecar["sidecar_id"], "acoustic_sidecar_sha256": sha256_json(acoustic_sidecar)})
    profile["profile_id"] = identity("ldprofile", profile, "profile_id")
    validate_instance(profile, "listening-difficulty-profile")
    _validate_profile_semantics(profile)
    return profile


def _safe_output_root(path: Path) -> Path:
    if "://" in str(path):
        raise ListeningDifficultyError("network URLs are prohibited for output paths")
    root = path.absolute()
    if any(_is_link(parent) for parent in (root, *root.parents) if parent.exists()):
        raise ListeningDifficultyError("output root has a link-like ancestor")
    if root.exists() and not root.is_dir():
        raise ListeningDifficultyError("output root must be a directory")
    return root


def _inventory_entry(path: Path, role: str) -> JsonObject:
    content = path.read_bytes()
    return {"path": path.name, "role": role, "bytes": len(content), "sha256": _sha256_bytes(content)}


def _expected_run_id(fixture: Mapping[str, Any], profile: Mapping[str, Any], sidecar: Mapping[str, Any] | None) -> str:
    return "ldrun_" + sha256_json({"algorithm_version": ALGORITHM_VERSION, "transcription_sha256": sha256_json(fixture), "profile_sha256": sha256_json(profile), "acoustic_sidecar_sha256": sha256_json(sidecar) if sidecar else None})


def project_m13(transcription_run_directory: Path) -> JsonObject:
    """Verify and project one real local M13 fixture run; never infer acoustics."""
    try:
        verified = verify_transcription(run_directory=transcription_run_directory)
        root = transcription_run_directory.absolute()
        manifest = _load_m13_versioned(root / "run-manifest.json", "transcription-run-manifest")
        verification = _load_m13_versioned(root / "verification.json", "transcription-verification")
        artifact = _load_m13_versioned(root / "transcript-artifact.json", "transcript-artifact")
    except (OSError, ValueError, ListeningDifficultyError) as error:
        raise ListeningDifficultyError(f"M13 transcription verification failed: {error}") from error
    if verified.get("result") != "PASS" or manifest.get("run_id") != verified.get("run_id"):
        raise ListeningDifficultyError("M13 verification result is not a passing run")
    if verification.get("result") != "PASS" or verification.get("run_id") != manifest.get("run_id"):
        raise ListeningDifficultyError("M13 verification binding is invalid")
    artifact_hash = sha256_json(artifact)
    if manifest.get("artifact_sha256") != artifact_hash or verification.get("artifact_sha256") != artifact_hash:
        raise ListeningDifficultyError("M13 artifact hash binding is invalid")
    if artifact.get("language") != "en" or artifact.get("fixture_only") is not True:
        raise ListeningDifficultyError("only an English fixture-only M13 run is eligible")
    utterances = [{"text": segment["text"], "speaker_id": str(segment["speaker_label"]).casefold(), "start_ms": segment["start_ms"], "end_ms": segment["end_ms"]} for segment in artifact["segments"]]
    return bind_fixture({
        "schema_version": "1.0", "record_type": "listening_transcription_fixture", "transcription_id": "PENDING", "payload_sha256": "PENDING",
        "fixture_only": True, "network_accessed": False, "media_accessed": False, "model_accessed": False,
        "verification": {
            "result": "PASS", "method": "VERIFIED_M13_FIXTURE_PROJECTION", "transcription_run_id": manifest["run_id"],
            "transcription_manifest_sha256": sha256_json(manifest), "transcription_verification_id": verification["verification_id"],
            "transcription_verification_sha256": sha256_json(verification), "transcript_artifact_id": artifact["artifact_id"],
            "transcript_artifact_sha256": artifact_hash, "media_schema_version": manifest["media_schema_version"],
            "media_run_id": artifact["media_run_id"], "media_asset_id": artifact["media_asset_id"], "media_payload_sha256": artifact["media_payload_sha256"],
        },
        "transcript": {"language": "en", "utterances": utterances},
        "limitations": ["Projected from an independently verified M13 fixture run; no acoustic property is inferred.", "Fixture evidence does not establish real ASR accuracy or operational readiness."],
    })


def _build_receipt(run_id: str, fixture: Mapping[str, Any], profile: Mapping[str, Any], sidecar: Mapping[str, Any] | None, core_inventory: Sequence[Mapping[str, Any]]) -> JsonObject:
    receipt: JsonObject = {
        "schema_version": "1.0", "record_type": "listening_difficulty_verification", "verification_id": "PENDING",
        "run_id": run_id, "transcription_id": fixture["transcription_id"], "transcription_sha256": sha256_json(fixture),
        "profile_id": profile["profile_id"], "profile_sha256": sha256_json(profile), "core_inventory_sha256": sha256_json(list(core_inventory)),
        "result": "PASS", "verifier": "english_master.listening_difficulty.verify/v2", "verification_method": "DETERMINISTIC_OFFLINE_RECONSTRUCTION",
        "checks": ["M13_FIXTURE_RUN_REVERIFIED", "CLOSED_INVENTORY", "HASH_BINDINGS", "PROFILE_SCHEMA", "FEATURE_SEMANTICS", "DETERMINISTIC_RECONSTRUCTION", "FIXTURE_ONLY_BOUNDARY"],
        "content_status": "UNREVIEWED", "validation_tier": "MACHINE_VALIDATED", "human_reviewed": False, "release_approved": False,
        "fixture_only": True, "network_accessed": False, "media_accessed": False, "model_accessed": False, "limitations": LIMITATIONS,
    }
    if sidecar:
        receipt.update({"acoustic_sidecar_id": sidecar["sidecar_id"], "acoustic_sidecar_sha256": sha256_json(sidecar)})
    receipt["verification_id"] = identity("ldverify", receipt, "verification_id")
    validate_instance(receipt, "listening-difficulty-verification")
    return receipt


def run(*, transcription_run_directory: Path, output_root: Path, acoustic_sidecar_path: Path | None = None) -> Path:
    """Publish only from an independently verified M13 fixture run."""
    fixture = project_m13(transcription_run_directory)
    sidecar = _load(acoustic_sidecar_path, "listening-acoustic-fixture-sidecar") if acoustic_sidecar_path else None
    if sidecar:
        _verify_sidecar(sidecar, fixture)
    profile = analyze(fixture, sidecar, _verified_m13_publication=True)
    run_id = _expected_run_id(fixture, profile, sidecar)
    root = _safe_output_root(output_root)
    destination = root / run_id
    if destination.exists() or _is_link(destination):
        raise FileExistsError(f"refusing to overwrite immutable listening-difficulty run: {destination}")
    root.mkdir(parents=True, exist_ok=True)
    staging = Path(tempfile.mkdtemp(prefix=f".{run_id}.", dir=root))
    try:
        (staging / "input.json").write_bytes(_json_bytes(fixture))
        core_inventory = [_inventory_entry(staging / "input.json", "VERIFIED_M13_FIXTURE_INPUT")]
        if sidecar:
            (staging / "acoustic-sidecar.json").write_bytes(_json_bytes(sidecar))
            core_inventory.append(_inventory_entry(staging / "acoustic-sidecar.json", "ACOUSTIC_FIXTURE_SIDECAR"))
        (staging / "profile.json").write_bytes(_json_bytes(profile))
        core_inventory.append(_inventory_entry(staging / "profile.json", "DIFFICULTY_PROFILE"))
        receipt = _build_receipt(run_id, fixture, profile, sidecar, core_inventory)
        (staging / "verification.json").write_bytes(_json_bytes(receipt))
        inventory = [*core_inventory, _inventory_entry(staging / "verification.json", "IMMUTABLE_VERIFICATION_RECEIPT")]
        manifest: JsonObject = {
            "schema_version": "1.0", "record_type": "listening_difficulty_run_manifest", "run_id": run_id,
            "transcription_id": fixture["transcription_id"], "transcription_sha256": sha256_json(fixture),
            "profile_id": profile["profile_id"], "profile_sha256": sha256_json(profile),
            "verification_id": receipt["verification_id"], "verification_sha256": sha256_json(receipt),
            "algorithm_version": ALGORITHM_VERSION, "outcome": profile["composite"]["status"],
            "inventory": inventory, "inventory_sha256": sha256_json(inventory),
            "content_status": "UNREVIEWED", "validation_tier": "MACHINE_VALIDATED", "human_reviewed": False, "release_approved": False,
            "fixture_only": True, "network_accessed": False, "media_accessed": False, "model_accessed": False, "limitations": LIMITATIONS,
        }
        if sidecar:
            manifest.update({"acoustic_sidecar_id": sidecar["sidecar_id"], "acoustic_sidecar_sha256": sha256_json(sidecar)})
        validate_instance(manifest, "listening-difficulty-run-manifest")
        (staging / "manifest.json").write_bytes(_json_bytes(manifest))
        _fsync_directory(staging)
        _rename_directory_noreplace(staging, destination)
        try:
            _fsync_directory(root)
        except OSError:
            pass
    except BaseException:
        shutil.rmtree(staging, ignore_errors=True)
        raise
    return destination


def _verify_inventory(directory: Path, manifest: Mapping[str, Any]) -> list[JsonObject]:
    sidecar_expected = "acoustic_sidecar_id" in manifest
    expected_files = {"input.json", "profile.json", "verification.json", "manifest.json"}
    if sidecar_expected:
        expected_files.add("acoustic-sidecar.json")
    actual_files: set[str] = set()
    for path in directory.rglob("*"):
        if _is_link(path) or (path.exists() and not path.is_file() and not path.is_dir()):
            raise ListeningDifficultyError(f"unsafe path in run bundle: {path}")
        if path.is_file():
            actual_files.add(path.relative_to(directory).as_posix())
    if actual_files != expected_files:
        raise ListeningDifficultyError(f"closed inventory mismatch; missing={sorted(expected_files-actual_files)!r}, unexpected={sorted(actual_files-expected_files)!r}")
    core = [_inventory_entry(directory / "input.json", "VERIFIED_M13_FIXTURE_INPUT")]
    if sidecar_expected:
        core.append(_inventory_entry(directory / "acoustic-sidecar.json", "ACOUSTIC_FIXTURE_SIDECAR"))
    core.append(_inventory_entry(directory / "profile.json", "DIFFICULTY_PROFILE"))
    expected = [*core, _inventory_entry(directory / "verification.json", "IMMUTABLE_VERIFICATION_RECEIPT")]
    if manifest["inventory"] != expected or manifest["inventory_sha256"] != sha256_json(expected):
        raise ListeningDifficultyError("inventoried file drift")
    return core


def verify(*, run_directory: Path) -> JsonObject:
    """Read-only reconstruct a closed run and return its immutable receipt."""
    if _is_link(run_directory) or not run_directory.is_dir():
        raise ListeningDifficultyError("run directory must be a real local directory")
    if any(_is_link(parent) for parent in run_directory.absolute().parents if parent.exists()):
        raise ListeningDifficultyError("run directory has a link-like ancestor")
    manifest = _load(run_directory / "manifest.json", "listening-difficulty-run-manifest")
    core_inventory = _verify_inventory(run_directory, manifest)
    fixture = _load(run_directory / "input.json", "listening-transcription-fixture")
    _verify_fixture(fixture)
    sidecar = _load(run_directory / "acoustic-sidecar.json", "listening-acoustic-fixture-sidecar") if "acoustic_sidecar_id" in manifest else None
    if sidecar:
        _verify_sidecar(sidecar, fixture)
    profile = _load(run_directory / "profile.json", "listening-difficulty-profile")
    _validate_profile_semantics(profile)
    if profile != analyze(fixture, sidecar, _verified_m13_publication=True):
        raise ListeningDifficultyError("stored profile differs from deterministic reconstruction")
    expected_run_id = _expected_run_id(fixture, profile, sidecar)
    receipt = _load(run_directory / "verification.json", "listening-difficulty-verification")
    expected_receipt = _build_receipt(expected_run_id, fixture, profile, sidecar, core_inventory)
    if receipt != expected_receipt:
        raise ListeningDifficultyError("immutable verification receipt differs from reconstruction")
    expected = {
        "run_id": expected_run_id, "transcription_id": fixture["transcription_id"], "transcription_sha256": sha256_json(fixture),
        "profile_id": profile["profile_id"], "profile_sha256": sha256_json(profile), "verification_id": receipt["verification_id"],
        "verification_sha256": sha256_json(receipt), "outcome": profile["composite"]["status"],
    }
    if sidecar:
        expected.update({"acoustic_sidecar_id": sidecar["sidecar_id"], "acoustic_sidecar_sha256": sha256_json(sidecar)})
    if any(manifest.get(key) != value for key, value in expected.items()):
        raise ListeningDifficultyError("manifest binding drift")
    if run_directory.name != expected_run_id:
        raise ListeningDifficultyError("run directory name differs from deterministic run_id")
    return deepcopy(receipt)
