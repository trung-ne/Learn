from __future__ import annotations

import json
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator

from english_master.schema_validation import SCHEMA_FILENAMES, load_schemas, schema_directory, schema_registry


@pytest.fixture(scope="module")
def schemas() -> dict[str, dict[str, object]]:
    return load_schemas()


def test_all_schema_files_are_loaded_and_metaschema_valid(schemas: dict[str, dict[str, object]]) -> None:
    files = sorted(path.name for path in schema_directory().glob("*.schema.json"))
    assert files == [
        "ai-practice-prompt.schema.json",
        "common.schema.json",
        "concept.schema.json",
        "exercise.schema.json",
        "lesson.schema.json",
        "source.schema.json",
        "vocabulary-sense.schema.json",
    ]
    assert len(schemas) == len(files)
    for schema in schemas.values():
        Draft202012Validator.check_schema(schema)


def test_core_schemas_resolve_the_common_schema(schemas: dict[str, dict[str, object]]) -> None:
    registry = schema_registry(schemas)
    common_id = "https://english-master.local/schemas/common.schema.json"
    assert registry.contents(common_id) == schemas[common_id]
    for name, filename in SCHEMA_FILENAMES.items():
        schema = json.loads((schema_directory() / filename).read_text(encoding="utf-8"))
        validator = Draft202012Validator(schema, registry=registry)
        assert validator.schema["title"].startswith("English Master"), name


def test_source_status_model_is_exact() -> None:
    common = json.loads((schema_directory() / "common.schema.json").read_text(encoding="utf-8"))
    assert common["$defs"]["sourceStatus"]["enum"] == [
        "APPROVED",
        "REFERENCE_ONLY",
        "QUARANTINED",
        "REJECTED",
    ]
