"""Atomic immutable publication for M8.2 practice prompt pilots."""
from __future__ import annotations

import json
import os
import shutil
import uuid
from pathlib import Path
from typing import Any, Mapping, Sequence

from english_master.lesson_generation.canonical import identity, sha256_json
from english_master.lesson_generation.storage import _fsync_directory, _rename_directory_noreplace

from .authority import MODALITIES, VerifiedM6PracticeAuthority
from .verification import _is_linklike, verify_pilot

JsonObject = dict[str, Any]


def _write_json(path: Path, value: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    serialized = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False) + "\n"
    with path.open("w", encoding="utf-8", newline="\n") as handle:
        handle.write(serialized)
        handle.flush()
        os.fsync(handle.fileno())


def _name(lesson_id: str, modality: str) -> str:
    return f"{lesson_id.lower()}--{modality.lower()}.json"


def _is_within(path: Path, parent: Path) -> bool:
    """Return whether ``path`` is the same as or descends from ``parent``."""
    try:
        path.relative_to(parent)
    except ValueError:
        return False
    return True


def _validate_publication_destination(
    directory: Path,
    authority: VerifiedM6PracticeAuthority,
) -> Path:
    """Reject destinations that could add files to immutable authority evidence."""
    destination = directory.absolute()
    for ancestor in (destination, *destination.parents):
        if _is_linklike(ancestor):
            raise ValueError(f"pilot publication destination has a link-like ancestor: {ancestor}")
        if ancestor != destination and (ancestor / "batch-manifest.json").is_file():
            raise ValueError(
                "pilot publication destination is nested inside an immutable pilot: "
                f"{ancestor}"
            )

    protected_directories = (
        authority.snapshot_directory,
        authority.m6_root,
        authority.m6_batch_path.parent,
    )
    for protected in protected_directories:
        if _is_within(destination, protected):
            raise ValueError(
                "pilot publication destination is nested inside immutable authority evidence: "
                f"{protected}"
            )
    return destination


def publish_pilot(
    directory: Path,
    authority: VerifiedM6PracticeAuthority,
    authorization: Mapping[str, Any],
    entries: Sequence[tuple[Mapping[str, Any], Mapping[str, Any], Mapping[str, Any]]],
    *,
    created_at: str,
) -> Path:
    """Stage, independently reverify, then atomically publish a full pilot."""
    directory = _validate_publication_destination(directory, authority)
    if directory.exists() or _is_linklike(directory):
        raise FileExistsError(f"immutable pilot directory already exists: {directory}")
    if len(entries) != len(authority.lesson_ids) * len(MODALITIES):
        raise ValueError("pilot publication requires the complete ten-by-four artifact matrix")
    stage = directory.parent / f".{directory.name}.staging-{uuid.uuid4().hex}"
    try:
        stage.mkdir(parents=True, exist_ok=False)
        _write_json(stage / "authorization.json", authorization)
        members: list[JsonObject] = []
        seen: set[tuple[str, str]] = set()
        for request, artifact, audit in entries:
            key = (str(artifact["lesson_id"]), str(artifact["modality"]))
            if key not in {(lesson_id, modality) for lesson_id in authority.lesson_ids for modality in MODALITIES}:
                raise ValueError(f"pilot artifact is outside the trusted lesson/modality matrix: {key}")
            if key in seen:
                raise ValueError(f"duplicate pilot artifact: {key}")
            seen.add(key)
            filename = _name(*key)
            request_path = Path("requests") / filename
            prompt_path = Path("prompts") / filename
            audit_path = Path("audits") / filename
            _write_json(stage / request_path, request)
            _write_json(stage / prompt_path, artifact)
            _write_json(stage / audit_path, audit)
            members.append({
                "lesson_id": key[0], "modality": key[1],
                "request_path": request_path.as_posix(), "request_sha256": sha256_json(request),
                "prompt_path": prompt_path.as_posix(), "prompt_sha256": sha256_json(artifact),
                "audit_path": audit_path.as_posix(), "audit_sha256": sha256_json(audit),
            })
        manifest: JsonObject = {
            "schema_version": "1.0", "record_type": "ai_practice_pilot_manifest", "batch_id": "PENDING",
            "authorization_id": authorization["authorization_id"], "authorization_sha256": sha256_json(authorization),
            "m6_batch_id": authority.m6.batch["batch_id"], "m6_batch_sha256": sha256_json(authority.m6.batch),
            "created_at": created_at, "approval_tier": "MACHINE_VALIDATED", "content_lifecycle_status": "UNREVIEWED",
            "human_reviewed": False, "release_approved": False, "provider_authenticated": False,
            "members": sorted(members, key=lambda item: (item["lesson_id"], item["modality"])),
            "limitations": ["No human review, release approval, provider authentication, live provider validation, external media, external text, or Internet-wide search is claimed."],
            "inventory": [],
        }
        all_paths = sorted(path for path in stage.rglob("*.json") if path.name != "batch-manifest.json")
        manifest["inventory"] = [{"path": path.relative_to(stage).as_posix(), "sha256": sha256_json(json.loads(path.read_text(encoding="utf-8")))} for path in all_paths]
        manifest["batch_id"] = identity("aippilot", manifest, "batch_id")
        _write_json(stage / "batch-manifest.json", manifest)
        verify_pilot(stage, authority.reload())
        for child in (stage / "requests", stage / "prompts", stage / "audits", stage):
            _fsync_directory(child)
        _rename_directory_noreplace(stage, directory)
        try:
            _fsync_directory(directory.parent)
        except OSError:
            pass
        return directory
    except BaseException:
        if stage.exists() or stage.is_symlink():
            shutil.rmtree(stage, ignore_errors=True)
        raise
