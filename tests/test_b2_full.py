from __future__ import annotations

from pathlib import Path

from english_master.b2_full.service import (
    audit_full_b2,
    build_full_b2,
    sample_full_b2,
    verify_full_b2,
)

ROOT = Path(__file__).parents[1]
COMMITTED = ROOT / "curriculum" / "b2-full" / "v1"
SOURCES = {
    "population_path": ROOT / "curriculum" / "a1-full" / "v1" / "m15-population.json",
    "blueprint_path": ROOT / "curriculum" / "b2-blueprint" / "m16-b2-blueprint.json",
    "allocation_path": COMMITTED / "allocation.json",
    "content_manifest_path": COMMITTED / "content-manifest.json",
}


def test_build_verify_audit_sample_complete(tmp_path: Path) -> None:
    run = build_full_b2(
        **SOURCES,
        output_root=tmp_path / "runs",
        built_at="2026-09-13T12:00:00Z",
    )
    manifest, packets = verify_full_b2(run, **SOURCES)
    audit_path = tmp_path / "audit.json"
    report = audit_full_b2(run_dir=run, output_path=audit_path, **SOURCES)
    sample = sample_full_b2(
        run_dir=run,
        audit_report_path=audit_path,
        seed="test",
        output_path=tmp_path / "sample.json",
        **SOURCES,
    )

    assert len(manifest["inventory"]) == len(packets) == 50
    assert report["result"] == "PASS"
    assert len(sample["selected_lesson_ids"]) == 12
    selected = {packet["lesson_id"] for packet in packets if packet["lesson_id"] in sample["selected_lesson_ids"]}
    assert selected == set(sample["selected_lesson_ids"])
    assert {packet["unit_id"] for packet in packets if packet["lesson_id"] in selected} == {
        f"m16b2-v1-b2-u{number:02d}" for number in range(1, 11)
    }
    assert {packet["tier"] for packet in packets} == {"B2.1", "B2.2"}
    assert all(packet["content_status"] == "UNREVIEWED" for packet in packets)
