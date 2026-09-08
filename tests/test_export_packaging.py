from __future__ import annotations

import csv
import io
import json
import zipfile
from pathlib import Path
from xml.etree import ElementTree as ET

import pytest
import yaml

from english_master.export_packaging.authority import ExportEligibilityError, assess_authorization
from english_master.export_packaging.canonical import canonical_json_bytes, identity, sha256_bytes, sha256_file
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


def _write_json(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, sort_keys=True) + "\n", encoding="utf-8")


def _eligible_authorization(root: Path) -> Path:
    lesson = json.loads((ROOT / "tests" / "fixtures" / "valid" / "lesson.json").read_text(encoding="utf-8"))
    lesson["generation_metadata"]["qa_status"] = "APPROVED"
    lesson_path = root / "approved" / "lesson.json"
    _write_json(lesson_path, lesson)

    subjects = []
    for index in range(18):
        token = f"{index + 1:064x}"
        subjects.append({
            "subject_id": f"m9sub_{token}",
            "machine_report_path": f"machine/{token}.json",
            "machine_report_sha256": token,
            "ai_reviews": [
                {"review_role": "LINGUISTIC_AI_REVIEWER", "path": f"reviews/{token}-linguistic.json", "sha256": f"{index + 101:064x}"},
                {"review_role": "PEDAGOGICAL_AI_REVIEWER", "path": f"reviews/{token}-pedagogical.json", "sha256": f"{index + 201:064x}"},
            ],
        })
    batch = {
        "schema_version": "1.0", "record_type": "m9_development_batch", "batch_id": "PENDING",
        "selection_id": "m9select_" + "a" * 64, "selection_sha256": "b" * 64,
        "approval_tier": "DEVELOPMENT_APPROVED", "content_lifecycle_status": "UNREVIEWED",
        "human_reviewed": False, "release_approved": False, "provider_authenticated": False,
        "created_at": "2026-09-07T09:00:00Z", "subjects": subjects,
        "aggregate_report": {"selection_scope": "REPRESENTATIVE_SAMPLE", "selected_subject_count": 18, "machine_pass_count": 18, "ai_review_count": 36, "blocking_finding_count": 0, "unreviewed_outside_sample": True},
        "limitations": ["Fixture AI development evidence; no human or release claim."],
        "inventory": [{"path": "selection.json", "sha256": "c" * 64}],
    }
    batch["batch_id"] = identity("m9devbatch", batch, "batch_id")
    batch_path = root / "evidence" / "development-batch.json"
    _write_json(batch_path, batch)

    registry_source = ROOT / "sources" / "registry.yaml"
    registry_path = root / "sources" / "registry.json"
    _write_json(registry_path, yaml.safe_load(registry_source.read_text(encoding="utf-8")))
    artifacts = [{"content_type": "LESSON", "content_id": lesson["id"], "lesson_id": lesson["id"], "path": "approved/lesson.json", "sha256": sha256_file(lesson_path)}]
    authorization = {
        "schema_version": "1.0", "record_type": "m11_export_authorization", "authorization_id": "PENDING",
        "package_version": "fixture-v1", "authorized_at": "2026-09-07T10:00:00Z",
        "m9_development_batch": {"path": "evidence/development-batch.json", "sha256": sha256_file(batch_path)},
        "source_registry": {"path": "sources/registry.json", "sha256": sha256_file(registry_path)},
        "artifacts": artifacts, "subject_inventory_sha256": sha256_bytes(canonical_json_bytes(artifacts)),
        "formats": ["JSON", "CSV", "STATIC_MOBILE", "STATIC_WEB", "PRINT_HTML", "IMS_COMMON_CARTRIDGE_1_3"],
        "answer_materials": "SEPARATE_INSTRUCTOR_EDITION", "approval_tier": "DEVELOPMENT_APPROVED", "tatoeba_pilot_included": False,
    }
    authorization["authorization_id"] = identity("m11auth", authorization, "authorization_id")
    path = root / "authorization.json"
    _write_json(path, authorization)
    return path


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
    result = json.loads(capsys.readouterr().err)
    assert result["result"] == "INELIGIBLE"
    assert "authorization is invalid" in result["error"]


def test_representative_m9_evidence_cannot_authorize_m11(tmp_path: Path) -> None:
    repository = tmp_path / "repository"
    authorization = _eligible_authorization(repository)
    with pytest.raises(ExportEligibilityError, match="authorization is invalid"):
        assess_authorization(authorization, repository)


def test_renderer_fixture_retains_unreviewed_lifecycle() -> None:
    statuses = {
        artifact.content["generation_metadata"]["qa_status"]
        for artifact in _model().artifacts
        if "generation_metadata" in artifact.content
    }
    assert statuses == {"UNREVIEWED"}


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
