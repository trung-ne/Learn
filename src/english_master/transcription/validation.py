"""Semantic validation and deterministic record construction for M13."""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path, PurePosixPath
from typing import Any, Mapping

from english_master.lesson_generation.canonical import identity, sha256_json
from english_master.schema_validation import load_source_registry, validate_instance

from .models import FIXTURE_MODEL, FIXTURE_PARAMETERS, FIXTURE_TOOL, JsonObject, TranscriptionError
from .safety import sha256_bytes


def parse_time(value: str, label: str) -> datetime:
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as error:
        raise TranscriptionError(f"invalid {label}: {value}") from error
    if parsed.tzinfo is None:
        raise TranscriptionError(f"{label} must have an explicit UTC offset")
    return parsed.astimezone(timezone.utc)


def require_canonical(value: Mapping[str, Any], prefix: str, field: str) -> None:
    if value.get(field) != identity(prefix, value, field):
        raise TranscriptionError(f"{field} does not reconstruct canonically")


def _registered_source(registry: Mapping[str, Any], source_id: str) -> Mapping[str, Any]:
    matches = [item for item in registry.get("sources", []) if isinstance(item, Mapping) and item.get("source_id") == source_id]
    if len(matches) != 1:
        raise TranscriptionError("transcription source is not uniquely registered")
    source = matches[0]
    if source.get("status") != "APPROVED":
        raise TranscriptionError("transcription source is not APPROVED")
    return source


def _safe_snapshot_path(value: str) -> PurePosixPath:
    path = PurePosixPath(value)
    if path.is_absolute() or not path.parts or ".." in path.parts or "\\" in value:
        raise TranscriptionError("unsafe parent permission-evidence snapshot path")
    return path


def _located_bytes(content: bytes, locator: Mapping[str, Any]) -> bytes:
    if locator.get("kind") == "JSON_POINTER":
        try:
            value: Any = json.loads(content.decode("utf-8"))
            pointer = str(locator["pointer"])
            if pointer:
                if not pointer.startswith("/"):
                    raise ValueError("JSON pointer must be empty or absolute")
                for encoded in pointer[1:].split("/"):
                    token = encoded.replace("~1", "/").replace("~0", "~")
                    value = value[int(token)] if isinstance(value, list) else value[token]
            return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False).encode("utf-8")
        except (UnicodeError, json.JSONDecodeError, KeyError, IndexError, ValueError, TypeError) as error:
            raise TranscriptionError(f"permission-evidence JSON locator does not resolve: {error}") from error
    try:
        lines = content.decode("utf-8").splitlines()
        start, end = int(locator["start_line"]), int(locator["end_line"])
    except (UnicodeError, KeyError, ValueError, TypeError) as error:
        raise TranscriptionError("permission-evidence text locator is malformed") from error
    if start < 1 or end < start or end > len(lines):
        raise TranscriptionError("permission-evidence text locator is outside its snapshot")
    return "\n".join(lines[start - 1:end]).encode("utf-8")


def _record_permission_bindings(
    authorization: Mapping[str, Any],
    parent_authorization: Mapping[str, Any],
    parent_assessment: Mapping[str, Any],
    evidence_root: Path,
    *,
    use_retained_paths: bool = False,
) -> None:
    parent_entries = {str(item["operation"]): item for item in parent_authorization.get("permission_evidence", [])}
    assessment_entries = {str(item["operation"]): item for item in parent_assessment.get("operation_results", [])}
    required = (("transcript_generation", "can_generate_transcript"), ("timestamp_generation", "can_generate_timestamps"))
    supplied = authorization.get("permission_evidence")
    if not isinstance(supplied, list) or [item.get("operation") for item in supplied if isinstance(item, Mapping)] != [item[0] for item in required]:
        raise TranscriptionError("record-level permission evidence must contain transcript then timestamp evidence exactly")
    for supplied_entry, (operation, parent_key) in zip(supplied, required, strict=True):
        parent_entry = parent_entries.get(parent_key)
        assessment_entry = assessment_entries.get(parent_key)
        if parent_entry is None or assessment_entry is None:
            raise TranscriptionError(f"parent M12 v2 lacks record-level {operation} evidence")
        retained_path = f"evidence-{'transcript' if operation == 'transcript_generation' else 'timestamp'}.snapshot"
        expected = {
            "operation": operation,
            "parent_permission_key": parent_key,
            "parent_permission_evidence_sha256": sha256_json(parent_entry),
            "snapshot_path": parent_entry["snapshot_path"],
            "snapshot_sha256": parent_entry["snapshot_sha256"],
            "snapshot_bytes": parent_entry["snapshot_bytes"],
            "locator": parent_entry["locator"],
            "located_value_sha256": parent_entry["located_value_sha256"],
            "parent_assessment_result_sha256": sha256_json(assessment_entry),
            "retained_snapshot_path": retained_path,
        }
        if supplied_entry != expected:
            raise TranscriptionError(f"record-level {operation} evidence binding drift")
        if assessment_entry.get("deterministic_result") != "CONSISTENT" or assessment_entry.get("result") != "CONSISTENT":
            raise TranscriptionError(f"record-level {operation} evidence is not CONSISTENT")
        snapshot_relative = str(supplied_entry["retained_snapshot_path"]) if use_retained_paths else str(parent_entry["snapshot_path"])
        snapshot = evidence_root.joinpath(*_safe_snapshot_path(snapshot_relative).parts)
        try:
            content = snapshot.read_bytes()
        except OSError as error:
            raise TranscriptionError(f"record-level {operation} evidence snapshot is unavailable") from error
        if len(content) != parent_entry["snapshot_bytes"] or sha256_bytes(content) != parent_entry["snapshot_sha256"]:
            raise TranscriptionError(f"record-level {operation} evidence snapshot drift")
        if sha256_bytes(_located_bytes(content, parent_entry["locator"])) != parent_entry["located_value_sha256"]:
            raise TranscriptionError(f"record-level {operation} located evidence drift")


def validate_authority(
    authorization: Mapping[str, Any],
    *,
    registry_path: Path,
    parent_authorization: Mapping[str, Any],
    parent_receipt: Mapping[str, Any],
    parent_report: Mapping[str, Any],
    parent_asset: Mapping[str, Any],
    parent_verification: Mapping[str, Any],
    parent_assessment: Mapping[str, Any] | None,
    media_schema_version: str,
    evidence_root: Path | None = None,
    use_retained_evidence_paths: bool = False,
    allow_legacy_parent: bool = False,
) -> Mapping[str, Any]:
    """Validate exact M12 bindings and explicit transcript/timestamp permissions."""
    require_canonical(authorization, "transauth", "authorization_id")
    require_canonical(parent_authorization, "mediaauth", "authorization_id")
    require_canonical(parent_receipt, "mediareceipt", "receipt_id")
    require_canonical(parent_asset, "mediaasset", "asset_id")
    require_canonical(parent_verification, "mediaverify", "verification_id")
    if parent_assessment is not None:
        require_canonical(parent_assessment, "mediaevidenceassessment", "assessment_id")
    if media_schema_version not in {"1.0", "2.0"}:
        raise TranscriptionError("unsupported parent M12 schema version")
    hardened = authorization.get("schema_version") == "2.0"
    if hardened and media_schema_version != "2.0":
        raise TranscriptionError("new M13 derivatives require a verified M12 v2 parent; M12 v1 is verification-only")
    if not hardened and not allow_legacy_parent:
        raise TranscriptionError("M13 v1 authorization is verification-only")
    if authorization.get("authorization_mode") != "OFFLINE_TEST_FIXTURE_ONLY" or authorization.get("fixture_only") is not True:
        raise TranscriptionError("only offline test-fixture transcription authorization is accepted")
    registry_bytes = registry_path.read_bytes()
    if authorization["registry_sha256"] != sha256_bytes(registry_bytes):
        raise TranscriptionError("source registry hash drift")
    registry = load_source_registry(registry_path)
    source = _registered_source(registry, str(authorization["source_id"]))
    kind = str(authorization["media_kind"])
    media_permissions = source.get("media_permissions", {}).get(kind.lower(), {})
    if media_permissions.get("transcript_allowed") is not True:
        raise TranscriptionError("source registry does not explicitly permit transcript generation")
    if media_permissions.get("timestamp_allowed") is not True:
        raise TranscriptionError("source registry does not explicitly permit timestamp generation")
    if authorization.get("permissions") != {"transcript_generation": True, "timestamp_generation": True}:
        raise TranscriptionError("authorization must explicitly permit transcript and timestamp generation")
    if parent_report.get("outcome") != "STORED" or parent_report.get("fixture_only") is not True:
        raise TranscriptionError("parent M12 run is not a stored fixture run")
    if parent_authorization.get("fixture_only") is not True or parent_authorization.get("authorization_mode") != "OFFLINE_TEST_FIXTURE_ONLY":
        raise TranscriptionError("parent M12 authorization is outside the fixture boundary")
    if parent_authorization.get("permissions", {}).get("can_generate_transcript") is not True:
        raise TranscriptionError("parent M12 authorization does not permit transcript generation")
    if media_schema_version == "2.0":
        if parent_authorization.get("permissions", {}).get("can_generate_timestamps") is not True:
            raise TranscriptionError("parent M12 v2 authorization does not permit timestamp generation")
        if parent_assessment is None:
            raise TranscriptionError("parent M12 v2 evidence assessment is required")
    elif parent_assessment is not None:
        raise TranscriptionError("parent M12 v1 cannot bind a v2 evidence assessment")
    expected = {
        "media_schema_version": media_schema_version,
        "media_run_id": parent_report.get("run_id"),
        "media_run_report_sha256": sha256_json(parent_report),
        "media_acquisition_receipt_id": parent_receipt.get("receipt_id"),
        "media_acquisition_receipt_sha256": sha256_json(parent_receipt),
        "media_verification_id": parent_verification.get("verification_id"),
        "media_verification_sha256": sha256_json(parent_verification),
        "media_evidence_assessment_id": parent_assessment.get("assessment_id") if parent_assessment is not None else None,
        "media_evidence_assessment_sha256": sha256_json(parent_assessment) if parent_assessment is not None else None,
        "media_asset_id": parent_asset.get("asset_id"),
        "media_asset_sha256": sha256_json(parent_asset),
        "media_payload_sha256": parent_asset.get("payload_sha256"),
        "source_id": parent_asset.get("source_id"),
        "source_record_id": parent_asset.get("source_record_id"),
        "media_kind": parent_asset.get("media_kind"),
        "media_duration_ms": parent_asset.get("metadata", {}).get("duration_ms"),
    }
    if any(authorization.get(key) != expected_value for key, expected_value in expected.items()):
        raise TranscriptionError("transcription authorization differs from the exact parent M12 asset")
    if parent_report.get("asset_id") != parent_asset.get("asset_id"):
        raise TranscriptionError("parent M12 run and asset identity differ")
    if parent_report.get("authorization_id") != parent_authorization.get("authorization_id") or parent_report.get("authorization_sha256") != sha256_json(parent_authorization):
        raise TranscriptionError("parent M12 authorization binding drift")
    if parent_report.get("receipt_id") != parent_receipt.get("receipt_id") or parent_report.get("receipt_sha256") != sha256_json(parent_receipt):
        raise TranscriptionError("parent M12 acquisition receipt binding drift")
    if parent_verification.get("result") != "PASS" or parent_verification.get("run_id") != parent_report.get("run_id") or parent_verification.get("run_report_sha256") != sha256_json(parent_report):
        raise TranscriptionError("parent M12 verification binding drift")
    if parent_verification.get("receipt_sha256") != sha256_json(parent_receipt) or parent_verification.get("authorization_sha256") != sha256_json(parent_authorization):
        raise TranscriptionError("parent M12 verification authority drift")
    if media_schema_version == "2.0":
        assert parent_assessment is not None
        if parent_report.get("assessment_id") != parent_assessment.get("assessment_id") or parent_report.get("assessment_sha256") != sha256_json(parent_assessment):
            raise TranscriptionError("parent M12 evidence assessment binding drift")
        if parent_verification.get("assessment_sha256") != sha256_json(parent_assessment):
            raise TranscriptionError("parent M12 verification assessment drift")
        if parent_assessment.get("overall_result") != "CONSISTENT" or parent_assessment.get("rights_granted") is not False:
            raise TranscriptionError("parent M12 evidence assessment is not a consistent non-rights-granting assessment")
        if hardened:
            if evidence_root is None:
                raise TranscriptionError("record-level permission evidence root is required")
            _record_permission_bindings(
                authorization, parent_authorization, parent_assessment, evidence_root,
                use_retained_paths=use_retained_evidence_paths,
            )
    if parent_asset.get("authorization_id") != parent_authorization.get("authorization_id") or parent_asset.get("authorization_sha256") != sha256_json(parent_authorization):
        raise TranscriptionError("parent M12 asset authorization binding drift")
    if parent_authorization.get("registry_sha256") != authorization.get("registry_sha256"):
        raise TranscriptionError("parent M12 and transcription registry bindings differ")
    if parent_authorization.get("source_id") != source.get("source_id") or parent_authorization.get("media_kind") != kind:
        raise TranscriptionError("parent M12 source projection differs from the registry authority")
    authorized_at = parse_time(str(authorization["authorized_at"]), "authorized_at")
    expires_at = parse_time(str(authorization["expires_at"]), "expires_at")
    parent_completed = parse_time(str(parent_report["completed_at"]), "parent completed_at")
    if authorized_at < parent_completed or authorized_at >= expires_at:
        raise TranscriptionError("transcription authorization chronology is invalid")
    return source


def validate_request(authorization: Mapping[str, Any], request: Mapping[str, Any]) -> None:
    require_canonical(request, "transreq", "request_id")
    expected = {
        "authorization_id": authorization.get("authorization_id"),
        "authorization_sha256": sha256_json(authorization),
        "media_run_id": authorization.get("media_run_id"),
        "media_asset_id": authorization.get("media_asset_id"),
        "media_payload_sha256": authorization.get("media_payload_sha256"),
    }
    if any(request.get(key) != expected_value for key, expected_value in expected.items()):
        raise TranscriptionError("transcription request authority binding drift")
    if request.get("fixture_segments_sha256") != sha256_json(request.get("fixture_segments")):
        raise TranscriptionError("fixture segment hash drift")
    if request.get("schema_version") == "2.0":
        expected_constraints = {
            "read_parent_media": False,
            "decode_media": False,
            "extract_audio": False,
            "transform_media": False,
            "invoke_external_process": False,
            "access_network": False,
        }
        if request.get("processing_constraints") != expected_constraints:
            raise TranscriptionError("fixture processing constraints must prohibit media access and transformation")
    requested_at = parse_time(str(request["requested_at"]), "requested_at")
    if not (parse_time(str(authorization["authorized_at"]), "authorized_at") <= requested_at <= parse_time(str(authorization["expires_at"]), "expires_at")):
        raise TranscriptionError("request is outside the authorization interval")
    validate_segments(request["fixture_segments"], int(authorization["media_duration_ms"]))


def validate_segments(segments: Any, duration_ms: int) -> None:
    if not isinstance(segments, list) or not segments:
        raise TranscriptionError("at least one fixture segment is required")
    prior_end = 0
    labels: list[str] = []
    for index, segment in enumerate(segments, start=1):
        if not isinstance(segment, Mapping):
            raise TranscriptionError("every fixture segment must be an object")
        if segment.get("sequence") != index:
            raise TranscriptionError("segment sequence must be contiguous and one-based")
        start, end = segment.get("start_ms"), segment.get("end_ms")
        if not isinstance(start, int) or isinstance(start, bool) or not isinstance(end, int) or isinstance(end, bool):
            raise TranscriptionError("segment timestamps must be integers")
        if start < prior_end or start >= end or end > duration_ms:
            raise TranscriptionError("segment timestamps must be ordered, non-overlapping, and within media duration")
        text = segment.get("text")
        if not isinstance(text, str) or not text or text != text.strip():
            raise TranscriptionError("segment text must be nonempty and have no edge whitespace")
        label = segment.get("speaker_label")
        if label not in labels:
            expected = f"SPEAKER_{len(labels) + 1:02d}"
            if label != expected:
                raise TranscriptionError("speaker labels must be anonymized and sequential by first appearance")
            labels.append(str(label))
        prior_end = end


def build_processing_plan(authorization: Mapping[str, Any], request: Mapping[str, Any], planned_at: str) -> JsonObject:
    """Build the executable fixture contract; this plan has no media input operation."""
    plan: JsonObject = {
        "schema_version": "2.0",
        "record_type": "transcription_processing_plan",
        "plan_id": "PENDING",
        "authorization_id": authorization["authorization_id"],
        "authorization_sha256": sha256_json(authorization),
        "request_id": request["request_id"],
        "request_sha256": sha256_json(request),
        "planned_at": planned_at,
        "processing_mode": "INLINE_FIXTURE_COPY_NO_MEDIA_ACCESS",
        "input_kind": "CALLER_AUTHORED_INLINE_SEGMENTS",
        "operations": {
            "read_parent_media": False,
            "decode_media": False,
            "extract_audio": False,
            "transform_media": False,
            "invoke_external_process": False,
            "access_network": False,
        },
        "tool": dict(FIXTURE_TOOL),
        "model": dict(FIXTURE_MODEL),
        "parameters": dict(FIXTURE_PARAMETERS),
        "fixture_segments_sha256": request["fixture_segments_sha256"],
        "fixture_only": True,
    }
    plan["plan_id"] = identity("transplan", plan, "plan_id")
    validate_instance(plan, "transcription-processing-plan-v2")
    return plan


def validate_processing_plan(
    authorization: Mapping[str, Any], request: Mapping[str, Any], plan: Mapping[str, Any]
) -> None:
    require_canonical(plan, "transplan", "plan_id")
    expected = build_processing_plan(authorization, request, str(plan["planned_at"]))
    if plan != expected:
        raise TranscriptionError("processing plan differs from the deterministic no-media/no-transform fixture plan")


def build_artifact(
    authorization: Mapping[str, Any], request: Mapping[str, Any], generated_at: str,
    plan: Mapping[str, Any] | None = None,
) -> JsonObject:
    segments = [
        {
            "segment_id": f"segment_{index:04d}",
            "sequence": item["sequence"],
            "start_ms": item["start_ms"],
            "end_ms": item["end_ms"],
            "speaker_label": item["speaker_label"],
            "text": item["text"],
        }
        for index, item in enumerate(request["fixture_segments"], start=1)
    ]
    labels = list(dict.fromkeys(item["speaker_label"] for item in segments))
    full_text = " ".join(item["text"] for item in segments)
    hardened = authorization.get("schema_version") == "2.0"
    if hardened and plan is None:
        raise TranscriptionError("hardened artifact requires a processing plan")
    artifact: JsonObject = {
        "schema_version": "2.0" if hardened else "1.0",
        "record_type": "transcript_artifact",
        "artifact_id": "PENDING",
        "authorization_id": authorization["authorization_id"],
        "authorization_sha256": sha256_json(authorization),
        "request_id": request["request_id"],
        "request_sha256": sha256_json(request),
        "media_run_id": authorization["media_run_id"],
        "media_asset_id": authorization["media_asset_id"],
        "media_payload_sha256": authorization["media_payload_sha256"],
        "source_id": authorization["source_id"],
        "source_record_id": authorization["source_record_id"],
        "language": request["language"],
        "media_duration_ms": authorization["media_duration_ms"],
        "segments": segments,
        "speaker_labels": labels,
        "full_text": full_text,
        "full_text_sha256": sha256_bytes(full_text.encode("utf-8")),
        "generated_at": generated_at,
        "generation_method": "LOCAL_DETERMINISTIC_FIXTURE_COPY",
        "permissions_validated": {"transcript_generation": True, "timestamp_generation": True},
        "fixture_only": True,
        "network_accessed": False,
        "provider_invoked": False,
        "model_invoked": False,
        "content_lifecycle_status": "UNREVIEWED",
        "approval_tier": "MACHINE_VALIDATED",
        "redistribution_authorized": False,
    }
    if hardened:
        assert plan is not None
        artifact.update({
            "processing_plan_id": plan["plan_id"],
            "processing_plan_sha256": sha256_json(plan),
            "tool": plan["tool"],
            "model": plan["model"],
            "parameters": plan["parameters"],
            "parent_media_read": False,
            "media_transformed": False,
            "audio_extracted": False,
            "external_process_invoked": False,
        })
    artifact["artifact_id"] = identity("transcript", artifact, "artifact_id")
    validate_instance(artifact, "transcript-artifact-v2" if hardened else "transcript-artifact")
    return artifact


def validate_artifact(
    authorization: Mapping[str, Any], request: Mapping[str, Any], artifact: Mapping[str, Any],
    plan: Mapping[str, Any] | None = None,
) -> None:
    require_canonical(artifact, "transcript", "artifact_id")
    validate_segments(artifact.get("segments"), int(authorization["media_duration_ms"]))
    expected = build_artifact(authorization, request, str(artifact["generated_at"]), plan)
    if artifact != expected:
        raise TranscriptionError("transcript artifact differs from deterministic fixture construction")
