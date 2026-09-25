from __future__ import annotations

import json
from pathlib import Path

import pytest
from english_master.schema_validation import SchemaValidationError

from english_master.german_a1_pilot import build_pilot, verify_pilot

ROOT = Path(__file__).parents[1]
POPULATION = ROOT / "curriculum" / "german-bootstrap" / "v1" / "population.json"
BLUEPRINT = ROOT / "course" / "de" / "a1" / "blueprint-v1.json"
CONTENT = ROOT / "course" / "de" / "a1" / "content-input-v1.json"


def _build(tmp_path: Path) -> Path:
    return build_pilot(population_path=POPULATION, blueprint_path=BLUEPRINT, content_path=CONTENT, output_root=tmp_path, built_at="2026-09-25T00:00:00Z")


def test_german_pilot_builds_and_verifies_closed_ten_packet_inventory(tmp_path: Path) -> None:
    pilot = _build(tmp_path)
    manifest = verify_pilot(pilot_dir=pilot, population_path=POPULATION, blueprint_path=BLUEPRINT)
    assert manifest["language_code"] == "de"
    assert len(manifest["lesson_ids"]) == len(manifest["inventory"]) == 10
    packets = [json.loads((pilot / entry["path"]).read_text(encoding="utf-8")) for entry in manifest["inventory"]]
    blueprint = json.loads(BLUEPRINT.read_text(encoding="utf-8"))
    outlines = [lesson for unit in blueprint["units"] for lesson in unit["lessons"]]
    assert [(packet["lesson_id"], packet["outline_targets"], packet["prerequisite_lesson_ids"]) for packet in packets] == [(outline["id"], outline["targets"], outline["prerequisites"]) for outline in outlines]
    assert all(packet["content_status"] == "UNREVIEWED" and packet["provenance"]["content_origin"] == "PROJECT_AUTHORED" for packet in packets)
    assert all(3 <= len(packet["exercises"]) <= 6 and {prompt["modality"] for prompt in packet["prompts"]} == {"listening", "speaking", "pronunciation", "writing"} for packet in packets)
    assert all(next(prompt for prompt in packet["prompts"] if prompt["modality"] == "pronunciation")["assessment"] == "NOT_ASSESSED" for packet in packets)


def test_german_pilot_rejects_missing_modality(tmp_path: Path) -> None:
    content = json.loads(CONTENT.read_text(encoding="utf-8"))
    content["lessons"][0]["prompts"].pop()
    path = tmp_path / "content.json"; path.write_text(json.dumps(content), encoding="utf-8")
    with pytest.raises(SchemaValidationError):
        build_pilot(population_path=POPULATION, blueprint_path=BLUEPRINT, content_path=path, output_root=tmp_path / "runs", built_at="2026-09-25T00:00:00Z")


def test_german_pilot_rejects_forbidden_claim(tmp_path: Path) -> None:
    content = json.loads(CONTENT.read_text(encoding="utf-8"))
    content["lessons"][0]["human_reviewed"] = False
    path = tmp_path / "content.json"; path.write_text(json.dumps(content), encoding="utf-8")
    with pytest.raises(SchemaValidationError):
        build_pilot(population_path=POPULATION, blueprint_path=BLUEPRINT, content_path=path, output_root=tmp_path / "runs", built_at="2026-09-25T00:00:00Z")


def test_german_pilot_detects_packet_tampering(tmp_path: Path) -> None:
    pilot = _build(tmp_path)
    packet = next((pilot / "packets").glob("*.json"))
    value = json.loads(packet.read_text(encoding="utf-8")); value["title"] = "Verändert"
    packet.write_text(json.dumps(value), encoding="utf-8")
    with pytest.raises(ValueError, match="inventory mismatch"):
        verify_pilot(pilot_dir=pilot, population_path=POPULATION, blueprint_path=BLUEPRINT)


def test_existing_english_pilot_artifact_remains_present() -> None:
    assert (ROOT / "curriculum" / "a1-pilot" / "m15-population.json").is_file()
