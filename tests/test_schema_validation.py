from __future__ import annotations

from copy import deepcopy
import subprocess
import sys
from pathlib import Path

import pytest

from english_master.schema_validation import (
    SchemaValidationError,
    SourcePermissionError,
    can_create_clip,
    can_download_audio,
    can_download_video,
    can_extract_audio,
    can_generate_timestamps,
    can_generate_transcript,
    can_ingest_text,
    can_redistribute_derived_media,
    can_use_for_generated_exercises,
    load_json,
    load_source_registry,
    require_source_permission,
    source_permission_allowed,
    validate_instance,
    validation_issues,
)

FIXTURES = Path(__file__).parent / "fixtures"
REGISTRY_PATH = Path(__file__).parents[1] / "sources" / "registry.yaml"
SCHEMA_NAMES = [
    "source",
    "concept",
    "vocabulary-sense",
    "lesson",
    "exercise",
    "ai-practice-prompt",
]


@pytest.mark.parametrize("schema_name", SCHEMA_NAMES)
def test_valid_fixture_passes(schema_name: str) -> None:
    validate_instance(load_json(FIXTURES / "valid" / f"{schema_name}.json"), schema_name)


@pytest.mark.parametrize("schema_name", SCHEMA_NAMES)
def test_invalid_fixture_fails(schema_name: str) -> None:
    issues = validation_issues(load_json(FIXTURES / "invalid" / f"{schema_name}.json"), schema_name)
    assert issues
    with pytest.raises(SchemaValidationError):
        validate_instance(load_json(FIXTURES / "invalid" / f"{schema_name}.json"), schema_name)


def test_invalid_source_status_is_reported() -> None:
    issues = validation_issues(load_json(FIXTURES / "invalid" / "source.json"), "source")
    assert any(issue.instance_path == "$.status" for issue in issues)


def test_underscored_lesson_id_is_rejected() -> None:
    issues = validation_issues(load_json(FIXTURES / "invalid" / "lesson.json"), "lesson")
    assert any(issue.instance_path == "$.id" for issue in issues)


def test_cli_accepts_valid_fixture() -> None:
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "english_master.schema_validation",
            "--schema",
            "lesson",
            str(FIXTURES / "valid" / "lesson.json"),
        ],
        check=False,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0
    assert "VALID" in result.stdout


def test_cli_rejects_invalid_fixture() -> None:
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "english_master.schema_validation",
            "--schema",
            "lesson",
            str(FIXTURES / "invalid" / "lesson.json"),
        ],
        check=False,
        capture_output=True,
        text=True,
    )
    assert result.returncode != 0
    assert "$.id" in result.stderr



def test_quarantined_source_may_record_an_unknown_license() -> None:
    instance = deepcopy(load_json(FIXTURES / "valid" / "source.json"))
    instance["status"] = "QUARANTINED"
    instance["license"]["name"] = "UNKNOWN"
    instance["license"]["url"] = None

    assert validation_issues(instance, "source") == []


def test_non_quarantined_source_requires_an_identified_license() -> None:
    instance = deepcopy(load_json(FIXTURES / "valid" / "source.json"))
    instance["status"] = "REFERENCE_ONLY"
    instance["license"]["name"] = "UNKNOWN"

    issues = validation_issues(instance, "source")

    assert issues
    assert any("UNKNOWN" in issue.message for issue in issues)

    instance = deepcopy(load_json(FIXTURES / "valid" / "vocabulary-sense.json"))
    instance["provenance"] = {
        "source_id": "src_example_dictionary",
        "source_name": "Example Dictionary",
        "source_url": "https://example.com/dictionary",
        "source_record_id": "entry-coffee-001",
        "retrieved_at": "2026-08-28T00:00:00Z",
        "license": "CC-BY-4.0",
        "license_url": "https://creativecommons.org/licenses/by/4.0/",
        "attribution": "Example Dictionary",
        "content_hash": "0" * 64,
        "ingestion_version": "1.0",
    }

    issues = validation_issues(instance, "vocabulary-sense")

    assert any(issue.instance_path == "$.provenance" for issue in issues)


def test_exercise_requires_a_primary_answer() -> None:
    instance = deepcopy(load_json(FIXTURES / "valid" / "exercise.json"))
    instance["answer_key"]["answers"][0]["is_primary"] = False

    issues = validation_issues(instance, "exercise")

    assert any(issue.instance_path == "$.answer_key.answers" for issue in issues)


def test_external_provenance_requires_license_url() -> None:
    instance = deepcopy(load_json(FIXTURES / "valid" / "vocabulary-sense.json"))
    instance["provenance"] = {
        "source_id": "src_example_dictionary",
        "source_name": "Example Dictionary",
        "source_url": "https://example.com/dictionary",
        "source_record_id": "entry-coffee-001",
        "retrieved_at": "2026-08-30T00:00:00Z",
        "retrieved_by": "ingestion/v1",
        "license": "CC-BY-4.0",
        "attribution": "Example Dictionary",
        "content_hash": "0" * 64,
        "ingestion_version": "1.0",
    }

    issues = validation_issues(instance, "vocabulary-sense")

    assert any(issue.instance_path == "$.provenance" and "license_url" in issue.message for issue in issues)


def test_committed_source_registry_is_valid_and_has_six_approved_sources() -> None:
    registry = load_source_registry(REGISTRY_PATH)

    approved_ids = [source["source_id"] for source in registry["sources"] if source["status"] == "APPROVED"]

    assert approved_ids == [
        "src_tatoeba_text",
        "src_tatoeba_audio_cc_by_4",
        "src_common_voice_scripted_speech",
        "src_librivox_us_recordings",
        "src_nasa_svs_plain_moon_video",
        "src_wiktionary_en_text",
    ]


def test_reference_only_source_cannot_enter_ingestion() -> None:
    registry = load_source_registry(REGISTRY_PATH)

    assert not can_ingest_text(registry, "src_cefr_companion_volume")
    with pytest.raises(SourcePermissionError, match="REFERENCE_ONLY"):
        require_source_permission(registry, "src_cefr_companion_volume", "ingest_text")


def test_quarantined_source_cannot_enter_ingestion() -> None:
    registry = load_source_registry(REGISTRY_PATH)

    assert not can_ingest_text(registry, "src_english_profile_evp")
    with pytest.raises(SourcePermissionError, match="QUARANTINED"):
        require_source_permission(registry, "src_english_profile_evp", "ingest_text")


def test_rejected_source_cannot_enter_ingestion() -> None:
    registry = load_source_registry(REGISTRY_PATH)
    rejected = deepcopy(registry)
    rejected["sources"][0]["status"] = "REJECTED"

    assert not can_ingest_text(rejected, "src_tatoeba_text")
    with pytest.raises(SourcePermissionError, match="REJECTED"):
        require_source_permission(rejected, "src_tatoeba_text", "ingest_text")


def test_approved_text_source_permission_and_audio_denial() -> None:
    registry = load_source_registry(REGISTRY_PATH)

    assert can_ingest_text(registry, "src_tatoeba_text")
    assert can_use_for_generated_exercises(registry, "src_tatoeba_text", "text")
    assert not can_download_audio(registry, "src_tatoeba_text")
    assert not can_generate_transcript(registry, "src_tatoeba_text", "audio")


def test_audio_download_and_transcript_permissions_are_specific() -> None:
    registry = load_source_registry(REGISTRY_PATH)

    assert can_download_audio(registry, "src_tatoeba_audio_cc_by_4")
    assert can_generate_transcript(registry, "src_common_voice_scripted_speech", "audio")
    assert can_generate_timestamps(registry, "src_common_voice_scripted_speech", "audio")
    assert can_create_clip(registry, "src_common_voice_scripted_speech", "audio")
    assert not can_redistribute_derived_media(registry, "src_common_voice_scripted_speech", "audio")
    assert not can_download_audio(registry, "src_wiktionary_en_text")


def test_video_download_and_audio_extraction_are_independently_checked() -> None:
    registry = load_source_registry(REGISTRY_PATH)

    assert can_download_video(registry, "src_nasa_svs_plain_moon_video")
    assert not can_extract_audio(registry, "src_nasa_svs_plain_moon_video")
    assert not can_download_video(registry, "src_common_voice_scripted_speech")
    assert not can_generate_transcript(registry, "src_nasa_svs_plain_moon_video", "video")


def test_unknown_source_and_unknown_operation_fail_closed() -> None:
    registry = load_source_registry(REGISTRY_PATH)

    assert not source_permission_allowed(registry, "src_not_registered", "ingest_text")
    with pytest.raises(ValueError, match="Unknown source operation"):
        require_source_permission(registry, "src_tatoeba_text", "invent_permission")


def test_malformed_source_and_missing_evidence_are_rejected() -> None:
    source = deepcopy(load_json(FIXTURES / "valid" / "source.json"))
    del source["evidence"]

    issues = validation_issues(source, "source")

    assert any(issue.instance_path == "$" and "evidence" in issue.message for issue in issues)


def test_registry_rejects_duplicate_source_ids() -> None:
    registry = load_source_registry(REGISTRY_PATH)
    duplicate = deepcopy(registry)
    duplicate["sources"].append(deepcopy(duplicate["sources"][0]))

    issues = validation_issues(duplicate, "source-registry")

    assert any(issue.instance_path == "$.sources[12].source_id" and "duplicate source_id" in issue.message for issue in issues)


def test_registry_cli_permits_explicitly_approved_operation() -> None:
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "english_master.schema_validation",
            "--schema",
            "source-registry",
            "--require-source-permission",
            "src_tatoeba_text",
            "ingest_text",
            str(REGISTRY_PATH),
        ],
        check=False,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0
    assert "VALID" in result.stdout


@pytest.mark.parametrize(
    ("source_id", "operation", "status"),
    [
        ("src_cefr_companion_volume", "ingest_text", "REFERENCE_ONLY"),
        ("src_english_profile_evp", "ingest_text", "QUARANTINED"),
        ("src_nasa_svs_plain_moon_video", "extract_audio", "does not permit"),
    ],
)
def test_registry_cli_blocks_unapproved_or_unauthorized_operation(
    source_id: str, operation: str, status: str
) -> None:
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "english_master.schema_validation",
            "--schema",
            "source-registry",
            "--require-source-permission",
            source_id,
            operation,
            str(REGISTRY_PATH),
        ],
        check=False,
        capture_output=True,
        text=True,
    )

    assert result.returncode != 0
    assert status in result.stderr
