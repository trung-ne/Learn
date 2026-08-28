from __future__ import annotations

from copy import deepcopy
import subprocess
import sys
from pathlib import Path

import pytest

from english_master.schema_validation import (
    SchemaValidationError,
    load_json,
    validate_instance,
    validation_issues,
)

FIXTURES = Path(__file__).parent / "fixtures"
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
    instance["license"] = "UNKNOWN"
    del instance["license_url"]

    assert validation_issues(instance, "source") == []


def test_non_quarantined_source_requires_an_identified_license() -> None:
    instance = deepcopy(load_json(FIXTURES / "valid" / "source.json"))
    instance["status"] = "REFERENCE_ONLY"
    instance["license"] = "UNKNOWN"

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
