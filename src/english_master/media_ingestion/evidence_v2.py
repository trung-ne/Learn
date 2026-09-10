"""M12 v2 deterministic evidence hardening and local consistency assessor.

This module is deliberately offline.  It does not acquire media or invoke an AI
provider.  An optional externally produced capture may be checked, but neither
it nor this assessor grants rights; the only assessment labels are CONSISTENT
and UNVERIFIED.
"""
from __future__ import annotations

import json
import shutil
import uuid
from pathlib import Path, PurePosixPath
from typing import Any, Mapping

from english_master.lesson_generation.canonical import identity, sha256_json
from english_master.lesson_generation.storage import _fsync_directory, _rename_directory_noreplace
from english_master.schema_validation import load_source_registry, validate_instance

from .service import (
    CHECKS,
    LIMITATIONS,
    MediaIngestionError,
    _CONTAINER_FOR_MIME,
    _MEDIA_PERMISSION_KEYS,
    _canonical_identity,
    _existing_identity,
    _inventory,
    _is_link,
    _json_bytes,
    _load,
    _parse_time,
    _safe_filename,
    _safe_local_payload,
    _safe_root,
    _sha256_bytes,
    _sha256_file,
    _source,
    _url_within,
    _verify_media_bytes,
    _write_once,
)

JsonObject = dict[str, Any]
PERMISSION_KEYS = (
    "can_download_audio", "can_download_video", "can_store", "can_clip",
    "can_transform", "can_extract_audio", "can_generate_transcript",
    "can_generate_timestamps", "can_redistribute",
)
V2_CHECKS = sorted(set(CHECKS) | {"EVIDENCE_ASSESSMENT", "EVIDENCE_SNAPSHOTS", "REGISTRY_SNAPSHOT"})
ASSESSOR_LIMITATIONS = [
    "CONSISTENT means only that local hashes, locators, and an optional capture agree structurally.",
    "This assessment never grants, discovers, or certifies copyright, license, acquisition, derivative, redistribution, human-review, or release rights.",
]


def _safe_relative(value: str) -> PurePosixPath:
    path = PurePosixPath(value)
    if path.is_absolute() or not path.parts or ".." in path.parts or "\\" in value:
        raise MediaIngestionError(f"unsafe evidence snapshot path: {value}")
    return path


def _evidence_file(root: Path, relative: str) -> Path:
    if _is_link(root) or not root.is_dir():
        raise MediaIngestionError("evidence root must be a real local directory")
    path = root.joinpath(*_safe_relative(relative).parts)
    if _is_link(path) or not path.is_file():
        raise MediaIngestionError(f"evidence snapshot must be a regular local file: {relative}")
    if any(_is_link(parent) for parent in path.absolute().parents if parent.exists()):
        raise MediaIngestionError("evidence snapshot path has a link-like component")
    try:
        path.resolve(strict=True).relative_to(root.resolve(strict=True))
    except ValueError as error:
        raise MediaIngestionError("evidence snapshot escapes evidence root") from error
    return path


def _located_bytes(content: bytes, locator: Mapping[str, Any]) -> bytes:
    if locator["kind"] == "JSON_POINTER":
        try:
            value: Any = json.loads(content.decode("utf-8"))
            pointer = str(locator["pointer"])
            if pointer:
                for encoded in pointer[1:].split("/"):
                    token = encoded.replace("~1", "/").replace("~0", "~")
                    if isinstance(value, list):
                        value = value[int(token)]
                    elif isinstance(value, dict):
                        value = value[token]
                    else:
                        raise KeyError(token)
            return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False).encode("utf-8")
        except (UnicodeError, json.JSONDecodeError, KeyError, IndexError, ValueError, TypeError) as error:
            raise MediaIngestionError(f"JSON evidence locator does not resolve: {error}") from error
    try:
        lines = content.decode("utf-8").splitlines()
    except UnicodeError as error:
        raise MediaIngestionError("text evidence is not UTF-8") from error
    start, end = int(locator["start_line"]), int(locator["end_line"])
    if end < start or end > len(lines):
        raise MediaIngestionError("text evidence line locator is outside the snapshot")
    return "\n".join(lines[start - 1:end]).encode("utf-8")


def _true_evidence(authorization: Mapping[str, Any]) -> dict[str, Mapping[str, Any]]:
    permissions = authorization["permissions"]
    entries = authorization["permission_evidence"]
    by_operation = {str(item["operation"]): item for item in entries}
    if len(by_operation) != len(entries):
        raise MediaIngestionError("permission evidence operations must be unique")
    expected = {key for key in PERMISSION_KEYS if permissions[key] is True}
    if set(by_operation) != expected:
        raise MediaIngestionError("v2 permission evidence must cover exactly the true operations")
    return by_operation


def _load_external_capture(path: Path | None, authorization: Mapping[str, Any]) -> tuple[JsonObject | None, str | None, str | None]:
    if path is None:
        return None, None, None
    try:
        raw = _safe_local_payload(path)
        value = json.loads(raw.decode("utf-8"))
        if not isinstance(value, dict):
            raise ValueError("capture is not an object")
        validate_instance(value, "media-evidence-external-capture")
        _canonical_identity(value, "mediaevidencecapture", "capture_id")
        if value["authorization_id"] != authorization["authorization_id"] or value["authorization_sha256"] != sha256_json(authorization):
            raise ValueError("capture authorization binding drift")
        return value, _sha256_bytes(raw), None
    except Exception as error:  # malformed/unavailable runner evidence is data, not promotion evidence
        try:
            capture_hash = _sha256_file(path)
        except Exception:
            capture_hash = None
        return None, capture_hash, f"external capture is unavailable or invalid: {error}"


def assess_evidence(*, authorization_path: Path, evidence_root: Path, assessment_path: Path,
                    assessed_at: str, external_capture_path: Path | None = None) -> JsonObject:
    """Assess local evidence consistency; never infer or grant permission."""
    _parse_time(assessed_at)
    authorization = _load(authorization_path, "media-source-authorization-v2")
    _canonical_identity(authorization, "mediaauth", "authorization_id")
    entries = _true_evidence(authorization)
    capture, capture_hash, capture_error = _load_external_capture(external_capture_path, authorization)
    capture_results: dict[str, Mapping[str, Any]] = {}
    if capture is not None:
        raw_results = capture["operation_results"]
        capture_results = {str(item["operation"]): item for item in raw_results}
        if len(capture_results) != len(raw_results) or set(capture_results) != set(entries):
            capture_error = "external capture operation inventory differs from true authorization operations"
            capture = None
            capture_results = {}
    operation_results: list[JsonObject] = []
    for operation in sorted(entries):
        entry = entries[operation]
        reasons: list[str] = []
        deterministic = "CONSISTENT"
        try:
            path = _evidence_file(evidence_root, str(entry["snapshot_path"]))
            content = path.read_bytes()
            if len(content) != entry["snapshot_bytes"] or _sha256_bytes(content) != entry["snapshot_sha256"]:
                raise MediaIngestionError("evidence snapshot hash or size differs from authorization")
            located = _located_bytes(content, entry["locator"])
            if _sha256_bytes(located) != entry["located_value_sha256"]:
                raise MediaIngestionError("located evidence value hash differs from authorization")
            reasons.append("local snapshot, size, hash, locator, and located value are consistent")
        except (MediaIngestionError, OSError) as error:
            deterministic = "UNVERIFIED"
            reasons.append(str(error))
        external_result: str | None = None
        if external_capture_path is not None:
            if capture_error is not None:
                external_result = "UNVERIFIED"
                reasons.append(capture_error)
            else:
                external_result = str(capture_results[operation]["result"])
                reasons.append(f"external runner reported {external_result}: {capture_results[operation]['reason']}")
        result = "CONSISTENT" if deterministic == "CONSISTENT" and external_result in {None, "CONSISTENT"} and (capture is None or capture["overall_result"] == "CONSISTENT") else "UNVERIFIED"
        operation_results.append({
            "operation": operation, "snapshot_path": entry["snapshot_path"], "snapshot_sha256": entry["snapshot_sha256"],
            "locator": entry["locator"], "located_value_sha256": entry["located_value_sha256"],
            "deterministic_result": deterministic, "external_result": external_result, "result": result, "reasons": reasons,
        })
    overall = "CONSISTENT" if operation_results and all(item["result"] == "CONSISTENT" for item in operation_results) else "UNVERIFIED"
    assessment: JsonObject = {
        "schema_version": "1.0", "record_type": "media_evidence_assessment", "assessment_id": "PENDING",
        "authorization_id": authorization["authorization_id"], "authorization_sha256": sha256_json(authorization), "assessed_at": assessed_at,
        "assessor_mode": "DETERMINISTIC_WITH_EXTERNAL_CAPTURE" if external_capture_path is not None else "DETERMINISTIC_LOCAL",
        "external_capture_sha256": capture_hash, "operation_results": operation_results, "overall_result": overall,
        "rights_granted": False, "limitations": ASSESSOR_LIMITATIONS,
    }
    assessment["assessment_id"] = identity("mediaevidenceassessment", assessment, "assessment_id")
    validate_instance(assessment, "media-evidence-assessment")
    _write_once(assessment_path.absolute(), _json_bytes(assessment))
    return assessment


def _verify_registry_path(authorization: Mapping[str, Any], registry_path: Path) -> bytes:
    if _is_link(registry_path) or not registry_path.is_file() or any(_is_link(parent) for parent in registry_path.absolute().parents if parent.exists()):
        raise MediaIngestionError("source registry must be a regular local file without link-like components")
    declared = PurePosixPath(str(authorization["registry_path"]))
    actual = PurePosixPath(registry_path.absolute().as_posix())
    if declared.is_absolute() or ".." in declared.parts or tuple(actual.parts[-len(declared.parts):]) != declared.parts:
        raise MediaIngestionError("source registry path differs from the pinned authorization path")
    content = registry_path.read_bytes()
    if _sha256_bytes(content) != authorization["registry_sha256"]:
        raise MediaIngestionError("source registry hash drift")
    return content


def _verify_authorization_v2(authorization: Mapping[str, Any], registry_path: Path, *, at: str,
                             enforce_declared_path: bool = True) -> bytes:
    _canonical_identity(authorization, "mediaauth", "authorization_id")
    if authorization["authorization_mode"] != "OFFLINE_TEST_FIXTURE_ONLY" or authorization["fixture_only"] is not True:
        raise MediaIngestionError("only offline test-fixture authorization is accepted")
    registry_bytes = _verify_registry_path(authorization, registry_path) if enforce_declared_path else registry_path.read_bytes()
    if _sha256_bytes(registry_bytes) != authorization["registry_sha256"]:
        raise MediaIngestionError("retained source registry hash drift")
    registry = load_source_registry(registry_path)
    source = _source(registry, str(authorization["source_id"]))
    if source.get("source_url") != authorization["source_url"] or source.get("license", {}).get("name") != authorization["license"] or source.get("license", {}).get("url") != authorization["license_url"]:
        raise MediaIngestionError("authorization source or license projection differs from the registry")
    bases = [str(source["source_url"])]
    access = source.get("access", {})
    bases.extend(str(access[key]) for key in ("dataset_url", "api_url") if isinstance(access.get(key), str))
    if not _url_within(str(authorization["official_record_url"]), bases):
        raise MediaIngestionError("official record URL is outside the registered source routes")
    if not _safe_filename(str(authorization["expected_filename"])):
        raise MediaIngestionError("unsafe authorized filename")
    operation_time, authorized_at, expires_at = _parse_time(at), _parse_time(str(authorization["authorized_at"])), _parse_time(str(authorization["expires_at"]))
    if authorized_at > operation_time or expires_at < operation_time or authorized_at >= expires_at:
        raise MediaIngestionError("authorization is not active at the declared operation time")
    kind, permissions = str(authorization["media_kind"]), authorization["permissions"]
    required = {"can_store", "can_download_audio" if kind == "AUDIO" else "can_download_video"}
    if any(permissions[key] is not True for key in required):
        raise MediaIngestionError("record authorization does not explicitly permit download and storage")
    _true_evidence(authorization)
    registry_requirements = {
        "can_store": "store_allowed", "can_download_audio": "download_allowed" if kind == "AUDIO" else None,
        "can_download_video": "download_allowed" if kind == "VIDEO" else None, "can_clip": "clip_allowed",
        "can_transform": "transform_allowed" if kind == "AUDIO" else None,
        "can_extract_audio": "audio_extraction_allowed" if kind == "VIDEO" else None,
        "can_generate_transcript": "transcript_allowed", "can_generate_timestamps": "timestamp_allowed",
        "can_redistribute": "redistribute_allowed",
    }
    media_permissions = source.get("media_permissions", {}).get(kind.lower(), {})
    for key, registry_key in registry_requirements.items():
        if permissions[key] and (registry_key is None or media_permissions.get(registry_key) is not True):
            raise MediaIngestionError(f"record permission {key} exceeds source registry permission")
    metadata = authorization["expected_metadata"]
    if metadata["container"] != _CONTAINER_FOR_MIME[authorization["expected_mime_type"]]:
        raise MediaIngestionError("container and MIME metadata conflict")
    if kind == "AUDIO" and (metadata["width"] is not None or metadata["height"] is not None):
        raise MediaIngestionError("audio metadata cannot declare dimensions")
    if kind == "VIDEO" and (metadata["width"] is None or metadata["height"] is None):
        raise MediaIngestionError("video metadata must declare dimensions")
    return registry_bytes


def _verify_assessment(authorization: Mapping[str, Any], assessment: Mapping[str, Any]) -> None:
    _canonical_identity(assessment, "mediaevidenceassessment", "assessment_id")
    if assessment["authorization_id"] != authorization["authorization_id"] or assessment["authorization_sha256"] != sha256_json(authorization):
        raise MediaIngestionError("evidence assessment authorization binding drift")
    if assessment["overall_result"] != "CONSISTENT" or assessment["rights_granted"] is not False:
        raise MediaIngestionError("evidence assessment is UNVERIFIED and cannot support this run")
    evidence = _true_evidence(authorization)
    results = {str(item["operation"]): item for item in assessment["operation_results"]}
    if len(results) != len(assessment["operation_results"]) or set(results) != set(evidence):
        raise MediaIngestionError("evidence assessment does not consistently cover every true operation")
    for operation, entry in evidence.items():
        result = results[operation]
        projection = {
            "snapshot_path": entry["snapshot_path"], "snapshot_sha256": entry["snapshot_sha256"],
            "locator": entry["locator"], "located_value_sha256": entry["located_value_sha256"],
        }
        if any(result.get(key) != value for key, value in projection.items()):
            raise MediaIngestionError("evidence assessment snapshot or locator binding drift")
        if result["deterministic_result"] != "CONSISTENT" or result["result"] != "CONSISTENT" or result["external_result"] not in {None, "CONSISTENT"}:
            raise MediaIngestionError("evidence assessment does not consistently cover every true operation")
    if assessment["assessor_mode"] == "DETERMINISTIC_LOCAL" and assessment["external_capture_sha256"] is not None:
        raise MediaIngestionError("deterministic-only assessment cannot bind an external capture")
    if assessment["assessor_mode"] == "DETERMINISTIC_WITH_EXTERNAL_CAPTURE" and assessment["external_capture_sha256"] is None:
        raise MediaIngestionError("external-capture assessment is missing its capture hash")


def _verify_external_capture(capture: Mapping[str, Any], authorization: Mapping[str, Any], assessment: Mapping[str, Any]) -> None:
    _canonical_identity(capture, "mediaevidencecapture", "capture_id")
    if capture["authorization_id"] != authorization["authorization_id"] or capture["authorization_sha256"] != sha256_json(authorization):
        raise MediaIngestionError("external capture authorization binding drift")
    evidence_operations = set(_true_evidence(authorization))
    results = capture["operation_results"]
    by_operation = {str(item["operation"]): item for item in results}
    if len(by_operation) != len(results) or set(by_operation) != evidence_operations:
        raise MediaIngestionError("external capture operation inventory drift")
    if capture["overall_result"] != "CONSISTENT" or any(item["result"] != "CONSISTENT" for item in results):
        raise MediaIngestionError("external capture is UNVERIFIED")
    assessed = {str(item["operation"]): item for item in assessment["operation_results"]}
    if any(assessed[operation]["external_result"] != by_operation[operation]["result"] for operation in evidence_operations):
        raise MediaIngestionError("external capture differs from the assessment")


def prepare_v2(*, authorization_path: Path, payload_path: Path, registry_path: Path, assessment_path: Path,
               receipt_path: Path, acquired_at: str) -> JsonObject:
    authorization = _load(authorization_path, "media-source-authorization-v2")
    registry_bytes = _verify_authorization_v2(authorization, registry_path, at=acquired_at)
    assessment = _load(assessment_path, "media-evidence-assessment")
    _verify_assessment(authorization, assessment)
    content = _safe_local_payload(payload_path)
    if payload_path.name != authorization["expected_filename"]:
        raise MediaIngestionError("payload filename differs from authorization")
    observed_hash, observed_bytes = _sha256_bytes(content), len(content)
    if observed_hash != authorization["expected_payload_sha256"] or observed_bytes != authorization["expected_payload_bytes"]:
        raise MediaIngestionError("payload hash or size differs from authorization")
    _verify_media_bytes(content, payload_path.name, str(authorization["expected_mime_type"]))
    receipt: JsonObject = {
        "schema_version": "2.0", "record_type": "media_acquisition_receipt", "receipt_id": "PENDING",
        "authorization_id": authorization["authorization_id"], "authorization_sha256": sha256_json(authorization),
        "assessment_id": assessment["assessment_id"], "assessment_sha256": sha256_json(assessment), "registry_sha256": _sha256_bytes(registry_bytes),
        "source_id": authorization["source_id"], "source_record_id": authorization["source_record_id"], "official_record_url": authorization["official_record_url"],
        "filename": authorization["expected_filename"], "expected_payload_sha256": authorization["expected_payload_sha256"], "expected_payload_bytes": authorization["expected_payload_bytes"],
        "observed_payload_sha256": observed_hash, "observed_payload_bytes": observed_bytes, "payload_matches_authorization": True,
        "mime_type": authorization["expected_mime_type"], "media_kind": authorization["media_kind"], "metadata": authorization["expected_metadata"],
        "acquisition_method": "LOCAL_TEST_FIXTURE", "fixture_only": True, "acquired_at": acquired_at,
    }
    receipt["receipt_id"] = identity("mediareceipt", receipt, "receipt_id")
    validate_instance(receipt, "media-acquisition-receipt-v2")
    _write_once(receipt_path.absolute(), _json_bytes(receipt))
    return receipt


def _verify_receipt_v2(authorization: Mapping[str, Any], assessment: Mapping[str, Any], receipt: Mapping[str, Any], content: bytes) -> bool:
    _canonical_identity(receipt, "mediareceipt", "receipt_id")
    observed_hash, observed_bytes = _sha256_bytes(content), len(content)
    expected = {
        "authorization_id": authorization["authorization_id"], "authorization_sha256": sha256_json(authorization),
        "assessment_id": assessment["assessment_id"], "assessment_sha256": sha256_json(assessment), "registry_sha256": authorization["registry_sha256"],
        "source_id": authorization["source_id"], "source_record_id": authorization["source_record_id"], "official_record_url": authorization["official_record_url"],
        "filename": authorization["expected_filename"], "expected_payload_sha256": authorization["expected_payload_sha256"], "expected_payload_bytes": authorization["expected_payload_bytes"],
        "mime_type": authorization["expected_mime_type"], "media_kind": authorization["media_kind"], "metadata": authorization["expected_metadata"],
    }
    if any(receipt.get(key) != value for key, value in expected.items()):
        raise MediaIngestionError("acquisition receipt binding drift")
    if receipt["observed_payload_sha256"] != authorization["expected_payload_sha256"] or receipt["observed_payload_bytes"] != authorization["expected_payload_bytes"]:
        raise MediaIngestionError("acquisition receipt did not verify the authorized payload")
    return observed_hash == authorization["expected_payload_sha256"] and observed_bytes == authorization["expected_payload_bytes"]


def _copy_evidence(stage: Path, authorization: Mapping[str, Any], evidence_root: Path) -> list[tuple[str, str]]:
    paths: list[tuple[str, str]] = []
    written: set[str] = set()
    for entry in _true_evidence(authorization).values():
        relative = _safe_relative(str(entry["snapshot_path"]))
        source = _evidence_file(evidence_root, str(relative))
        content = source.read_bytes()
        if len(content) != entry["snapshot_bytes"] or _sha256_bytes(content) != entry["snapshot_sha256"]:
            raise MediaIngestionError("evidence snapshot changed after assessment")
        target_relative = PurePosixPath("evidence") / relative
        if target_relative.as_posix() in written:
            continue
        target = stage.joinpath(*target_relative.parts)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(content)
        paths.append((target_relative.as_posix(), "EVIDENCE_SNAPSHOT"))
        written.add(target_relative.as_posix())
    return paths


def run_v2(*, authorization_path: Path, receipt_path: Path, payload_path: Path, registry_path: Path,
           assessment_path: Path, evidence_root: Path, data_root: Path, completed_at: str,
           external_capture_path: Path | None = None) -> Path:
    media_root = _safe_root(data_root)
    authorization = _load(authorization_path, "media-source-authorization-v2")
    registry_bytes = _verify_authorization_v2(authorization, registry_path, at=completed_at)
    assessment = _load(assessment_path, "media-evidence-assessment")
    _verify_assessment(authorization, assessment)
    if external_capture_path is None:
        if assessment["external_capture_sha256"] is not None:
            raise MediaIngestionError("assessment requires its external capture")
        external_bytes = None
    else:
        external_bytes = _safe_local_payload(external_capture_path)
        if _sha256_bytes(external_bytes) != assessment["external_capture_sha256"]:
            raise MediaIngestionError("external capture hash differs from assessment")
        capture = _load(external_capture_path, "media-evidence-external-capture")
        _verify_external_capture(capture, authorization, assessment)
    receipt = _load(receipt_path, "media-acquisition-receipt-v2")
    content = _safe_local_payload(payload_path)
    quarantine_reason: tuple[str, str] | None = None
    try:
        payload_matches = _verify_receipt_v2(authorization, assessment, receipt, content)
        if payload_path.name != authorization["expected_filename"]:
            raise MediaIngestionError("payload filename differs from authorization")
        _verify_media_bytes(content, payload_path.name, str(authorization["expected_mime_type"]))
        if not payload_matches:
            raise MediaIngestionError("payload hash or size differs from authorization")
    except MediaIngestionError as error:
        payload_matches = _sha256_bytes(content) == authorization["expected_payload_sha256"] and len(content) == authorization["expected_payload_bytes"]
        message = str(error)
        code = "CHECKSUM_MISMATCH" if "hash or size" in message or "binding drift" in message else "MIME_EXTENSION_MISMATCH" if "MIME" in message else "PAYLOAD_MALFORMED"
        quarantine_reason = (code, message)
    existing = _existing_identity(media_root, str(authorization["source_id"]), str(authorization["source_record_id"]))
    if existing is not None:
        code = "DUPLICATE_IDENTITY" if existing[0] == _sha256_bytes(content) else "DUPLICATE_IDENTITY_DRIFT"
        quarantine_reason = (code, f"source identity already exists as {existing[1]}")
    return _publish_run_v2(media_root=media_root, authorization=authorization, assessment=assessment, receipt=receipt,
                           content=content, registry_bytes=registry_bytes, evidence_root=evidence_root,
                           completed_at=completed_at, quarantine_reason=quarantine_reason, external_bytes=external_bytes)


def _publish_run_v2(*, media_root: Path, authorization: Mapping[str, Any], assessment: Mapping[str, Any],
                    receipt: Mapping[str, Any], content: bytes, registry_bytes: bytes, evidence_root: Path,
                    completed_at: str, quarantine_reason: tuple[str, str] | None, external_bytes: bytes | None) -> Path:
    auth_hash, assessment_hash, receipt_hash = sha256_json(authorization), sha256_json(assessment), sha256_json(receipt)
    observed_hash, observed_bytes = _sha256_bytes(content), len(content)
    payload_matches = observed_hash == authorization["expected_payload_sha256"] and observed_bytes == authorization["expected_payload_bytes"]
    seed = {"authorization_id": authorization["authorization_id"], "receipt_id": receipt["receipt_id"], "assessment_id": assessment["assessment_id"], "payload_sha256": observed_hash, "completed_at": completed_at, "outcome": "QUARANTINED" if quarantine_reason else "STORED"}
    run_id = f"mediarun_{sha256_json(seed)}"
    branch = "quarantine" if quarantine_reason else "originals"
    destination = media_root / branch / run_id
    if destination.exists() or _is_link(destination):
        raise FileExistsError(f"immutable media run already exists: {destination}")
    destination.parent.mkdir(parents=True, exist_ok=True)
    stage = media_root / f".media-v2-staging-{uuid.uuid4().hex}"
    try:
        stage.mkdir(parents=True, exist_ok=False); (stage / "payload").mkdir()
        (stage / "authorization.json").write_bytes(_json_bytes(authorization))
        (stage / "evidence-assessment.json").write_bytes(_json_bytes(assessment))
        (stage / "acquisition-receipt.json").write_bytes(_json_bytes(receipt))
        (stage / "registry-snapshot.yaml").write_bytes(registry_bytes)
        payload_target = stage / "payload" / str(authorization["expected_filename"]); payload_target.write_bytes(content)
        paths = [
            ("authorization.json", "AUTHORIZATION"), ("evidence-assessment.json", "EVIDENCE_ASSESSMENT"),
            ("acquisition-receipt.json", "ACQUISITION_RECEIPT"), ("registry-snapshot.yaml", "SOURCE_REGISTRY_SNAPSHOT"),
            (f"payload/{payload_target.name}", "PAYLOAD"),
        ]
        paths.extend(_copy_evidence(stage, authorization, evidence_root))
        if external_bytes is not None:
            (stage / "external-runner-capture.json").write_bytes(external_bytes); paths.append(("external-runner-capture.json", "EXTERNAL_CAPTURE"))
        asset_id: str | None = None; quarantine_id: str | None = None
        if quarantine_reason:
            code, reason = quarantine_reason
            quarantine: JsonObject = {
                "schema_version": "1.0", "record_type": "media_quarantine_record", "quarantine_id": "PENDING",
                "authorization_id": authorization["authorization_id"], "authorization_sha256": auth_hash,
                "source_id": authorization["source_id"], "source_record_id": authorization["source_record_id"], "payload_filename": authorization["expected_filename"],
                "observed_sha256": observed_hash, "observed_bytes": observed_bytes, "reason_code": code, "reason": reason,
                "quarantine_path": f"quarantine/{run_id}/payload/{payload_target.name}", "quarantined_at": completed_at,
                "fixture_only": True, "content_lifecycle_status": "UNREVIEWED", "approval_tier": "NONE", "redistribution_authorized": False,
            }
            quarantine["quarantine_id"] = identity("mediaquarantine", quarantine, "quarantine_id"); quarantine_id = quarantine["quarantine_id"]
            validate_instance(quarantine, "media-quarantine-record"); (stage / "quarantine-record.json").write_bytes(_json_bytes(quarantine)); paths.append(("quarantine-record.json", "QUARANTINE_RECORD"))
        else:
            asset: JsonObject = {
                "schema_version": "1.0", "record_type": "media_asset_metadata", "asset_id": "PENDING",
                "authorization_id": authorization["authorization_id"], "authorization_sha256": auth_hash, "receipt_id": receipt["receipt_id"], "receipt_sha256": receipt_hash,
                "source_id": authorization["source_id"], "source_record_id": authorization["source_record_id"], "media_kind": authorization["media_kind"],
                "original_filename": authorization["expected_filename"], "stored_path": f"originals/{run_id}/payload/{payload_target.name}",
                "payload_sha256": observed_hash, "payload_bytes": observed_bytes, "mime_type": authorization["expected_mime_type"], "metadata": authorization["expected_metadata"],
                "license": authorization["license"], "license_url": authorization["license_url"], "attribution": authorization["attribution"], "imported_at": completed_at,
                "fixture_only": True, "content_lifecycle_status": "UNREVIEWED", "approval_tier": "MACHINE_VALIDATED", "redistribution_authorized": bool(authorization["permissions"]["can_redistribute"]),
            }
            asset["asset_id"] = identity("mediaasset", asset, "asset_id"); asset_id = asset["asset_id"]
            validate_instance(asset, "media-asset-metadata"); (stage / "asset-metadata.json").write_bytes(_json_bytes(asset)); paths.append(("asset-metadata.json", "ASSET_METADATA"))
        inventory = _inventory(stage, paths)
        report: JsonObject = {
            "schema_version": "2.0", "record_type": "media_run_report", "run_id": run_id,
            "authorization_id": authorization["authorization_id"], "authorization_sha256": auth_hash,
            "assessment_id": assessment["assessment_id"], "assessment_sha256": assessment_hash,
            "receipt_id": receipt["receipt_id"], "receipt_sha256": receipt_hash, "registry_snapshot_path": "registry-snapshot.yaml", "registry_sha256": _sha256_bytes(registry_bytes),
            "source_id": authorization["source_id"], "source_record_id": authorization["source_record_id"], "started_at": receipt["acquired_at"], "completed_at": completed_at,
            "outcome": "QUARANTINED" if quarantine_reason else "STORED", "asset_id": asset_id, "quarantine_id": quarantine_id,
            "expected_payload_sha256": authorization["expected_payload_sha256"], "expected_payload_bytes": authorization["expected_payload_bytes"],
            "observed_payload_sha256": observed_hash, "observed_payload_bytes": observed_bytes, "payload_matches_authorization": payload_matches,
            "inventory": inventory, "inventory_sha256": sha256_json(inventory), "checks": V2_CHECKS,
            "fixture_only": True, "network_accessed": False, "derivatives_created": 0, "content_lifecycle_status": "UNREVIEWED", "approval_tier": "MACHINE_VALIDATED",
            "redistribution_authorized": bool(authorization["permissions"]["can_redistribute"]) if not quarantine_reason else False, "limitations": LIMITATIONS + ASSESSOR_LIMITATIONS,
        }
        validate_instance(report, "media-run-report-v2"); (stage / "run-report.json").write_bytes(_json_bytes(report))
        verification = _build_verification_v2(stage, completed_at, require_stored=False); (stage / "verification-report.json").write_bytes(_json_bytes(verification))
        _fsync_directory(stage / "payload"); _fsync_directory(stage); _rename_directory_noreplace(stage, destination); _fsync_directory(destination.parent)
        return destination
    except BaseException:
        if stage.exists() or _is_link(stage): shutil.rmtree(stage, ignore_errors=True)
        raise


def _build_verification_v2(directory: Path, verified_at: str, *, require_stored: bool) -> JsonObject:
    if _is_link(directory): raise MediaIngestionError("media run cannot be a link")
    root = directory.resolve(strict=True)
    if not root.is_dir() or _is_link(root): raise MediaIngestionError("media run must be a real directory")
    for path in root.rglob("*"):
        if _is_link(path) or (path.exists() and not path.is_file() and not path.is_dir()): raise MediaIngestionError(f"unsafe path in media run: {path}")
    report = _load(root / "run-report.json", "media-run-report-v2")
    expected = {item["path"] for item in report["inventory"]} | {"run-report.json", "verification-report.json"}
    actual = {path.relative_to(root).as_posix() for path in root.rglob("*") if path.is_file()}
    expected_actual = expected if require_stored else expected - {"verification-report.json"}
    if actual != expected_actual: raise MediaIngestionError(f"closed inventory mismatch; missing={sorted(expected_actual-actual)!r}, unexpected={sorted(actual-expected_actual)!r}")
    if report["inventory_sha256"] != sha256_json(report["inventory"]): raise MediaIngestionError("run inventory hash drift")
    for item in report["inventory"]:
        relative = _safe_relative(str(item["path"])); path = root.joinpath(*relative.parts)
        if not path.is_file() or path.stat().st_size != item["bytes"] or _sha256_file(path) != item["sha256"]: raise MediaIngestionError(f"inventoried file drift: {item['path']}")
    authorization = _load(root / "authorization.json", "media-source-authorization-v2")
    assessment = _load(root / "evidence-assessment.json", "media-evidence-assessment")
    receipt = _load(root / "acquisition-receipt.json", "media-acquisition-receipt-v2")
    _verify_assessment(authorization, assessment)
    capture_entries = [item for item in report["inventory"] if item["role"] == "EXTERNAL_CAPTURE"]
    if assessment["external_capture_sha256"] is None:
        if capture_entries:
            raise MediaIngestionError("unexpected external capture in deterministic-only run")
    else:
        if len(capture_entries) != 1 or capture_entries[0]["sha256"] != assessment["external_capture_sha256"]:
            raise MediaIngestionError("retained external capture binding drift")
        capture_path = root.joinpath(*_safe_relative(str(capture_entries[0]["path"])).parts)
        capture = _load(capture_path, "media-evidence-external-capture")
        _verify_external_capture(capture, authorization, assessment)
    registry_path = root / str(report["registry_snapshot_path"])
    _verify_authorization_v2(authorization, registry_path, at=str(report["completed_at"]), enforce_declared_path=False)
    evidence_root = root / "evidence"
    for entry in _true_evidence(authorization).values():
        content = _evidence_file(evidence_root, str(entry["snapshot_path"])).read_bytes()
        if len(content) != entry["snapshot_bytes"] or _sha256_bytes(content) != entry["snapshot_sha256"] or _sha256_bytes(_located_bytes(content, entry["locator"])) != entry["located_value_sha256"]:
            raise MediaIngestionError("retained evidence snapshot binding drift")
    payload_entries = [item for item in report["inventory"] if item["role"] == "PAYLOAD"]
    if len(payload_entries) != 1: raise MediaIngestionError("run must inventory exactly one payload")
    payload = root.joinpath(*_safe_relative(str(payload_entries[0]["path"])).parts); content = payload.read_bytes()
    payload_matches = _verify_receipt_v2(authorization, assessment, receipt, content)
    observed_hash, observed_bytes = _sha256_bytes(content), len(content)
    report_binding = {
        "authorization_id": authorization["authorization_id"], "authorization_sha256": sha256_json(authorization), "assessment_id": assessment["assessment_id"], "assessment_sha256": sha256_json(assessment),
        "receipt_id": receipt["receipt_id"], "receipt_sha256": sha256_json(receipt), "registry_sha256": authorization["registry_sha256"],
        "expected_payload_sha256": authorization["expected_payload_sha256"], "expected_payload_bytes": authorization["expected_payload_bytes"],
        "observed_payload_sha256": observed_hash, "observed_payload_bytes": observed_bytes, "payload_matches_authorization": payload_matches,
    }
    if any(report.get(key) != value for key, value in report_binding.items()): raise MediaIngestionError("run authority, registry, or payload binding drift")
    if report["outcome"] == "STORED" and not payload_matches: raise MediaIngestionError("stored payload does not match authorization")
    if report["outcome"] == "STORED":
        asset = _load(root / "asset-metadata.json", "media-asset-metadata"); _canonical_identity(asset, "mediaasset", "asset_id")
        if report["asset_id"] != asset["asset_id"] or asset["stored_path"] != f"originals/{report['run_id']}/{payload_entries[0]['path']}": raise MediaIngestionError("asset metadata binding drift")
    else:
        quarantine = _load(root / "quarantine-record.json", "media-quarantine-record"); _canonical_identity(quarantine, "mediaquarantine", "quarantine_id")
        if report["quarantine_id"] != quarantine["quarantine_id"] or quarantine["quarantine_path"] != f"quarantine/{report['run_id']}/{payload_entries[0]['path']}": raise MediaIngestionError("quarantine metadata binding drift")
    verification: JsonObject = {
        "schema_version": "2.0", "record_type": "media_verification_report", "verification_id": "PENDING", "run_id": report["run_id"],
        "run_report_sha256": sha256_json(report), "authorization_sha256": sha256_json(authorization), "assessment_sha256": sha256_json(assessment), "receipt_sha256": sha256_json(receipt), "registry_sha256": authorization["registry_sha256"],
        "expected_payload_sha256": authorization["expected_payload_sha256"], "expected_payload_bytes": authorization["expected_payload_bytes"], "observed_payload_sha256": observed_hash, "observed_payload_bytes": observed_bytes, "payload_matches_authorization": payload_matches,
        "verified_at": verified_at, "verified_inventory": report["inventory"], "checks": V2_CHECKS, "result": "PASS", "fixture_only": True, "network_accessed": False, "approval_tier": "MACHINE_VALIDATED", "content_lifecycle_status": "UNREVIEWED",
    }
    verification["verification_id"] = identity("mediaverify", verification, "verification_id"); validate_instance(verification, "media-verification-report-v2")
    if require_stored:
        stored = _load(root / "verification-report.json", "media-verification-report-v2")
        if stored != verification: raise MediaIngestionError("stored verification does not match independent reconstruction")
    return verification


def verify_v2(*, run_directory: Path) -> JsonObject:
    stored = _load(run_directory / "verification-report.json", "media-verification-report-v2")
    return _build_verification_v2(run_directory, str(stored["verified_at"]), require_stored=True)
