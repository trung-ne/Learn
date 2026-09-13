import json
from pathlib import Path

import pytest

from english_master.b1_pilot.service import sample_pilot, verify_pilot

ROOT = Path(__file__).parents[1]
POPULATION = ROOT / "curriculum/a1-full/v1/m15-population.json"
BLUEPRINT = ROOT / "curriculum/b1-blueprint/m16-b1-blueprint.json"
RUN = ROOT / "curriculum/b1-pilot/v1/runs/b1pilot_310bd605f76f7e2b028e4f0c0ec61181fd66cae13c9c350d331bdf1ca995d421"
AUDIT = ROOT / "curriculum/b1-pilot/v1/reports/audit.json"


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
    packet = copied / "packets/b1pilot-packet-01.json"
    value = json.loads(packet.read_text(encoding="utf8"))
    value["outline_targets"] = list(reversed(value["outline_targets"]))
    value["packet_sha256"] = "0" * 64
    packet.write_text(json.dumps(value), encoding="utf8")
    manifest = json.loads((copied / "manifest.json").read_text(encoding="utf8"))
    manifest["inventory"][0]["sha256"] = "0" * 64
    (copied / "manifest.json").write_text(json.dumps(manifest), encoding="utf8")
    with pytest.raises(ValueError):
        verify_pilot(copied, POPULATION, BLUEPRINT)
