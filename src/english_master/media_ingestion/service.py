"""Offline fixture-only controlled media ingestion for M12."""
from __future__ import annotations

import hashlib
import json
import os
import shutil
import tempfile
import uuid
from datetime import datetime, timezone
from pathlib import Path, PurePath, PurePosixPath
from typing import Any, Mapping
from urllib.parse import urlsplit

from english_master.lesson_generation.canonical import identity, sha256_json
from english_master.lesson_generation.storage import _fsync_directory, _rename_directory_noreplace
from english_master.schema_validation import SchemaValidationError, load_source_registry, validate_instance

JsonObject = dict[str, Any]
CHECKS = [
    "AUTHORIZATION_BINDING", "CHECKSUM", "CLOSED_INVENTORY", "DUPLICATE_IDENTITY",
    "FIXTURE_BOUNDARY", "MEDIA_METADATA", "MIME_EXTENSION", "PATH_SAFETY",
    "PERMISSIONS", "PROVENANCE", "SOURCE_REGISTRY",
]
LIMITATIONS = [
    "This run imports only a caller-supplied offline test fixture; it is not real media acquisition.",
    "Static fixture validation is not transcript QA, public-release authority, or live-provider evidence.",
]
_PERMISSION_KEYS = (
    "can_download_audio", "can_download_video", "can_store", "can_clip",
    "can_transform", "can_extract_audio", "can_generate_transcript", "can_redistribute",
)
_MEDIA_PERMISSION_KEYS = {
    "AUDIO": {"download": "download_allowed", "store": "store_allowed", "clip": "clip_allowed", "transform": "transform_allowed", "transcript": "transcript_allowed", "redistribute": "redistribute_allowed"},
    "VIDEO": {"download": "download_allowed", "store": "store_allowed", "clip": "clip_allowed", "transform": None, "extract": "audio_extraction_allowed", "transcript": "transcript_allowed", "redistribute": "redistribute_allowed"},
}
_MIME_EXTENSIONS = {
    "audio/wav": {".wav"}, "audio/mpeg": {".mp3"}, "audio/ogg": {".ogg", ".oga"},
    "video/mp4": {".mp4", ".m4v"}, "video/webm": {".webm"},
}
_CONTAINER_FOR_MIME = {"audio/wav": "WAV", "audio/mpeg": "MP3", "audio/ogg": "OGG", "video/mp4": "MP4", "video/webm": "WEBM"}


class MediaIngestionError(ValueError):
    """Raised when the fixture boundary or immutable media store is invalid."""


def _sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _json_bytes(value: Mapping[str, Any]) -> bytes:
    return (json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2, allow_nan=False) + "\n").encode("utf-8")


def _load(path: Path, schema: str) -> JsonObject:
    if path.is_symlink() or not path.is_file():
        raise MediaIngestionError(f"{schema} must be a regular file: {path}")
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(value, dict):
            raise ValueError("document is not an object")
        validate_instance(value, schema)
    except (OSError, UnicodeError, json.JSONDecodeError, SchemaValidationError, ValueError) as error:
        raise MediaIngestionError(f"invalid {schema}: {error}") from error
    return value


def _canonical_identity(value: Mapping[str, Any], prefix: str, field: str) -> None:
    if value.get(field) != identity(prefix, value, field):
        raise MediaIngestionError(f"{field} does not reconstruct canonically")


def _safe_filename(name: str) -> bool:
    path = PurePath(name)
    return bool(name) and not path.is_absolute() and path.name == name and name not in {".", ".."} and "\\" not in name and "/" not in name and ":" not in name


def _is_link(path: Path) -> bool:
    return path.is_symlink() or (hasattr(path, "is_junction") and path.is_junction())


def _safe_root(data_root: Path) -> Path:
    root = data_root.absolute()
    lowered = {part.lower() for part in root.parts}
    if lowered.intersection({"approved", "curriculum", "exports"}):
        raise MediaIngestionError("media data root cannot be inside approved, curriculum, or export storage")
    if any(_is_link(parent) for parent in (root, *root.parents) if parent.exists()):
        raise MediaIngestionError("media data root has a link-like ancestor")
    return root / "media"


def _safe_local_payload(path: Path) -> bytes:
    if str(path).startswith(("http://", "https://")) or "://" in str(path):
        raise MediaIngestionError("network URLs are not accepted; supply a local fixture")
    if _is_link(path) or not path.is_file():
        raise MediaIngestionError("payload must be a regular local file")
    if any(_is_link(parent) for parent in path.absolute().parents if parent.exists()):
        raise MediaIngestionError("payload path has a link-like ancestor")
    return path.read_bytes()


def _parse_time(value: str) -> datetime:
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as error:
        raise MediaIngestionError(f"invalid operation timestamp: {value}") from error
    if parsed.tzinfo is None:
        raise MediaIngestionError("operation timestamp must have an explicit offset")
    return parsed.astimezone(timezone.utc)


def _source(registry: Mapping[str, Any], source_id: str) -> Mapping[str, Any]:
    matches = [item for item in registry.get("sources", []) if isinstance(item, Mapping) and item.get("source_id") == source_id]
    if len(matches) != 1:
        raise MediaIngestionError("authorization source is not uniquely registered")
    source = matches[0]
    if source.get("status") != "APPROVED":
        raise MediaIngestionError("media source is not APPROVED")
    return source


def _url_within(candidate: str, bases: list[str]) -> bool:
    actual = urlsplit(candidate)
    if actual.scheme != "https" or actual.username or actual.password:
        return False
    for raw_base in bases:
        base = urlsplit(raw_base)
        if actual.hostname == base.hostname and actual.port == base.port and (actual.path == base.path or actual.path.startswith(base.path.rstrip("/") + "/")):
            return True
    return False


def _verify_authorization(authorization: Mapping[str, Any], registry_path: Path, *, at: str) -> Mapping[str, Any]:
    _canonical_identity(authorization, "mediaauth", "authorization_id")
    if authorization["authorization_mode"] != "OFFLINE_TEST_FIXTURE_ONLY" or authorization["fixture_only"] is not True:
        raise MediaIngestionError("only offline test-fixture authorization is accepted")
    registry_bytes = registry_path.read_bytes()
    declared_registry = PurePosixPath(str(authorization["registry_path"]))
    actual_registry = PurePosixPath(registry_path.absolute().as_posix())
    if declared_registry.is_absolute() or ".." in declared_registry.parts or tuple(actual_registry.parts[-len(declared_registry.parts):]) != declared_registry.parts:
        raise MediaIngestionError("source registry path differs from the pinned authorization path")
    if _is_link(registry_path) or any(_is_link(parent) for parent in registry_path.absolute().parents if parent.exists()):
        raise MediaIngestionError("source registry path has a link-like component")
    if authorization["registry_sha256"] != _sha256_bytes(registry_bytes):
        raise MediaIngestionError("source registry hash drift")
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
    operation_time = _parse_time(at)
    authorized_at = _parse_time(str(authorization["authorized_at"]))
    expires_at = _parse_time(str(authorization["expires_at"]))
    if authorized_at > operation_time or expires_at < operation_time or authorized_at >= expires_at:
        raise MediaIngestionError("authorization is not active at the declared operation time")
    kind = str(authorization["media_kind"])
    permissions = authorization["permissions"]
    required = {"can_store", "can_download_audio" if kind == "AUDIO" else "can_download_video"}
    if any(permissions[key] is not True for key in required):
        raise MediaIngestionError("record authorization does not explicitly permit download and storage")
    evidence_ops = {item["operation"] for item in authorization["permission_evidence"]}
    if set(_PERMISSION_KEYS) != evidence_ops:
        raise MediaIngestionError("permission evidence must cover every explicit record operation")
    media_permissions = source.get("media_permissions", {}).get(kind.lower(), {})
    registry_requirements = {
        "can_store": "store_allowed",
        "can_download_audio": "download_allowed" if kind == "AUDIO" else None,
        "can_download_video": "download_allowed" if kind == "VIDEO" else None,
        "can_clip": "clip_allowed", "can_transform": "transform_allowed" if kind == "AUDIO" else None,
        "can_extract_audio": "audio_extraction_allowed" if kind == "VIDEO" else None,
        "can_generate_transcript": "transcript_allowed", "can_redistribute": "redistribute_allowed",
    }
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
    return source


def _verify_media_bytes(content: bytes, filename: str, mime_type: str) -> None:
    if Path(filename).suffix.lower() not in _MIME_EXTENSIONS[mime_type]:
        raise MediaIngestionError("MIME type and filename extension conflict")
    signatures = {
        "audio/wav": len(content) >= 12 and content[:4] == b"RIFF" and content[8:12] == b"WAVE",
        "audio/mpeg": content.startswith(b"ID3") or (len(content) >= 2 and content[0] == 0xFF and content[1] & 0xE0 == 0xE0),
        "audio/ogg": content.startswith(b"OggS"),
        "video/mp4": len(content) >= 12 and content[4:8] == b"ftyp",
        "video/webm": content.startswith(b"\x1aE\xdf\xa3"),
    }
    if not signatures[mime_type]:
        raise MediaIngestionError("payload signature does not match the authorized MIME type")


def _verify_payload(authorization: Mapping[str, Any], payload_path: Path) -> bytes:
    content = _safe_local_payload(payload_path)
    if payload_path.name != authorization["expected_filename"]:
        raise MediaIngestionError("payload filename differs from authorization")
    if len(content) != authorization["expected_payload_bytes"] or _sha256_bytes(content) != authorization["expected_payload_sha256"]:
        raise MediaIngestionError("payload bytes differ from authorization")
    _verify_media_bytes(content, payload_path.name, str(authorization["expected_mime_type"]))
    return content


def _write_once(path: Path, content: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists() or _is_link(path):
        raise FileExistsError(f"refusing to overwrite immutable output: {path}")
    descriptor, temporary_name = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
    temporary = Path(temporary_name)
    try:
        with os.fdopen(descriptor, "wb") as stream:
            stream.write(content); stream.flush(); os.fsync(stream.fileno())
        os.link(temporary, path)
    finally:
        temporary.unlink(missing_ok=True)


def prepare(*, authorization_path: Path, payload_path: Path, registry_path: Path, receipt_path: Path, acquired_at: str) -> JsonObject:
    """Validate explicit fixture authority and write one immutable acquisition receipt."""
    authorization = _load(authorization_path, "media-source-authorization")
    _verify_authorization(authorization, registry_path, at=acquired_at)
    content = _verify_payload(authorization, payload_path)
    receipt: JsonObject = {
        "schema_version": "1.0", "record_type": "media_acquisition_receipt", "receipt_id": "PENDING",
        "authorization_id": authorization["authorization_id"], "authorization_sha256": sha256_json(authorization),
        "source_id": authorization["source_id"], "source_record_id": authorization["source_record_id"], "official_record_url": authorization["official_record_url"],
        "filename": authorization["expected_filename"], "payload_sha256": _sha256_bytes(content), "payload_bytes": len(content),
        "mime_type": authorization["expected_mime_type"], "media_kind": authorization["media_kind"], "metadata": authorization["expected_metadata"],
        "acquisition_method": "LOCAL_TEST_FIXTURE", "fixture_only": True, "acquired_at": acquired_at, "checksum_verified": True,
    }
    receipt["receipt_id"] = identity("mediareceipt", receipt, "receipt_id")
    validate_instance(receipt, "media-acquisition-receipt")
    _write_once(receipt_path.absolute(), _json_bytes(receipt))
    return receipt


def _verify_receipt(authorization: Mapping[str, Any], receipt: Mapping[str, Any], content: bytes) -> None:
    _canonical_identity(receipt, "mediareceipt", "receipt_id")
    expected = {
        "authorization_id": authorization["authorization_id"], "authorization_sha256": sha256_json(authorization), "source_id": authorization["source_id"],
        "source_record_id": authorization["source_record_id"], "official_record_url": authorization["official_record_url"], "filename": authorization["expected_filename"],
        "payload_sha256": authorization["expected_payload_sha256"], "payload_bytes": authorization["expected_payload_bytes"], "mime_type": authorization["expected_mime_type"], "media_kind": authorization["media_kind"], "metadata": authorization["expected_metadata"],
    }
    if any(receipt.get(key) != value for key, value in expected.items()):
        raise MediaIngestionError("acquisition receipt binding drift")


def _existing_identity(media_root: Path, source_id: str, source_record_id: str) -> tuple[str, str] | None:
    for path in sorted(media_root.glob("originals/*/asset-metadata.json")):
        if _is_link(path):
            raise MediaIngestionError("controlled media store contains a link")
        try:
            value = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as error:
            raise MediaIngestionError(f"cannot inspect existing media identity: {error}") from error
        if value.get("source_id") == source_id and value.get("source_record_id") == source_record_id:
            return str(value.get("payload_sha256")), str(value.get("asset_id"))
    return None


def _inventory(stage: Path, paths: list[tuple[str, str]]) -> list[JsonObject]:
    result = []
    for relative, role in sorted(paths):
        path = stage / Path(*PurePosixPath(relative).parts)
        result.append({"path": relative, "bytes": path.stat().st_size, "sha256": _sha256_file(path), "role": role})
    return result


def _publish_run(*, media_root: Path, authorization: Mapping[str, Any], receipt: Mapping[str, Any], content: bytes, completed_at: str, quarantine_reason: tuple[str, str] | None) -> Path:
    authorization_hash, receipt_hash = sha256_json(authorization), sha256_json(receipt)
    seed = {"authorization_id": authorization["authorization_id"], "receipt_id": receipt["receipt_id"], "payload_sha256": _sha256_bytes(content), "completed_at": completed_at, "outcome": "QUARANTINED" if quarantine_reason else "STORED"}
    run_id = f"mediarun_{sha256_json(seed)}"
    branch = "quarantine" if quarantine_reason else "originals"
    destination = media_root / branch / run_id
    if destination.exists() or _is_link(destination):
        raise FileExistsError(f"immutable media run already exists: {destination}")
    destination.parent.mkdir(parents=True, exist_ok=True)
    if any(_is_link(parent) for parent in destination.parents if parent.exists()):
        raise MediaIngestionError("media destination has a link-like ancestor")
    stage = media_root / f".media-staging-{uuid.uuid4().hex}"
    try:
        stage.mkdir(parents=True, exist_ok=False)
        (stage / "payload").mkdir()
        (stage / "authorization.json").write_bytes(_json_bytes(authorization))
        (stage / "acquisition-receipt.json").write_bytes(_json_bytes(receipt))
        payload_target = stage / "payload" / str(authorization["expected_filename"])
        payload_target.write_bytes(content)
        paths = [("authorization.json", "AUTHORIZATION"), ("acquisition-receipt.json", "ACQUISITION_RECEIPT"), (f"payload/{payload_target.name}", "PAYLOAD")]
        asset_id: str | None = None
        quarantine_id: str | None = None
        if quarantine_reason:
            code, reason = quarantine_reason
            quarantine: JsonObject = {
                "schema_version": "1.0", "record_type": "media_quarantine_record", "quarantine_id": "PENDING", "authorization_id": authorization["authorization_id"], "authorization_sha256": authorization_hash,
                "source_id": authorization["source_id"], "source_record_id": authorization["source_record_id"], "payload_filename": authorization["expected_filename"], "observed_sha256": _sha256_bytes(content), "observed_bytes": len(content),
                "reason_code": code, "reason": reason, "quarantine_path": f"quarantine/{run_id}/payload/{payload_target.name}", "quarantined_at": completed_at,
                "fixture_only": True, "content_lifecycle_status": "UNREVIEWED", "approval_tier": "NONE", "redistribution_authorized": False,
            }
            quarantine["quarantine_id"] = identity("mediaquarantine", quarantine, "quarantine_id")
            quarantine_id = quarantine["quarantine_id"]
            validate_instance(quarantine, "media-quarantine-record")
            (stage / "quarantine-record.json").write_bytes(_json_bytes(quarantine)); paths.append(("quarantine-record.json", "QUARANTINE_RECORD"))
        else:
            asset: JsonObject = {
                "schema_version": "1.0", "record_type": "media_asset_metadata", "asset_id": "PENDING", "authorization_id": authorization["authorization_id"], "authorization_sha256": authorization_hash,
                "receipt_id": receipt["receipt_id"], "receipt_sha256": receipt_hash, "source_id": authorization["source_id"], "source_record_id": authorization["source_record_id"], "media_kind": authorization["media_kind"],
                "original_filename": authorization["expected_filename"], "stored_path": f"originals/{run_id}/payload/{payload_target.name}", "payload_sha256": _sha256_bytes(content), "payload_bytes": len(content),
                "mime_type": authorization["expected_mime_type"], "metadata": authorization["expected_metadata"], "license": authorization["license"], "license_url": authorization["license_url"], "attribution": authorization["attribution"],
                "imported_at": completed_at, "fixture_only": True, "content_lifecycle_status": "UNREVIEWED", "approval_tier": "MACHINE_VALIDATED", "redistribution_authorized": bool(authorization["permissions"]["can_redistribute"]),
            }
            asset["asset_id"] = identity("mediaasset", asset, "asset_id"); asset_id = asset["asset_id"]
            validate_instance(asset, "media-asset-metadata")
            (stage / "asset-metadata.json").write_bytes(_json_bytes(asset)); paths.append(("asset-metadata.json", "ASSET_METADATA"))
        inventory = _inventory(stage, paths)
        report: JsonObject = {
            "schema_version": "1.0", "record_type": "media_run_report", "run_id": run_id, "authorization_id": authorization["authorization_id"], "authorization_sha256": authorization_hash,
            "receipt_id": receipt["receipt_id"], "receipt_sha256": receipt_hash, "source_id": authorization["source_id"], "source_record_id": authorization["source_record_id"], "started_at": receipt["acquired_at"], "completed_at": completed_at,
            "outcome": "QUARANTINED" if quarantine_reason else "STORED", "asset_id": asset_id, "quarantine_id": quarantine_id, "inventory": inventory, "inventory_sha256": sha256_json(inventory), "checks": CHECKS,
            "fixture_only": True, "network_accessed": False, "derivatives_created": 0, "content_lifecycle_status": "UNREVIEWED", "approval_tier": "MACHINE_VALIDATED", "redistribution_authorized": bool(authorization["permissions"]["can_redistribute"]) if not quarantine_reason else False, "limitations": LIMITATIONS,
        }
        validate_instance(report, "media-run-report")
        (stage / "run-report.json").write_bytes(_json_bytes(report))
        verification = _build_verification(stage, completed_at, require_stored=False)
        (stage / "verification-report.json").write_bytes(_json_bytes(verification))
        _fsync_directory(stage / "payload"); _fsync_directory(stage)
        _rename_directory_noreplace(stage, destination); _fsync_directory(destination.parent)
        return destination
    except BaseException:
        if stage.exists() or _is_link(stage):
            shutil.rmtree(stage, ignore_errors=True)
        raise


def run(*, authorization_path: Path, receipt_path: Path, payload_path: Path, registry_path: Path, data_root: Path, completed_at: str) -> Path:
    """Import one verified local media fixture into an immutable controlled bundle."""
    media_root = _safe_root(data_root)
    authorization = _load(authorization_path, "media-source-authorization")
    _verify_authorization(authorization, registry_path, at=completed_at)
    content = _safe_local_payload(payload_path)
    receipt = _load(receipt_path, "media-acquisition-receipt")
    quarantine: tuple[str, str] | None = None
    try:
        _verify_payload(authorization, payload_path)
        _verify_receipt(authorization, receipt, content)
    except MediaIngestionError as error:
        message = str(error)
        code = "CHECKSUM_MISMATCH" if "bytes differ" in message or "binding drift" in message else "MIME_EXTENSION_MISMATCH" if "MIME" in message else "PAYLOAD_MALFORMED"
        quarantine = (code, message)
    existing = _existing_identity(media_root, str(authorization["source_id"]), str(authorization["source_record_id"]))
    if existing is not None:
        code = "DUPLICATE_IDENTITY" if existing[0] == _sha256_bytes(content) else "DUPLICATE_IDENTITY_DRIFT"
        quarantine = (code, f"source identity already exists as {existing[1]}")
    return _publish_run(media_root=media_root, authorization=authorization, receipt=receipt, content=content, completed_at=completed_at, quarantine_reason=quarantine)


def _build_verification(directory: Path, verified_at: str, *, require_stored: bool) -> JsonObject:
    if _is_link(directory):
        raise MediaIngestionError("media run cannot be a link")
    root = directory.resolve(strict=True)
    if not root.is_dir() or _is_link(root):
        raise MediaIngestionError("media run must be a real directory")
    for path in root.rglob("*"):
        if _is_link(path) or (path.exists() and not path.is_file() and not path.is_dir()):
            raise MediaIngestionError(f"unsafe path in media run: {path}")
    report = _load(root / "run-report.json", "media-run-report")
    expected = {item["path"] for item in report["inventory"]} | {"run-report.json", "verification-report.json"}
    actual = {path.relative_to(root).as_posix() for path in root.rglob("*") if path.is_file()}
    expected_actual = expected if require_stored else expected - {"verification-report.json"}
    if actual != expected_actual:
        raise MediaIngestionError(f"closed inventory mismatch; missing={sorted(expected_actual-actual)!r}, unexpected={sorted(actual-expected_actual)!r}")
    if report["inventory_sha256"] != sha256_json(report["inventory"]):
        raise MediaIngestionError("run inventory hash drift")
    for item in report["inventory"]:
        relative = PurePosixPath(item["path"])
        if relative.is_absolute() or ".." in relative.parts or "\\" in item["path"]:
            raise MediaIngestionError("unsafe inventory path")
        path = root.joinpath(*relative.parts)
        if not path.is_file() or path.stat().st_size != item["bytes"] or _sha256_file(path) != item["sha256"]:
            raise MediaIngestionError(f"inventoried file drift: {item['path']}")
    authorization = _load(root / "authorization.json", "media-source-authorization")
    receipt = _load(root / "acquisition-receipt.json", "media-acquisition-receipt")
    _canonical_identity(authorization, "mediaauth", "authorization_id"); _canonical_identity(receipt, "mediareceipt", "receipt_id")
    if report["authorization_id"] != authorization["authorization_id"] or report["authorization_sha256"] != sha256_json(authorization) or report["receipt_id"] != receipt["receipt_id"] or report["receipt_sha256"] != sha256_json(receipt):
        raise MediaIngestionError("run authority binding drift")
    payload_entries = [item for item in report["inventory"] if item["role"] == "PAYLOAD"]
    if len(payload_entries) != 1:
        raise MediaIngestionError("run must inventory exactly one payload")
    payload = root.joinpath(*PurePosixPath(payload_entries[0]["path"]).parts)
    content = payload.read_bytes()
    _verify_receipt(authorization, receipt, content)
    if report["outcome"] == "STORED":
        asset = _load(root / "asset-metadata.json", "media-asset-metadata"); _canonical_identity(asset, "mediaasset", "asset_id")
        if report["asset_id"] != asset["asset_id"] or asset["stored_path"] != f"originals/{report['run_id']}/{payload_entries[0]['path']}":
            raise MediaIngestionError("asset metadata binding drift")
    else:
        quarantine = _load(root / "quarantine-record.json", "media-quarantine-record"); _canonical_identity(quarantine, "mediaquarantine", "quarantine_id")
        if report["quarantine_id"] != quarantine["quarantine_id"] or quarantine["quarantine_path"] != f"quarantine/{report['run_id']}/{payload_entries[0]['path']}":
            raise MediaIngestionError("quarantine metadata binding drift")
    verification: JsonObject = {
        "schema_version": "1.0", "record_type": "media_verification_report", "verification_id": "PENDING", "run_id": report["run_id"],
        "run_report_sha256": sha256_json(report), "authorization_sha256": sha256_json(authorization), "receipt_sha256": sha256_json(receipt), "verified_at": verified_at,
        "verified_inventory": report["inventory"], "checks": CHECKS, "result": "PASS", "fixture_only": True, "network_accessed": False, "approval_tier": "MACHINE_VALIDATED", "content_lifecycle_status": "UNREVIEWED",
    }
    verification["verification_id"] = identity("mediaverify", verification, "verification_id")
    validate_instance(verification, "media-verification-report")
    if require_stored:
        stored = _load(root / "verification-report.json", "media-verification-report")
        if stored != verification:
            raise MediaIngestionError("stored verification does not match independent reconstruction")
    return verification


def verify(*, run_directory: Path) -> JsonObject:
    """Read-only verification of one complete immutable controlled-media bundle."""
    stored = _load(run_directory / "verification-report.json", "media-verification-report")
    return _build_verification(run_directory, str(stored["verified_at"]), require_stored=True)
