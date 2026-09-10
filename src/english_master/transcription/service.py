"""Atomic fixture-only transcription orchestration and read-only verification."""
from __future__ import annotations

import json
from pathlib import Path, PurePosixPath
from typing import Any, Mapping

from english_master.lesson_generation.canonical import identity, sha256_json
from english_master.media_ingestion.lineage import VerifiedMediaLineage, verify_media_lineage
from english_master.media_ingestion.service import MediaIngestionError
from english_master.schema_validation import load_document, validate_instance

from .models import CHECKS, LEGACY_CHECKS, LEGACY_STAGES, LIMITATIONS, STAGES, JsonObject, TranscriptionError
from .safety import (
    atomic_publish,
    inventory,
    is_link,
    json_bytes,
    load_record,
    local_path_matches,
    require_real_directory,
    require_regular_file,
    safe_output_root,
    sha256_bytes,
    sha256_file,
)
from .validation import (
    build_artifact,
    build_processing_plan,
    parse_time,
    require_canonical,
    validate_artifact,
    validate_authority,
    validate_processing_plan,
    validate_request,
)


def _parent_records(media_run_directory: Path) -> VerifiedMediaLineage:
    try:
        lineage = verify_media_lineage(media_run_directory)
    except (MediaIngestionError, OSError, ValueError) as error:
        raise TranscriptionError(f"M12 parent verification failed: {error}") from error
    if lineage.report["outcome"] != "STORED":
        raise TranscriptionError("only a stored M12 media fixture can be transcribed")
    return lineage


def _run_id(
    authorization: Mapping[str, Any], request: Mapping[str, Any], started_at: str,
    completed_at: str, plan: Mapping[str, Any] | None = None,
) -> str:
    seed = {
        "authorization_id": authorization["authorization_id"],
        "request_id": request["request_id"],
        "fixture_segments_sha256": request["fixture_segments_sha256"],
        "started_at": started_at,
        "completed_at": completed_at,
    }
    if plan is not None:
        seed["processing_plan_id"] = plan["plan_id"]
        seed["processing_plan_sha256"] = sha256_json(plan)
    return f"transrun_{sha256_json(seed)}"


def _build_receipts(
    run_id: str, authorization: Mapping[str, Any], request: Mapping[str, Any],
    artifact: Mapping[str, Any], checked_at: str, plan: Mapping[str, Any] | None = None,
) -> list[tuple[str, JsonObject]]:
    if plan is None:
        stages = LEGACY_STAGES
        inputs = [sha256_json(authorization), sha256_json(request), str(request["fixture_segments_sha256"]), sha256_json(artifact)]
        schema_name = "transcription-stage-receipt"
    else:
        stages = STAGES
        inputs = [sha256_json(authorization), sha256_json(request), sha256_json(plan), str(request["fixture_segments_sha256"]), sha256_json(artifact)]
        schema_name = "transcription-stage-receipt-v2"
    result: list[tuple[str, JsonObject]] = []
    for (sequence, stage, path, checks), input_hash in zip(stages, inputs, strict=True):
        receipt: JsonObject = {
            "schema_version": "2.0" if plan is not None else "1.0", "record_type": "transcription_stage_receipt", "receipt_id": "PENDING",
            "run_id": run_id, "sequence": sequence, "stage": stage, "input_sha256": input_hash,
            "status": "PASS", "checked_at": checked_at, "checks": list(checks), "fixture_only": True, "network_accessed": False,
        }
        receipt["receipt_id"] = identity("transreceipt", receipt, "receipt_id")
        validate_instance(receipt, schema_name)
        result.append((path, receipt))
    return result


def _validate_chronology(authorization: Mapping[str, Any], request: Mapping[str, Any], started_at: str, completed_at: str) -> None:
    authorized = parse_time(str(authorization["authorized_at"]), "authorized_at")
    requested = parse_time(str(request["requested_at"]), "requested_at")
    started = parse_time(started_at, "started_at")
    completed = parse_time(completed_at, "completed_at")
    expires = parse_time(str(authorization["expires_at"]), "expires_at")
    if not (authorized <= requested <= started <= completed <= expires):
        raise TranscriptionError("timestamps must satisfy authorized <= requested <= started <= completed <= expires")


def run(
    *, authorization_path: Path, request_path: Path, media_run_directory: Path,
    registry_path: Path, data_root: Path, started_at: str, completed_at: str,
) -> Path:
    """Create one immutable transcript bundle from inline deterministic fixture segments."""
    require_regular_file(registry_path, "source registry")
    media_directory = require_real_directory(media_run_directory, "M12 media run")
    authorization = load_record(authorization_path, "transcription-authorization-v2")
    request = load_record(request_path, "transcription-request-v2")
    local_path_matches(str(authorization["registry_path"]), registry_path, "source registry path")
    local_path_matches(str(authorization["media_run_path"]), media_directory, "M12 media run path")
    parent = _parent_records(media_directory)
    if parent.schema_version != "2.0":
        raise TranscriptionError("new M13 derivatives require a verified M12 v2 parent; M12 v1 is verification-only")
    validate_authority(
        authorization,
        registry_path=registry_path,
        parent_authorization=parent.authorization,
        parent_receipt=parent.receipt,
        parent_report=parent.report,
        parent_asset=parent.asset,
        parent_verification=parent.verification,
        parent_assessment=parent.assessment,
        media_schema_version=parent.schema_version,
        evidence_root=media_directory / "evidence",
    )
    validate_request(authorization, request)
    _validate_chronology(authorization, request, started_at, completed_at)
    plan = build_processing_plan(authorization, request, started_at)
    artifact = build_artifact(authorization, request, completed_at, plan)
    run_id = _run_id(authorization, request, started_at, completed_at, plan)
    receipts = _build_receipts(run_id, authorization, request, artifact, completed_at, plan)
    runs_root = safe_output_root(data_root)
    destination = runs_root / run_id

    def populate(stage: Path) -> None:
        (stage / "receipts").mkdir()
        records = {
            "authorization.json": authorization,
            "request.json": request,
            "processing-plan.json": plan,
            "transcript-artifact.json": artifact,
            "parent-media-authorization.json": parent.authorization,
            "parent-media-acquisition-receipt.json": parent.receipt,
            "parent-media-run-report.json": parent.report,
            "parent-media-verification.json": parent.verification,
            "parent-media-asset.json": parent.asset,
        }
        if parent.assessment is not None:
            records["parent-media-evidence-assessment.json"] = parent.assessment
        paths: list[tuple[str, str]] = []
        roles = {
            "authorization.json": "AUTHORIZATION", "request.json": "REQUEST", "processing-plan.json": "PROCESSING_PLAN", "transcript-artifact.json": "TRANSCRIPT_ARTIFACT",
            "parent-media-authorization.json": "PARENT_MEDIA_AUTHORIZATION", "parent-media-acquisition-receipt.json": "PARENT_MEDIA_ACQUISITION_RECEIPT",
            "parent-media-run-report.json": "PARENT_MEDIA_RUN_REPORT", "parent-media-verification.json": "PARENT_MEDIA_VERIFICATION",
            "parent-media-evidence-assessment.json": "PARENT_MEDIA_EVIDENCE_ASSESSMENT", "parent-media-asset.json": "PARENT_MEDIA_ASSET",
        }
        for name, value in records.items():
            (stage / name).write_bytes(json_bytes(value)); paths.append((name, roles[name]))
        copied_evidence: set[str] = set()
        for evidence in authorization["permission_evidence"]:
            retained = str(evidence["retained_snapshot_path"])
            if retained in copied_evidence:
                continue
            source_relative = PurePosixPath(str(evidence["snapshot_path"]))
            source = media_directory.joinpath("evidence", *source_relative.parts)
            require_regular_file(source, "parent permission-evidence snapshot")
            content = source.read_bytes()
            if len(content) != evidence["snapshot_bytes"] or sha256_bytes(content) != evidence["snapshot_sha256"]:
                raise TranscriptionError("parent permission-evidence snapshot changed after authority validation")
            target = stage.joinpath(*PurePosixPath(retained).parts)
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(content)
            paths.append((retained, "PARENT_PERMISSION_EVIDENCE"))
            copied_evidence.add(retained)
        (stage / "source-registry.yaml").write_bytes(registry_path.read_bytes()); paths.append(("source-registry.yaml", "SOURCE_REGISTRY"))
        receipt_refs: list[JsonObject] = []
        for path, receipt in receipts:
            target = stage.joinpath(*PurePosixPath(path).parts)
            target.write_bytes(json_bytes(receipt)); paths.append((path, "STAGE_RECEIPT"))
            receipt_refs.append({"sequence": receipt["sequence"], "stage": receipt["stage"], "path": path, "receipt_id": receipt["receipt_id"], "sha256": sha256_json(receipt)})
        contents = inventory(stage, paths)
        manifest: JsonObject = {
            "schema_version": "2.0", "record_type": "transcription_run_manifest", "run_id": run_id,
            "authorization_id": authorization["authorization_id"], "authorization_sha256": sha256_json(authorization),
            "request_id": request["request_id"], "request_sha256": sha256_json(request),
            "processing_plan_id": plan["plan_id"], "processing_plan_sha256": sha256_json(plan),
            "artifact_id": artifact["artifact_id"], "artifact_sha256": sha256_json(artifact),
            "media_schema_version": parent.schema_version,
            "media_run_id": authorization["media_run_id"], "media_run_report_sha256": sha256_json(parent.report),
            "media_acquisition_receipt_id": parent.receipt["receipt_id"], "media_acquisition_receipt_sha256": sha256_json(parent.receipt),
            "media_verification_id": parent.verification["verification_id"], "media_verification_sha256": sha256_json(parent.verification),
            "media_evidence_assessment_id": parent.assessment["assessment_id"] if parent.assessment is not None else None,
            "media_evidence_assessment_sha256": sha256_json(parent.assessment) if parent.assessment is not None else None,
            "media_asset_id": authorization["media_asset_id"],
            "started_at": started_at, "completed_at": completed_at, "outcome": "COMPLETED", "stage_receipts": receipt_refs,
            "inventory": contents, "inventory_sha256": sha256_json(contents), "checks": CHECKS,
            "fixture_only": True, "network_accessed": False, "provider_invoked": False, "model_invoked": False,
            "content_lifecycle_status": "UNREVIEWED", "approval_tier": "MACHINE_VALIDATED", "redistribution_authorized": False, "limitations": LIMITATIONS,
        }
        validate_instance(manifest, "transcription-run-manifest-v2")
        (stage / "run-manifest.json").write_bytes(json_bytes(manifest))
        verification = _build_verification(stage, completed_at, require_stored=False)
        (stage / "verification.json").write_bytes(json_bytes(verification))

    atomic_publish(runs_root, destination, populate)
    return destination


def _load_versioned(path: Path, legacy_schema: str, hardened_schema: str) -> JsonObject:
    require_regular_file(path, path.name)
    value = load_document(path)
    if not isinstance(value, dict):
        raise TranscriptionError(f"{path.name} must contain an object")
    version = value.get("schema_version")
    validate_instance(value, hardened_schema if version == "2.0" else legacy_schema)
    return value


def _load_registry(path: Path) -> JsonObject:
    require_regular_file(path, "source registry snapshot")
    try:
        value = load_document(path)
        validate_instance(value, "source-registry")
        return value
    except (OSError, ValueError) as error:
        raise TranscriptionError(f"invalid source registry snapshot: {error}") from error


def _build_verification(directory: Path, verified_at: str, *, require_stored: bool) -> JsonObject:
    root = require_real_directory(directory, "transcription run")
    for path in root.rglob("*"):
        if is_link(path) or (path.exists() and not path.is_file() and not path.is_dir()):
            raise TranscriptionError(f"unsafe path in transcription run: {path}")
    manifest = _load_versioned(root / "run-manifest.json", "transcription-run-manifest", "transcription-run-manifest-v2")
    hardened = manifest["schema_version"] == "2.0"
    expected = {item["path"] for item in manifest["inventory"]} | {"run-manifest.json", "verification.json"}
    actual = {path.relative_to(root).as_posix() for path in root.rglob("*") if path.is_file()}
    expected_actual = expected if require_stored else expected - {"verification.json"}
    if actual != expected_actual:
        raise TranscriptionError(f"closed inventory mismatch; missing={sorted(expected_actual-actual)!r}, unexpected={sorted(actual-expected_actual)!r}")
    if manifest["inventory_sha256"] != sha256_json(manifest["inventory"]):
        raise TranscriptionError("inventory hash drift")
    inventory_paths = [str(item["path"]) for item in manifest["inventory"]]
    if len(inventory_paths) != len(set(inventory_paths)):
        raise TranscriptionError("inventory paths must be unique")
    expected_roles = {
        "authorization.json": "AUTHORIZATION", "request.json": "REQUEST", "transcript-artifact.json": "TRANSCRIPT_ARTIFACT",
        "source-registry.yaml": "SOURCE_REGISTRY", "parent-media-authorization.json": "PARENT_MEDIA_AUTHORIZATION",
        "parent-media-acquisition-receipt.json": "PARENT_MEDIA_ACQUISITION_RECEIPT", "parent-media-run-report.json": "PARENT_MEDIA_RUN_REPORT",
        "parent-media-verification.json": "PARENT_MEDIA_VERIFICATION", "parent-media-asset.json": "PARENT_MEDIA_ASSET",
    }
    if hardened:
        expected_roles.update({"processing-plan.json": "PROCESSING_PLAN", "parent-media-evidence-assessment.json": "PARENT_MEDIA_EVIDENCE_ASSESSMENT"})
    role_by_path = {str(item["path"]): str(item["role"]) for item in manifest["inventory"]}
    if any(role_by_path.get(path) != role for path, role in expected_roles.items()):
        raise TranscriptionError("closed inventory role binding drift")
    for item in manifest["inventory"]:
        relative = PurePosixPath(item["path"])
        if relative.is_absolute() or ".." in relative.parts or "\\" in item["path"]:
            raise TranscriptionError("unsafe inventory path")
        path = root.joinpath(*relative.parts)
        if not path.is_file() or path.stat().st_size != item["bytes"] or sha256_file(path) != item["sha256"]:
            raise TranscriptionError(f"inventoried file drift: {item['path']}")
    authorization = _load_versioned(root / "authorization.json", "transcription-authorization", "transcription-authorization-v2")
    request = _load_versioned(root / "request.json", "transcription-request", "transcription-request-v2")
    artifact = _load_versioned(root / "transcript-artifact.json", "transcript-artifact", "transcript-artifact-v2")
    plan = load_record(root / "processing-plan.json", "transcription-processing-plan-v2") if hardened else None
    if (authorization.get("schema_version") == "2.0") != hardened or (request.get("schema_version") == "2.0") != hardened or (artifact.get("schema_version") == "2.0") != hardened:
        raise TranscriptionError("M13 record schema versions differ within the run")
    expected_receipt_paths = {path for _, _, path, _ in (STAGES if hardened else LEGACY_STAGES)}
    actual_receipt_paths = {path for path, role in role_by_path.items() if role == "STAGE_RECEIPT"}
    if actual_receipt_paths != expected_receipt_paths:
        raise TranscriptionError("closed stage-receipt inventory drift")
    if hardened:
        evidence_paths = {str(item["retained_snapshot_path"]) for item in authorization["permission_evidence"]}
        actual_evidence_paths = {path for path, role in role_by_path.items() if role == "PARENT_PERMISSION_EVIDENCE"}
        if actual_evidence_paths != evidence_paths:
            raise TranscriptionError("closed permission-evidence inventory drift")
    media_version = str(manifest["media_schema_version"])
    if media_version == "1.0":
        parent_authorization = load_record(root / "parent-media-authorization.json", "media-source-authorization")
        parent_receipt = load_record(root / "parent-media-acquisition-receipt.json", "media-acquisition-receipt")
        parent_report = load_record(root / "parent-media-run-report.json", "media-run-report")
        parent_verification = load_record(root / "parent-media-verification.json", "media-verification-report")
        parent_assessment = None
    elif media_version == "2.0":
        parent_authorization = load_record(root / "parent-media-authorization.json", "media-source-authorization-v2")
        parent_receipt = load_record(root / "parent-media-acquisition-receipt.json", "media-acquisition-receipt-v2")
        parent_report = load_record(root / "parent-media-run-report.json", "media-run-report-v2")
        parent_verification = load_record(root / "parent-media-verification.json", "media-verification-report-v2")
        parent_assessment = load_record(root / "parent-media-evidence-assessment.json", "media-evidence-assessment")
    else:
        raise TranscriptionError("unsupported parent M12 schema version")
    parent_asset = load_record(root / "parent-media-asset.json", "media-asset-metadata")
    _load_registry(root / "source-registry.yaml")
    validate_authority(
        authorization,
        registry_path=root / "source-registry.yaml",
        parent_authorization=parent_authorization,
        parent_receipt=parent_receipt,
        parent_report=parent_report,
        parent_asset=parent_asset,
        parent_verification=parent_verification,
        parent_assessment=parent_assessment,
        media_schema_version=media_version,
        evidence_root=root if hardened else None,
        use_retained_evidence_paths=hardened,
        allow_legacy_parent=not hardened,
    )
    validate_request(authorization, request)
    if hardened:
        assert plan is not None
        validate_processing_plan(authorization, request, plan)
    _validate_chronology(authorization, request, str(manifest["started_at"]), str(manifest["completed_at"]))
    validate_artifact(authorization, request, artifact, plan)
    if manifest["run_id"] != _run_id(authorization, request, str(manifest["started_at"]), str(manifest["completed_at"]), plan):
        raise TranscriptionError("run ID does not reconstruct canonically")
    bindings = {
        "authorization_id": authorization["authorization_id"], "authorization_sha256": sha256_json(authorization),
        "request_id": request["request_id"], "request_sha256": sha256_json(request),
        "artifact_id": artifact["artifact_id"], "artifact_sha256": sha256_json(artifact),
        "media_schema_version": media_version, "media_run_id": authorization["media_run_id"],
        "media_run_report_sha256": sha256_json(parent_report),
        "media_acquisition_receipt_id": parent_receipt["receipt_id"], "media_acquisition_receipt_sha256": sha256_json(parent_receipt),
        "media_verification_id": parent_verification["verification_id"], "media_verification_sha256": sha256_json(parent_verification),
        "media_evidence_assessment_id": parent_assessment["assessment_id"] if parent_assessment is not None else None,
        "media_evidence_assessment_sha256": sha256_json(parent_assessment) if parent_assessment is not None else None,
        "media_asset_id": authorization["media_asset_id"],
    }
    if hardened:
        assert plan is not None
        bindings.update({"processing_plan_id": plan["plan_id"], "processing_plan_sha256": sha256_json(plan)})
    if any(manifest.get(key) != value for key, value in bindings.items()):
        raise TranscriptionError("run manifest binding drift")
    expected_receipts = _build_receipts(str(manifest["run_id"]), authorization, request, artifact, str(manifest["completed_at"]), plan)
    refs: list[JsonObject] = []
    for path, expected_receipt in expected_receipts:
        stored = load_record(root.joinpath(*PurePosixPath(path).parts), "transcription-stage-receipt-v2" if hardened else "transcription-stage-receipt")
        if stored != expected_receipt:
            raise TranscriptionError(f"stage receipt drift: {path}")
        refs.append({"sequence": stored["sequence"], "stage": stored["stage"], "path": path, "receipt_id": stored["receipt_id"], "sha256": sha256_json(stored)})
    if manifest["stage_receipts"] != refs:
        raise TranscriptionError("stage receipt inventory drift")
    verification: JsonObject = {
        "schema_version": "2.0" if hardened else "1.0", "record_type": "transcription_verification", "verification_id": "PENDING",
        "run_id": manifest["run_id"], "manifest_sha256": sha256_json(manifest), "authorization_sha256": sha256_json(authorization),
        "request_sha256": sha256_json(request), "artifact_sha256": sha256_json(artifact),
        "media_schema_version": media_version, "media_run_report_sha256": sha256_json(parent_report),
        "media_acquisition_receipt_sha256": sha256_json(parent_receipt),
        "media_verification_id": parent_verification["verification_id"], "media_verification_sha256": sha256_json(parent_verification),
        "media_evidence_assessment_sha256": sha256_json(parent_assessment) if parent_assessment is not None else None,
        "verified_at": verified_at,
        "verified_inventory": manifest["inventory"], "checks": CHECKS if hardened else LEGACY_CHECKS, "result": "PASS", "fixture_only": True,
        "network_accessed": False, "provider_invoked": False, "model_invoked": False, "content_lifecycle_status": "UNREVIEWED", "approval_tier": "MACHINE_VALIDATED",
    }
    if hardened:
        assert plan is not None
        verification["processing_plan_sha256"] = sha256_json(plan)
    verification["verification_id"] = identity("transverify", verification, "verification_id")
    validate_instance(verification, "transcription-verification-v2" if hardened else "transcription-verification")
    if require_stored:
        stored = _load_versioned(root / "verification.json", "transcription-verification", "transcription-verification-v2")
        if stored != verification:
            raise TranscriptionError("stored verification differs from independent reconstruction")
    return verification


def verify(*, run_directory: Path) -> JsonObject:
    """Read-only verify one complete immutable fixture transcript run."""
    stored = _load_versioned(run_directory / "verification.json", "transcription-verification", "transcription-verification-v2")
    return _build_verification(run_directory, str(stored["verified_at"]), require_stored=True)
