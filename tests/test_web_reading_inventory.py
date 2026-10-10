from __future__ import annotations

import copy
import json
from pathlib import Path

from jsonschema import Draft202012Validator

from english_master.schema_validation import load_schemas, schema_registry


ROOT = Path(__file__).resolve().parents[1]
INVENTORY_PATH = ROOT / "curriculum" / "web-reading" / "v1" / "english-reading-map.json"
SCHEMA_ID = "https://english-master.local/schemas/web-reading-inventory.schema.json"


def validator() -> Draft202012Validator:
    schemas = load_schemas()
    return Draft202012Validator(schemas[SCHEMA_ID], registry=schema_registry(schemas))


def load_inventory() -> dict[str, object]:
    return json.loads(INVENTORY_PATH.read_text(encoding="utf-8"))


def test_reading_mapping_inventory_is_schema_valid_and_closed() -> None:
    inventory = load_inventory()
    validator().validate(inventory)

    records = inventory["records"]
    assert isinstance(records, list)
    assert len(records) == 212
    assert len({record["id"] for record in records}) == 212
    assert sum(record["band"] in {"A1", "A2", "B1"} and record["source_kind"] == "exercise" for record in records) == 112
    assert sum(record["band"] in {"C1", "C2"} and record["source_kind"] == "section" for record in records) == 100
    assert {record["band"] for record in records} == {"A1", "A2", "B1", "C1", "C2"}
    assert all(record.get("content_status") is None for record in records)


def test_reading_mapping_schema_rejects_extra_fields_and_invalid_ranges() -> None:
    inventory = load_inventory()
    extra = copy.deepcopy(inventory)
    extra["records"][0]["source_path"] = "private.json"
    assert list(validator().iter_errors(extra))

    invalid_range = copy.deepcopy(inventory)
    mapped = next(record for record in invalid_range["records"] if "word_sense_occurrences" in record)
    mapped["word_sense_occurrences"][0]["start"] = -1
    assert list(validator().iter_errors(invalid_range))
