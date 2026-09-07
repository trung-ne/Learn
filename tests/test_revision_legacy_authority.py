from __future__ import annotations

from pathlib import Path

from english_master.revision_cycle.legacy_authority import LegacyAuthorityPaths, revalidate_predecessor

ROOT = Path(__file__).resolve().parents[1]


def _paths() -> LegacyAuthorityPaths:
    return LegacyAuthorityPaths(
        structure=ROOT / "curriculum" / "structure.json",
        m5_snapshot=ROOT / "data" / "reviews" / "m5" / "development-20260903-062008",
        source_registry=ROOT / "sources" / "registry.yaml",
        m6_batch=ROOT / "data" / "generated" / "m6" / "development-batches" / "20260903-v6" / "development-batch.json",
        m6_root=ROOT / "data" / "generated" / "m6" / "development-candidates" / "20260903-v6-selected",
        exercise_root=ROOT / "curriculum" / "exercises",
        m7_batch=ROOT / "curriculum" / "exercises" / "development-batches" / "20260903-v3" / "development-batch.json",
        m8_pilot=ROOT / "curriculum" / "ai-practice" / "pilot-batches" / "20260905-v13",
    )


def test_m10_revalidates_real_m6_predecessor_authority_read_only() -> None:
    assert revalidate_predecessor({"target_milestone": "M6"}, _paths()) == ()


def test_m10_revalidates_real_m7_and_m82_predecessor_authority_read_only() -> None:
    paths = _paths()
    assert revalidate_predecessor({"target_milestone": "M7"}, paths) == ()
    assert revalidate_predecessor({"target_milestone": "M8_2"}, paths) == ()


def test_m10_rejects_unknown_successor_target() -> None:
    issues = revalidate_predecessor({"target_milestone": "M99"}, _paths())
    assert issues[0].code == "REQUEST_BINDING"
