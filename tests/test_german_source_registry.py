from __future__ import annotations

from copy import deepcopy
import json
from pathlib import Path

import pytest

from english_master.german_source_registry import build_registry, validate_registry
from english_master.schema_validation import SchemaValidationError, validate_instance

ROOT = Path(__file__).parents[1]
REGISTRY_PATH = ROOT / "sources" / "german-registry-v1.json"


def test_german_registry_is_valid_and_language_scoped() -> None:
    value = json.loads(REGISTRY_PATH.read_text(encoding="utf-8"))
    validate_registry(value)
    validate_instance(value, "multilingual-source-registry-v1")
    assert len(value["registry"]["sources"]) == 5
    assert {code for scope in value["language_scopes"] for code in scope["language_codes"]} == {"de"}
    assert {source["status"] for source in value["registry"]["sources"]} == {"APPROVED", "REFERENCE_ONLY"}


def test_reference_only_sources_cannot_be_ingested() -> None:
    value = build_registry()
    source = next(item for item in value["registry"]["sources"] if item["status"] == "REFERENCE_ONLY")
    source["permissions"]["ingest_allowed"] = True
    with pytest.raises(ValueError, match="reference-only"):
        validate_registry(value)


def test_registry_rejects_unknown_scope_source() -> None:
    value = build_registry()
    broken = deepcopy(value)
    broken["language_scopes"][0]["source_id"] = "src_de_missing"
    with pytest.raises(SchemaValidationError):
        validate_registry(broken)


def test_registry_does_not_change_legacy_registry() -> None:
    legacy = ROOT / "sources" / "registry.yaml"
    assert legacy.exists()
    assert REGISTRY_PATH != legacy
