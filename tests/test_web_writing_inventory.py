from __future__ import annotations

import copy
import json
from pathlib import Path

from jsonschema import Draft202012Validator

from english_master.schema_validation import load_schemas, schema_registry


ROOT = Path(__file__).resolve().parents[1]
SNAPSHOT_PATH = ROOT / "apps" / "web" / "src" / "content" / "generated" / "writing-snapshot.json"
SCHEMA_ID = "https://english-master.local/schemas/web-writing-inventory.schema.json"


def validator() -> Draft202012Validator:
    schemas = load_schemas()
    return Draft202012Validator(schemas[SCHEMA_ID], registry=schema_registry(schemas))


def load_snapshot() -> dict[str, object]:
    return json.loads(SNAPSHOT_PATH.read_text(encoding="utf-8"))


def test_writing_snapshot_is_schema_valid_and_complete() -> None:
    snapshot = load_snapshot()
    validator().validate(snapshot)

    protocols = snapshot["protocols"]
    assert isinstance(protocols, list)
    assert len(protocols) == 300
    assert len({protocol["id"] for protocol in protocols}) == 300
    assert {protocol["language"] for protocol in protocols} == {"en"}
    assert {protocol["band"] for protocol in protocols} == {"A1", "A2", "B1", "B2", "C1", "C2"}
    assert all(sum(protocol["band"] == band for protocol in protocols) == 50 for band in {"A1", "A2", "B1", "B2", "C1", "C2"})
    assert all(protocol["feedbackBoundary"] == "FEEDBACK_ONLY_NO_REPLACEMENT" for protocol in protocols)
    assert all(protocol["contentStatus"] == "UNREVIEWED" for protocol in protocols)


def test_writing_snapshot_schema_rejects_private_or_evaluator_fields() -> None:
    snapshot = load_snapshot()
    extra = copy.deepcopy(snapshot)
    extra["protocols"][0]["packetHash"] = "a" * 64
    assert list(validator().iter_errors(extra))

    invalid_boundary = copy.deepcopy(snapshot)
    invalid_boundary["protocols"][0]["feedbackBoundary"] = "ALLOW_REPLACEMENT"
    assert list(validator().iter_errors(invalid_boundary))
