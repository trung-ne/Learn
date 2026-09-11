"""Direct local-batch M11 export path without development-approval authority."""
from __future__ import annotations

import shutil
import tempfile
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from typing import Any, Mapping, Sequence

import yaml

from english_master.lesson_generation.storage import _fsync_directory, _rename_directory_noreplace
from english_master.schema_validation import (
    load_document,
    load_json,
    require_source_permission,
    validate_instance,
)

from .canonical import canonical_json_bytes, identity, sha256_bytes, sha256_file
from .models import ExportModel, build_export_model
from .renderers import RENDERERS, common_cartridge_bytes
from .storage import STATIC_LIMITATIONS, _write_json
from .verification import ExportVerificationError, _validate_cartridge, _validate_payload_files

DEFAULT_BATCH_FORMATS = ("CSV", "JSON", "STATIC_MOBILE", "STATIC_WEB")
OPTIONAL_BATCH_FORMATS = ("PRINT_HTML", "IMS_COMMON_CARTRIDGE_1_3")
_RENDERER_PROFILES = {
    "model": "M11_NORMALIZED_MODEL_v1",
    "json": "M11_CANONICAL_JSON_v1",
    "csv": "M11_RFC4180_CSV_v1",
    "static": "M11_STATIC_HTML_v1",
    "print": "M11_PRINT_HTML_v1",
    "common_cartridge": "M11_IMS_CC_1_3_UNGRADED_WEBCONTENT_v1",
}
_SCHEMA_BY_TYPE = {
    "LESSON": "lesson",
    "EXERCISE_SET": "exercise-set",
    "AI_PRACTICE_PROMPT": "ai-practice-prompt-artifact",
}


class BatchEligibilityError(ValueError):
    """Raised when direct local-batch input or content is unsafe."""


@dataclass(frozen=True)
class EligibleBatch:
    batch_input: dict[str, Any]
    batch_input_path: Path
    repository_root: Path
    artifacts: tuple[tuple[dict[str, Any], dict[str, Any], Path], ...]


def _source_ids(value: Any) -> set[str]:
    result: set[str] = set()
    if isinstance(value, Mapping):
        source_id = value.get("source_id")
        if isinstance(source_id, str):
            result.add(source_id)
        for item in value.values():
            result.update(_source_ids(item))
    elif isinstance(value, list):
        for item in value:
            result.update(_source_ids(item))
    return result


def _qa_statuses(value: Any) -> set[str]:
    result: set[str] = set()
    if isinstance(value, Mapping):
        lifecycle = value.get("content_lifecycle_status")
        if isinstance(lifecycle, str):
            result.add(lifecycle)
        metadata = value.get("generation_metadata")
        if isinstance(metadata, Mapping) and isinstance(metadata.get("qa_status"), str):
            result.add(str(metadata["qa_status"]))
        for item in value.values():
            result.update(_qa_statuses(item))
    elif isinstance(value, list):
        for item in value:
            result.update(_qa_statuses(item))
    return result


def _resolve(root: Path, relative: object, *, label: str) -> Path:
    if not isinstance(relative, str) or not relative:
        raise BatchEligibilityError(f"{label}: path must be a nonempty repository-relative POSIX path")
    value = PurePosixPath(relative)
    if value.is_absolute() or ".." in value.parts or "\\" in relative:
        raise BatchEligibilityError(f"{label}: unsafe path {relative!r}")
    root = root.resolve()
    unresolved = root.joinpath(*value.parts)
    current = root
    for part in value.parts:
        current = current / part
        if current.is_symlink():
            raise BatchEligibilityError(f"{label}: symbolic-link paths are not allowed")
    path = unresolved.resolve()
    try:
        path.relative_to(root)
    except ValueError as error:
        raise BatchEligibilityError(f"{label}: path escapes repository root") from error
    if not path.is_file():
        raise BatchEligibilityError(f"{label}: file does not exist: {relative}")
    return path


def _load_bound(root: Path, reference: Mapping[str, Any], *, label: str, document: bool = False) -> tuple[dict[str, Any], Path]:
    path = _resolve(root, reference.get("path"), label=label)
    if reference.get("sha256") != sha256_file(path):
        raise BatchEligibilityError(f"{label}: SHA-256 mismatch")
    try:
        return (load_document(path) if document else load_json(path)), path
    except (OSError, ValueError, yaml.YAMLError) as error:
        raise BatchEligibilityError(f"{label}: invalid structured object: {error}") from error


def assess_batch_input(batch_input_path: Path, repository_root: Path) -> EligibleBatch:
    """Validate one explicit local inventory without consulting M9/M10 authority."""

    try:
        batch_input = load_json(batch_input_path.resolve())
        validate_instance(batch_input, "m11-export-batch-input")
    except (OSError, ValueError) as error:
        raise BatchEligibilityError(f"batch input is invalid: {error}") from error
    if batch_input.get("batch_input_id") != identity("m11batchinput", batch_input, "batch_input_id"):
        raise BatchEligibilityError("batch_input_id is not canonical")
    if batch_input.get("subject_inventory_sha256") != sha256_bytes(canonical_json_bytes(batch_input.get("artifacts"))):
        raise BatchEligibilityError("subject_inventory_sha256 does not bind the exact artifact inventory")

    root = repository_root.resolve()
    registry, _ = _load_bound(root, batch_input["source_registry"], label="source_registry", document=True)
    try:
        validate_instance(registry, "source-registry")
    except ValueError as error:
        raise BatchEligibilityError(f"source_registry: {error}") from error

    artifacts: list[tuple[dict[str, Any], dict[str, Any], Path]] = []
    seen_ids: set[str] = set()
    seen_paths: set[str] = set()
    for index, raw_member in enumerate(batch_input["artifacts"]):
        member = dict(raw_member)
        label = f"artifacts[{index}]"
        record, path = _load_bound(root, member, label=label)
        try:
            validate_instance(record, _SCHEMA_BY_TYPE[member["content_type"]])
        except ValueError as error:
            raise BatchEligibilityError(f"{label}: {error}") from error
        if member["content_id"] in seen_ids or member["path"] in seen_paths:
            raise BatchEligibilityError(f"{label}: duplicate content identity or path")
        seen_ids.add(member["content_id"])
        seen_paths.add(member["path"])
        actual_id = record.get("id") or record.get("exercise_set_id") or record.get("prompt_artifact_id")
        if actual_id != member["content_id"]:
            raise BatchEligibilityError(f"{label}: content_id does not match the record")
        actual_lesson = record.get("lesson_id") or (record.get("id") if member["content_type"] == "LESSON" else None)
        if actual_lesson != member["lesson_id"]:
            raise BatchEligibilityError(f"{label}: lesson_id does not match the record")
        statuses = _qa_statuses(record)
        if statuses != {batch_input["required_lifecycle_status"]}:
            raise BatchEligibilityError(f"{label}: generated records must remain consistently UNREVIEWED, found {sorted(statuses)!r}")
        for source_id in sorted(_source_ids(record)):
            try:
                require_source_permission(registry, source_id, batch_input["required_source_permission"])
            except ValueError as error:
                raise BatchEligibilityError(f"{label}: source {source_id!r} lacks redistribution authority: {error}") from error
        artifacts.append((member, record, path))

    # The shared normalized model enforces lesson closure for every referenced member.
    config = {
        "package_version": batch_input["package_version"],
        "answer_materials": "SEPARATE_INSTRUCTOR_EDITION",
        "formats": list(DEFAULT_BATCH_FORMATS),
    }
    try:
        build_export_model(config, artifacts, exported_at="2000-01-01T00:00:00Z")
    except ValueError as error:
        raise BatchEligibilityError(str(error)) from error
    return EligibleBatch(batch_input, batch_input_path.resolve(), root, tuple(artifacts))


def _formats(*, include_print: bool, include_ims: bool) -> tuple[str, ...]:
    formats = list(DEFAULT_BATCH_FORMATS)
    if include_print:
        formats.append("PRINT_HTML")
    if include_ims:
        formats.append("IMS_COMMON_CARTRIDGE_1_3")
    return tuple(sorted(formats))


def _model(eligible: EligibleBatch, formats: Sequence[str], exported_at: str) -> ExportModel:
    config = {
        "package_version": eligible.batch_input["package_version"],
        "answer_materials": "SEPARATE_INSTRUCTOR_EDITION",
        "formats": list(formats),
    }
    return build_export_model(config, eligible.artifacts, exported_at=exported_at)


def _format_for(path: str) -> str:
    if path == "batch-input.json":
        return "CONTROL"
    prefix = path.split("/", 1)[0]
    return {"json": "JSON", "csv": "CSV", "mobile": "STATIC_MOBILE", "web": "STATIC_WEB", "print": "PRINT_HTML", "lms": "IMS_COMMON_CARTRIDGE_1_3"}[prefix]


def _inventory(staging: Path, emitted: Sequence[Path]) -> list[dict[str, Any]]:
    result = []
    for path in sorted(emitted, key=lambda item: item.relative_to(staging).as_posix()):
        relative = path.relative_to(staging).as_posix()
        result.append({"path": relative, "format": _format_for(relative), "bytes": path.stat().st_size, "sha256": sha256_file(path)})
    return result


def build_batch_export(
    batch_input_path: Path,
    repository_root: Path,
    output_root: Path,
    *,
    exported_at: str,
    include_print: bool = False,
    include_ims: bool = False,
) -> Path:
    """Atomically build a direct local batch using the shared M11 renderers."""

    eligible = assess_batch_input(batch_input_path, repository_root)
    model = _model(eligible, _formats(include_print=include_print, include_ims=include_ims), exported_at)
    output_root.mkdir(parents=True, exist_ok=True)
    staging = Path(tempfile.mkdtemp(prefix=".m11-batch-export-", dir=output_root))
    try:
        shutil.copyfile(eligible.batch_input_path, staging / "batch-input.json")
        emitted: list[Path] = [staging / "batch-input.json"]
        for format_name in model.formats:
            emitted.extend(RENDERERS[format_name](staging, model))
        manifest: dict[str, Any] = {
            "schema_version": "1.0",
            "record_type": "m11_export_batch_manifest",
            "export_id": "PENDING",
            "package_version": model.package_version,
            "exported_at": model.exported_at,
            "batch_input_id": eligible.batch_input["batch_input_id"],
            "batch_input_sha256": sha256_file(staging / "batch-input.json"),
            "formats": list(model.formats),
            "answer_materials": model.answer_materials,
            "renderer_profiles": _RENDERER_PROFILES,
            "content_counts": {"lessons": len(model.lessons), "exercise_sets": len(model.exercise_sets), "ai_practice_prompts": len(model.prompts)},
            "files": _inventory(staging, emitted),
            "content_lifecycle_status": "UNREVIEWED",
            "required_source_permission": "redistribute_text",
            "static_limitations": STATIC_LIMITATIONS,
        }
        manifest["export_id"] = identity("m11batchexport", manifest, "export_id")
        validate_instance(manifest, "m11-export-batch-manifest")
        _write_json(staging / "manifest.json", manifest)
        receipt = build_batch_verification(staging, repository_root.resolve(), require_receipt=False)
        _write_json(staging / "verification.json", receipt)
        _fsync_directory(staging)
        destination = output_root / manifest["export_id"]
        _rename_directory_noreplace(staging, destination)
        try:
            _fsync_directory(output_root)
        except OSError:
            pass
        return destination
    except BaseException:
        shutil.rmtree(staging, ignore_errors=True)
        raise


def _compare_rebuilt(bundle: Path, manifest: Mapping[str, Any], model: ExportModel) -> None:
    with tempfile.TemporaryDirectory(prefix="m11-batch-verify-") as temporary:
        root = Path(temporary)
        for format_name in model.formats:
            RENDERERS[format_name](root, model)
        rebuilt = {path.relative_to(root).as_posix(): (path.stat().st_size, sha256_file(path)) for path in root.rglob("*") if path.is_file()}
    declared = {item["path"]: (item["bytes"], item["sha256"]) for item in manifest["files"] if item["path"] != "batch-input.json"}
    if rebuilt != declared:
        raise ExportVerificationError("rendered payload inventory does not match deterministic reconstruction")


def build_batch_verification(bundle: Path, repository_root: Path, *, require_receipt: bool) -> dict[str, Any]:
    """Independently reconstruct and verify a direct local-batch export."""

    try:
        manifest = load_json(bundle / "manifest.json")
        validate_instance(manifest, "m11-export-batch-manifest")
    except (OSError, ValueError) as error:
        raise ExportVerificationError(f"invalid batch manifest: {error}") from error
    if manifest.get("export_id") != identity("m11batchexport", manifest, "export_id"):
        raise ExportVerificationError("batch manifest export_id is not canonical")
    try:
        eligible = assess_batch_input(bundle / "batch-input.json", repository_root)
    except BatchEligibilityError as error:
        raise ExportVerificationError(str(error)) from error
    if manifest["batch_input_id"] != eligible.batch_input["batch_input_id"] or manifest["batch_input_sha256"] != sha256_file(bundle / "batch-input.json"):
        raise ExportVerificationError("batch manifest input binding mismatch")
    model = _model(eligible, manifest["formats"], manifest["exported_at"])

    expected = {item["path"] for item in manifest["files"]} | {"manifest.json", "verification.json"}
    members = list(bundle.rglob("*"))
    if any(path.is_symlink() for path in members):
        raise ExportVerificationError("batch export must not contain symbolic links")
    actual = {path.relative_to(bundle).as_posix() for path in members if path.is_file()}
    required = expected if require_receipt else expected - {"verification.json"}
    if actual != required:
        raise ExportVerificationError(f"batch inventory mismatch; missing={sorted(required-actual)!r}, unexpected={sorted(actual-required)!r}")
    _validate_payload_files(bundle, manifest)
    _compare_rebuilt(bundle, manifest, model)

    checks = ["BATCH_INPUT", "CLOSED_INVENTORY", "CSV", "DETERMINISTIC_OUTPUT", "FILE_HASHES", "HTML", "JSON", "LIFECYCLE", "SCHEMA", "SOURCE_PERMISSIONS"]
    if "PRINT_HTML" in model.formats:
        learner = (bundle / "print" / "learner.html").read_text(encoding="utf-8")
        instructor = (bundle / "print" / "instructor-answer-key.html").read_text(encoding="utf-8")
        if "Answer material:" in learner or (model.exercise_sets and "Answer material:" not in instructor):
            raise ExportVerificationError("learner/instructor answer-material separation failed")
        checks.append("ANSWER_SEPARATION")
    if "IMS_COMMON_CARTRIDGE_1_3" in model.formats:
        _validate_cartridge(bundle / "lms" / "english-master.imscc", common_cartridge_bytes(model))
        checks.extend(("ARCHIVE_CLOSURE", "XML"))

    receipt: dict[str, Any] = {
        "schema_version": "1.0",
        "record_type": "m11_export_batch_verification",
        "verification_id": "PENDING",
        "export_id": manifest["export_id"],
        "manifest_sha256": sha256_file(bundle / "manifest.json"),
        "batch_input_sha256": sha256_file(bundle / "batch-input.json"),
        "verified_at": manifest["exported_at"],
        "checks": sorted(checks),
        "verified_file_count": len(manifest["files"]),
        "result": "PASS",
        "content_lifecycle_status": "UNREVIEWED",
    }
    receipt["verification_id"] = identity("m11batchverify", receipt, "verification_id")
    validate_instance(receipt, "m11-export-batch-verification")
    if require_receipt:
        stored = load_json(bundle / "verification.json")
        validate_instance(stored, "m11-export-batch-verification")
        if stored != receipt:
            raise ExportVerificationError("stored batch verification receipt does not match independent verification")
    return receipt


def verify_batch_export(bundle: Path, repository_root: Path) -> dict[str, Any]:
    if bundle.is_symlink():
        raise ExportVerificationError("batch export directory must not be a symbolic link")
    return build_batch_verification(bundle.resolve(), repository_root.resolve(), require_receipt=True)
