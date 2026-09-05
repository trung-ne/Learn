"""Independent reconstruction and tamper detection for M8.2 pilots."""
from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping

from english_master.curriculum_review.loading import load_strict_document
from english_master.lesson_generation.canonical import sha256_json
from english_master.schema_validation import validate_instance
from english_master.qa_engine.time import ensure_not_after, orderable_timestamp

from .authority import MODALITIES, VerifiedM6PracticeAuthority

JsonObject = dict[str, Any]


def _load_validated(path: Path, schema_name: str) -> JsonObject:
    value = load_strict_document(path)
    validate_instance(value, schema_name)
    return value


def _is_linklike(path: Path) -> bool:
    """Treat Windows junctions as links as well as POSIX/Windows symlinks."""
    return path.is_symlink() or getattr(path, "is_junction", lambda: False)()


def _require_path(root: Path, relative: str) -> Path:
    candidate = root / relative
    if _is_linklike(candidate) or not candidate.is_file():
        raise ValueError(f"pilot member must be a regular file: {relative}")
    resolved = candidate.resolve()
    if root not in resolved.parents:
        raise ValueError(f"pilot member escapes root: {relative}")
    return resolved


def _expected_paths(authority: VerifiedM6PracticeAuthority) -> set[str]:
    paths = {"authorization.json", "batch-manifest.json"}
    for lesson_id in authority.lesson_ids:
        for modality in MODALITIES:
            filename = f"{lesson_id.lower()}--{modality.lower()}.json"
            paths.update({f"requests/{filename}", f"prompts/{filename}", f"audits/{filename}"})
    return paths


def verify_pilot(directory: Path, authority: VerifiedM6PracticeAuthority) -> JsonObject:
    """Rebuild all authority-derived records; never trust stored PASS assertions."""
    if _is_linklike(directory) or not directory.is_dir():
        raise ValueError("pilot directory must be a real directory, not a symlink")
    root = directory.resolve()
    verified_at = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
    expected = _expected_paths(authority)
    actual_paths: set[str] = set()
    allowed_directories = {"requests", "prompts", "audits"}
    for path in root.rglob("*"):
        relative = path.relative_to(root).as_posix()
        if _is_linklike(path):
            raise ValueError(f"pilot directory contains a symlink: {relative}")
        if path.is_dir():
            if relative not in allowed_directories:
                raise ValueError(f"pilot directory contains an unexpected directory: {relative}")
            continue
        if not path.is_file() or relative not in expected:
            raise ValueError(f"pilot directory contains an unexpected path: {relative}")
        actual_paths.add(relative)
        if len(actual_paths) > len(expected):
            raise ValueError("pilot directory exceeds the fixed inventory limit")
    if actual_paths != expected:
        raise ValueError("pilot inventory does not match the required complete matrix")
    authorization = _load_validated(_require_path(root, "authorization.json"), "ai-practice-authorization")
    expected_authorization = authority.authorization(
        created_at=authorization.get("created_at"), prompt_version=authorization.get("prompt_version")
    )
    if authorization != expected_authorization:
        raise ValueError("authorization is not reconstructable from trusted M6 authority")
    ensure_not_after(authority.m6.batch["created_at"], authorization["created_at"], "M8.2 authorization predates M6 batch authority")
    ensure_not_after(authorization["created_at"], verified_at, "M8.2 authorization is future-dated")
    manifest = _load_validated(_require_path(root, "batch-manifest.json"), "ai-practice-pilot-manifest")
    required_manifest = {
        "schema_version", "record_type", "batch_id", "authorization_id", "authorization_sha256", "m6_batch_id", "m6_batch_sha256",
        "created_at", "approval_tier", "content_lifecycle_status", "human_reviewed", "release_approved", "provider_authenticated", "members", "limitations", "inventory",
    }
    if set(manifest) != required_manifest:
        raise ValueError("pilot manifest has an invalid field inventory")
    if manifest["record_type"] != "ai_practice_pilot_manifest" or manifest["schema_version"] != "1.0":
        raise ValueError("pilot manifest identity is invalid")
    if (manifest["authorization_id"], manifest["authorization_sha256"]) != (authorization["authorization_id"], sha256_json(authorization)):
        raise ValueError("pilot manifest authorization binding drift")
    if (manifest["m6_batch_id"], manifest["m6_batch_sha256"]) != (authority.m6.batch["batch_id"], sha256_json(authority.m6.batch)):
        raise ValueError("pilot manifest M6 binding drift")
    if manifest["created_at"] != authorization["created_at"]:
        raise ValueError("pilot manifest timestamp must equal authorization timestamp")
    orderable_timestamp(manifest["created_at"])
    if manifest["approval_tier"] != "MACHINE_VALIDATED" or manifest["content_lifecycle_status"] != "UNREVIEWED" or manifest["human_reviewed"] or manifest["release_approved"] or manifest["provider_authenticated"]:
        raise ValueError("pilot manifest makes a prohibited approval claim")
    expected_limitations = ["No human review, release approval, provider authentication, live provider validation, external media, external text, or Internet-wide search is claimed."]
    if manifest["limitations"] != expected_limitations:
        raise ValueError("pilot manifest limitations differ from the fixed M8.2 claim boundary")
    expected_batch = dict(manifest)
    expected_batch["batch_id"] = "PENDING"
    from english_master.lesson_generation.canonical import identity
    if manifest["batch_id"] != identity("aippilot", expected_batch, "batch_id"):
        raise ValueError("pilot manifest identity is not canonical")

    from .generation import audit_artifact, build_artifact
    members = manifest["members"]
    if members != sorted(members, key=lambda item: (item.get("lesson_id", ""), item.get("modality", ""))):
        raise ValueError("pilot manifest members are not in canonical order")
    if not isinstance(members, list) or len(members) != 40:
        raise ValueError("pilot manifest must bind exactly forty members")
    seen: set[tuple[str, str]] = set()
    inventory_paths: set[str] = {"authorization.json"}
    for member in members:
        if not isinstance(member, Mapping):
            raise ValueError("pilot member is not an object")
        lesson_id, modality = member.get("lesson_id"), member.get("modality")
        if lesson_id not in authority.lesson_ids or modality not in MODALITIES:
            raise ValueError("pilot member has untrusted lesson or modality")
        key = (lesson_id, modality)
        if key in seen:
            raise ValueError("pilot manifest contains duplicate lesson/modality member")
        seen.add(key)
        filenames = f"{lesson_id.lower()}--{modality.lower()}.json"
        expected_member_paths = (f"requests/{filenames}", f"prompts/{filenames}", f"audits/{filenames}")
        if tuple(member.get(key) for key in ("request_path", "prompt_path", "audit_path")) != expected_member_paths:
            raise ValueError("pilot member path is noncanonical")
        request = _load_validated(_require_path(root, expected_member_paths[0]), "ai-practice-request")
        expected_request = authority.request(lesson_id, modality, authorization)
        if request != expected_request or member.get("request_sha256") != sha256_json(request):
            raise ValueError("pilot request scope or hash is not reconstructable")
        artifact = _load_validated(_require_path(root, expected_member_paths[1]), "ai-practice-prompt-artifact")
        if artifact["provenance"]["generated_at"] != authorization["created_at"]:
            raise ValueError("artifact generation timestamp must equal authorization timestamp")
        expected_artifact = build_artifact(authority, authorization, request, generated_at=artifact["provenance"]["generated_at"])
        if artifact != expected_artifact or member.get("prompt_sha256") != sha256_json(artifact):
            raise ValueError("pilot prompt artifact is not reconstructable")
        audit = _load_validated(_require_path(root, expected_member_paths[2]), "ai-practice-audit")
        expected_audit = audit_artifact(artifact, authority=authority, request=request, authorization=authorization, audited_at=authorization["created_at"])
        if audit["qa_timestamp"] != authorization["created_at"] or audit != expected_audit or audit.get("result") != "PASS" or member.get("audit_sha256") != sha256_json(audit):
            raise ValueError("pilot audit is stale, failed, or not reconstructable")
        inventory_paths.update(expected_member_paths)
    required_keys = {(lesson_id, modality) for lesson_id in authority.lesson_ids for modality in MODALITIES}
    if seen != required_keys:
        raise ValueError("pilot does not contain the complete lesson/modality matrix")
    inventory = manifest["inventory"]
    if not isinstance(inventory, list) or len(inventory) != len(inventory_paths):
        raise ValueError("pilot manifest inventory is incomplete")
    actual_inventory = []
    for relative in sorted(inventory_paths):
        document = load_strict_document(_require_path(root, relative))
        actual_inventory.append({"path": relative, "sha256": sha256_json(document)})
    if inventory != actual_inventory:
        raise ValueError("pilot manifest file inventory hash drift")
    return {
        "batch_id": manifest["batch_id"], "artifact_count": len(seen), "lesson_count": len(authority.lesson_ids),
        "approval_tier": "MACHINE_VALIDATED", "content_lifecycle_status": "UNREVIEWED",
        "human_reviewed": False, "release_approved": False, "provider_authenticated": False,
    }
