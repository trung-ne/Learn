import json
from pathlib import Path

import pytest

from english_master.a2_pilot.service import sample_pilot, verify_pilot

ROOT = Path(__file__).parents[1]
POPULATION = ROOT / "curriculum/a1-full/v1/m15-population.json"
BLUEPRINT = ROOT / "curriculum/a2-blueprint/m16-a2-blueprint.json"
RUN = ROOT / "curriculum/a2-pilot/v1/runs/a2pilot_0aa86043e2f0b9f21f1a4f74dc71a6777b930e74a51cc6560421498afc2226a9"
AUDIT = ROOT / "curriculum/a2-pilot/v1/reports/audit-v2.json"


def test_repaired_run_verifies_and_has_ten_packets():
    manifest = verify_pilot(RUN, POPULATION, BLUEPRINT)
    assert len(manifest["lesson_ids"]) == 10


def test_sample_is_deterministic_and_stratified(tmp_path):
    first = sample_pilot(pilot_dir=RUN, population_path=POPULATION, blueprint_path=BLUEPRINT,
                         audit_report_path=AUDIT, seed="test", sample_size=5,
                         output_path=tmp_path / "one.json")
    second_path = tmp_path / "two.json"
    second = sample_pilot(pilot_dir=RUN, population_path=POPULATION, blueprint_path=BLUEPRINT,
                          audit_report_path=AUDIT, seed="test", sample_size=5,
                          output_path=second_path)
    assert first["sample_sha256"] == second["sample_sha256"]
    assert {item.split("-u")[1][:2] for item in first["selected_lesson_ids"]} == {"01", "02"}


def test_verify_rejects_packet_target_drift(tmp_path):
    copied = tmp_path / "run"
    import shutil
    shutil.copytree(RUN, copied)
    packet = copied / "packets/a2pilot-packet-01.json"
    value = json.loads(packet.read_text(encoding="utf8"))
    value["outline_targets"] = list(reversed(value["outline_targets"]))
    value["packet_sha256"] = "0" * 64
    packet.write_text(json.dumps(value), encoding="utf8")
    manifest = json.loads((copied / "manifest.json").read_text(encoding="utf8"))
    manifest["inventory"][0]["sha256"] = "0" * 64
    (copied / "manifest.json").write_text(json.dumps(manifest), encoding="utf8")
    with pytest.raises(ValueError):
        verify_pilot(copied, POPULATION, BLUEPRINT)
