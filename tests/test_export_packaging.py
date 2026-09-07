from __future__ import annotations

import csv
import io
import json
import zipfile
from pathlib import Path
from xml.etree import ElementTree as ET

import pytest

from english_master.export_packaging.authority import ExportEligibilityError, assess_authorization
from english_master.export_packaging.cli import main
from english_master.export_packaging.models import ExportArtifact, ExportModel
from english_master.export_packaging.renderers import RENDERERS, common_cartridge_bytes
from english_master.export_packaging.storage import build_export
from english_master.schema_validation import load_schemas

ROOT = Path(__file__).resolve().parents[1]


def _model() -> ExportModel:
    metadata = {"generator": "M11_INTERNAL_RENDERER_FIXTURE", "generator_version": "1", "model": "NONE", "prompt_version": "NONE", "generated_at": "2026-09-07T10:00:00Z", "curriculum_version": "fixture", "qa_status": "UNREVIEWED", "qa_notes": "Renderer fixture below authority boundary; never release evidence."}
    lesson = {"schema_version": "1.0", "id": "A1-U01-L01", "unit_id": "A1.1-U01", "lesson_number": 1, "cefr_level": "A1.1", "title": "Xin chào <script>alert(1)</script>", "duration_minutes": 20, "objectives": ["Read safely"], "content_sections": [{"id": "section_01", "section_type": "reading", "title": "Tom & Lan", "body_text": "Use <b> as text, not markup.", "embedded_examples": []}], "generation_metadata": metadata}
    exercise_set = {"exercise_set_id": "m7set_fixture", "lesson_id": "A1-U01-L01", "exercises": [{"id": "ex_A1-U01-L01_001", "sequence": 1, "exercise_type": "fill_blank", "difficulty": "easy", "title": "Complete", "instructions": "Write café.", "scoring_mode": "OBJECTIVE", "payload": {"stimulus": "I ___ here.", "primary_answer": "live", "nested": {"kept": True}}, "generation_metadata": metadata}]}
    prompt = {"prompt_id": "m8prompt_fixture", "lesson_id": "A1-U01-L01", "modality": "LISTENING", "cefr_level": "A1.1", "generation_metadata": metadata}
    values = (("LESSON", "A1-U01-L01", lesson), ("EXERCISE_SET", "m7set_fixture", exercise_set), ("AI_PRACTICE_PROMPT", "m8prompt_fixture", prompt))
    artifacts = tuple(ExportArtifact(kind, content_id, "A1-U01-L01", character * 64, f"fixture/{content_id}.json", content) for (kind, content_id, content), character in zip(values, "abc", strict=True))
    return ExportModel("1.0", "fixture-v1", "2026-09-07T10:00:00Z", "SEPARATE_INSTRUCTOR_EDITION", tuple(sorted(RENDERERS)), artifacts)


def test_m11_schemas_load_and_metaschema_validate() -> None:
    schemas = load_schemas()
    assert "https://english-master.local/schemas/m11-export-authorization.schema.json" in schemas
    assert "https://english-master.local/schemas/m11-export-manifest.schema.json" in schemas
    assert "https://english-master.local/schemas/m11-export-verification.schema.json" in schemas


def test_current_repository_has_no_eligible_release_authority(tmp_path: Path) -> None:
    current_m9_selection = ROOT / "data" / "reviews" / "m9" / "prepared-20260906" / "selection.json"
    with pytest.raises(ExportEligibilityError, match="authorization is invalid"):
        assess_authorization(current_m9_selection, ROOT)
    output = tmp_path / "exports"
    with pytest.raises(ExportEligibilityError):
        build_export(current_m9_selection, ROOT, output, exported_at="2026-09-07T10:00:00Z")
    assert not output.exists()


def test_cli_inspect_authority_fails_closed(capsys: pytest.CaptureFixture[str]) -> None:
    selection = ROOT / "data" / "reviews" / "m9" / "prepared-20260906" / "selection.json"
    assert main(["inspect-authority", "--authorization", str(selection), "--repository-root", str(ROOT)]) == 2
    assert json.loads(capsys.readouterr().err)["result"] == "INELIGIBLE"


def test_all_renderers_are_deterministic_and_escape_markup(tmp_path: Path) -> None:
    model = _model()
    first, second = tmp_path / "first", tmp_path / "second"
    for name in model.formats:
        RENDERERS[name](first, model)
        RENDERERS[name](second, model)
    first_files = {path.relative_to(first).as_posix(): path.read_bytes() for path in first.rglob("*") if path.is_file()}
    second_files = {path.relative_to(second).as_posix(): path.read_bytes() for path in second.rglob("*") if path.is_file()}
    assert first_files == second_files
    assert json.loads(first_files["json/catalog.json"])["artifacts"][0]["content_id"] == "A1-U01-L01"
    artifact = json.loads(first_files["json/artifacts/lesson/A1-U01-L01.json"])
    assert artifact["content_sections"][0]["body_text"] == "Use <b> as text, not markup."
    web = first_files["web/lessons/A1-U01-L01.html"].decode()
    assert "<script>" not in web and "&lt;script&gt;" in web and "Xin chào" in web
    assert b"Answer material:" not in first_files["print/learner.html"]
    assert b"Answer material:" in first_files["print/instructor-answer-key.html"]


def test_csv_is_rfc4180_and_payload_json_is_preserved(tmp_path: Path) -> None:
    RENDERERS["CSV"](tmp_path, _model())
    raw = (tmp_path / "csv" / "exercises.csv").read_bytes()
    assert b"\r\n" in raw and b"\n" not in raw.replace(b"\r\n", b"")
    rows = list(csv.DictReader(io.StringIO(raw.decode("utf-8"), newline="")))
    assert len(rows) == 1
    assert json.loads(rows[0]["payload_json"])["nested"] == {"kept": True}


def test_common_cartridge_is_closed_ungraded_web_content() -> None:
    value = common_cartridge_bytes(_model())
    assert value == common_cartridge_bytes(_model())
    with zipfile.ZipFile(io.BytesIO(value)) as archive:
        assert archive.namelist() == ["imsmanifest.xml", "resources/A1-U01-L01.xhtml"]
        assert all(info.date_time == (1980, 1, 1, 0, 0, 0) for info in archive.infolist())
        root = ET.fromstring(archive.read("imsmanifest.xml"))
        resources = [node for node in root.iter() if node.tag.endswith("resource")]
        assert [resource.attrib["type"] for resource in resources] == ["webcontent"]
        ET.fromstring(archive.read("resources/A1-U01-L01.xhtml"))
