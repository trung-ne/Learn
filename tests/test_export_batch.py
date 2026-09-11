from __future__ import annotations

import json
from pathlib import Path

import pytest
import yaml

from english_master.export_packaging import batch as batch_module
from english_master.export_packaging.batch import (
    BatchEligibilityError,
    assess_batch_input,
    build_batch_export,
    verify_batch_export,
)
from english_master.export_packaging.canonical import canonical_json_bytes, identity, sha256_bytes, sha256_file
from english_master.export_packaging.cli import main
from english_master.schema_validation import load_schemas, validate_instance as real_validate_instance

ROOT = Path(__file__).resolve().parents[1]


def _write_json(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, sort_keys=True) + "\n", encoding="utf-8")


def _batch_input(root: Path, *, status: str = "UNREVIEWED") -> Path:
    lesson = json.loads((ROOT / "tests" / "fixtures" / "valid" / "lesson.json").read_text(encoding="utf-8"))
    lesson["generation_metadata"]["qa_status"] = status
    lesson_path = root / "content" / "lesson.json"
    _write_json(lesson_path, lesson)
    registry = yaml.safe_load((ROOT / "sources" / "registry.yaml").read_text(encoding="utf-8"))
    registry_path = root / "sources" / "registry.yaml"
    registry_path.parent.mkdir(parents=True, exist_ok=True)
    registry_path.write_text(yaml.safe_dump(registry, sort_keys=True), encoding="utf-8")
    artifacts = [{
        "content_type": "LESSON",
        "content_id": lesson["id"],
        "lesson_id": lesson["id"],
        "path": "content/lesson.json",
        "sha256": sha256_file(lesson_path),
    }]
    value = {
        "schema_version": "1.0",
        "record_type": "m11_export_batch_input",
        "batch_input_id": "PENDING",
        "package_version": "local-v1",
        "source_registry": {"path": "sources/registry.yaml", "sha256": sha256_file(registry_path)},
        "artifacts": artifacts,
        "subject_inventory_sha256": sha256_bytes(canonical_json_bytes(artifacts)),
        "required_lifecycle_status": "UNREVIEWED",
        "required_source_permission": "redistribute_text",
    }
    value["batch_input_id"] = identity("m11batchinput", value, "batch_input_id")
    path = root / "batch.json"
    _write_json(path, value)
    return path


def test_batch_schemas_load_and_validate() -> None:
    schemas = load_schemas()
    for name in ("input", "manifest", "verification"):
        assert f"https://english-master.local/schemas/m11-export-batch-{name}.schema.json" in schemas


def test_build_and_verify_batch_defaults_without_approval_evidence(tmp_path: Path) -> None:
    repository = tmp_path / "repository"
    batch_input = _batch_input(repository)
    output = build_batch_export(batch_input, repository, tmp_path / "exports", exported_at="2026-09-12T10:00:00Z")
    manifest = json.loads((output / "manifest.json").read_text(encoding="utf-8"))
    assert manifest["formats"] == ["CSV", "JSON", "STATIC_MOBILE", "STATIC_WEB"]
    assert manifest["content_lifecycle_status"] == "UNREVIEWED"
    assert "approval_tier" not in manifest
    assert not (output / "print").exists()
    assert not (output / "lms").exists()
    receipt = verify_batch_export(output, repository)
    assert receipt["result"] == "PASS"
    assert receipt["content_lifecycle_status"] == "UNREVIEWED"


def test_cli_build_batch_can_add_print_and_ims(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    repository = tmp_path / "repository"
    batch_input = _batch_input(repository)
    output_root = tmp_path / "exports"
    assert main([
        "build-batch", "--batch-input", str(batch_input), "--repository-root", str(repository),
        "--output-root", str(output_root), "--exported-at", "2026-09-12T10:00:00Z",
        "--include-print", "--include-ims",
    ]) == 0
    built = json.loads(capsys.readouterr().out)
    output = Path(built["directory"])
    assert (output / "print" / "learner.html").is_file()
    assert (output / "lms" / "english-master.imscc").is_file()
    assert main(["verify-batch", str(output), "--repository-root", str(repository)]) == 0
    verified = json.loads(capsys.readouterr().out)
    assert verified["mode"] == "LOCAL_BATCH"


def test_batch_rejects_hash_drift_and_non_unreviewed_lifecycle(tmp_path: Path) -> None:
    repository = tmp_path / "repository"
    batch_input = _batch_input(repository)
    lesson_path = repository / "content" / "lesson.json"
    lesson_path.write_text(lesson_path.read_text(encoding="utf-8") + " ", encoding="utf-8")
    with pytest.raises(BatchEligibilityError, match="SHA-256 mismatch"):
        assess_batch_input(batch_input, repository)

    other = tmp_path / "other"
    approved_input = _batch_input(other, status="APPROVED")
    with pytest.raises(BatchEligibilityError, match="consistently UNREVIEWED"):
        assess_batch_input(approved_input, other)


def test_batch_rejects_unsafe_path_and_unclosed_output_inventory(tmp_path: Path) -> None:
    repository = tmp_path / "repository"
    batch_input = _batch_input(repository)
    value = json.loads(batch_input.read_text(encoding="utf-8"))
    value["artifacts"][0]["path"] = "../lesson.json"
    value["subject_inventory_sha256"] = sha256_bytes(canonical_json_bytes(value["artifacts"]))
    value["batch_input_id"] = identity("m11batchinput", value, "batch_input_id")
    _write_json(batch_input, value)
    with pytest.raises(BatchEligibilityError, match="batch input is invalid"):
        assess_batch_input(batch_input, repository)

    valid_repository = tmp_path / "valid-repository"
    valid_input = _batch_input(valid_repository)
    output = build_batch_export(valid_input, valid_repository, tmp_path / "exports", exported_at="2026-09-12T10:00:00Z")
    (output / "unexpected.txt").write_text("not inventoried", encoding="utf-8")
    with pytest.raises(ValueError, match="inventory mismatch"):
        verify_batch_export(output, valid_repository)


def test_batch_checks_source_redistribution_permission(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    repository = tmp_path / "repository"
    batch_input = _batch_input(repository)
    lesson_path = repository / "content" / "lesson.json"
    lesson = json.loads(lesson_path.read_text(encoding="utf-8"))
    lesson["source_id"] = "src_unknown"
    _write_json(lesson_path, lesson)
    value = json.loads(batch_input.read_text(encoding="utf-8"))
    value["artifacts"][0]["sha256"] = sha256_file(lesson_path)
    value["subject_inventory_sha256"] = sha256_bytes(canonical_json_bytes(value["artifacts"]))
    value["batch_input_id"] = identity("m11batchinput", value, "batch_input_id")
    _write_json(batch_input, value)

    def validate_allow_fixture(instance: object, schema_name: str) -> None:
        if schema_name != "lesson":
            real_validate_instance(instance, schema_name)

    monkeypatch.setattr(batch_module, "validate_instance", validate_allow_fixture)
    with pytest.raises(BatchEligibilityError, match="lacks redistribution authority"):
        assess_batch_input(batch_input, repository)
