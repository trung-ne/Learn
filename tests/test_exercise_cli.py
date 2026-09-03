from __future__ import annotations

from pathlib import Path

from english_master.exercise_development_batch import main as batch_main
from english_master.exercise_generate import main

ROOT = Path(__file__).resolve().parents[1]
CAPTURE = ROOT / "tests" / "fixtures" / "exercise_generation" / "a1-u01-l01-capture.json"


def test_offline_cli_accepts_valid_capture(tmp_path: Path) -> None:
    result = main(["--lesson-id", "A1-U01-L01", "--captured-response", str(CAPTURE), "--output-dir", str(tmp_path / "accepted")])
    assert result == 0
    assert (tmp_path / "accepted" / "exercise-set.json").is_file()
    assert (tmp_path / "accepted" / "audit.json").is_file()


def test_offline_cli_accepts_revised_capture_with_new_identity(tmp_path: Path) -> None:
    default_output = tmp_path / "default"
    revised_output = tmp_path / "revised"
    assert main(["--lesson-id", "A1-U01-L01", "--captured-response", str(CAPTURE), "--output-dir", str(default_output)]) == 0
    assert main(["--revision", "2", "--lesson-id", "A1-U01-L01", "--captured-response", str(CAPTURE), "--output-dir", str(revised_output)]) == 0
    assert (default_output / "exercise-set.json").read_text(encoding="utf-8") != (revised_output / "exercise-set.json").read_text(encoding="utf-8")


def test_offline_cli_rejects_bad_capture(tmp_path: Path) -> None:
    bad = tmp_path / "bad.json"
    bad.write_text('{"content":{"items":[]},"observed_at":"2026-09-03T09:00:00Z"}', encoding="utf-8")
    result = main(["--lesson-id", "A1-U01-L01", "--captured-response", str(bad), "--output-dir", str(tmp_path / "accepted")])
    assert result in {1, 2}


def test_development_batch_cli_publishes_selected_immutable_revisions(tmp_path: Path) -> None:
    result = batch_main([
        "--exercise-root", str(ROOT / "curriculum" / "exercises"),
        "--bundle-paths", str(ROOT / "curriculum" / "exercises" / "development-20260903-v3" / "batch-selection.json"),
        "--created-at", "2026-09-03T10:15:00Z",
        "--output-dir", str(tmp_path / "development-batch"),
    ])
    assert result == 0
    assert (tmp_path / "development-batch" / "development-batch.json").is_file()
