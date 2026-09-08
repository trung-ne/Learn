"""Atomic no-overwrite construction of complete M11 export directories."""
from __future__ import annotations

import json
import os
import shutil
import tempfile
from pathlib import Path
from typing import Any

from english_master.lesson_generation.storage import _fsync_directory, _rename_directory_noreplace
from english_master.schema_validation import validate_instance

from .authority import assess_authorization
from .canonical import identity, sha256_file
from .models import build_export_model
from .renderers import RENDERERS
from .verification import build_verification


STATIC_LIMITATIONS = [
    "AI-practice exports are stored protocols, not evidence of live provider behavior.",
    "Static mobile and web files provide no runtime, telemetry, authentication, or media download.",
    "Print HTML is not PDF and separate instructor files are not access control.",
    "The LMS archive contains ungraded web-content only; no QTI, SCORM, or gradebook is claimed.",
    "No target-LMS or IMS certification is claimed.",
]


def _write_json(path: Path, value: dict[str, Any]) -> None:
    with path.open("x", encoding="utf-8", newline="\n") as stream:
        json.dump(value, stream, ensure_ascii=False, sort_keys=True, indent=2, allow_nan=False)
        stream.write("\n")
        stream.flush()
        os.fsync(stream.fileno())


def _format_for(path: str) -> str:
    if path == "authorization.json": return "CONTROL"
    prefix = path.split("/", 1)[0]
    return {"json": "JSON", "csv": "CSV", "mobile": "STATIC_MOBILE", "web": "STATIC_WEB", "print": "PRINT_HTML", "lms": "IMS_COMMON_CARTRIDGE_1_3"}[prefix]


def build_export(authorization_path: Path, repository_root: Path, output_root: Path, *, exported_at: str) -> Path:
    """Verify authority first, then atomically publish one immutable bundle."""

    eligible = assess_authorization(authorization_path.resolve(), repository_root.resolve())
    model = build_export_model(eligible.authorization, eligible.artifacts, exported_at=exported_at)
    output_root.mkdir(parents=True, exist_ok=True)
    staging = Path(tempfile.mkdtemp(prefix=".m11-export-", dir=output_root))
    try:
        shutil.copyfile(eligible.authorization_path, staging / "authorization.json")
        emitted: list[Path] = [staging / "authorization.json"]
        for format_name in model.formats:
            emitted.extend(RENDERERS[format_name](staging, model))
        inventory = []
        for path in sorted(emitted, key=lambda item: item.relative_to(staging).as_posix()):
            relative = path.relative_to(staging).as_posix()
            inventory.append({"path": relative, "format": _format_for(relative), "bytes": path.stat().st_size, "sha256": sha256_file(path)})
        manifest: dict[str, Any] = {
            "schema_version": "1.0",
            "record_type": "m11_export_manifest",
            "export_id": "PENDING",
            "package_version": model.package_version,
            "exported_at": model.exported_at,
            "authorization_id": eligible.authorization["authorization_id"],
            "authorization_sha256": sha256_file(staging / "authorization.json"),
            "formats": list(model.formats),
            "answer_materials": model.answer_materials,
            "renderer_profiles": {"model": "M11_NORMALIZED_MODEL_v1", "json": "M11_CANONICAL_JSON_v1", "csv": "M11_RFC4180_CSV_v1", "static": "M11_STATIC_HTML_v1", "print": "M11_PRINT_HTML_v1", "common_cartridge": "M11_IMS_CC_1_3_UNGRADED_WEBCONTENT_v1"},
            "content_counts": {"lessons": len(model.lessons), "exercise_sets": len(model.exercise_sets), "ai_practice_prompts": len(model.prompts)},
            "files": inventory,
            "static_limitations": STATIC_LIMITATIONS,
            "approval_tier": "DEVELOPMENT_APPROVED",
            "tatoeba_pilot_included": False,
        }
        manifest["export_id"] = identity("m11export", manifest, "export_id")
        validate_instance(manifest, "m11-export-manifest")
        _write_json(staging / "manifest.json", manifest)
        receipt = build_verification(staging, repository_root.resolve(), require_receipt=False)
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
