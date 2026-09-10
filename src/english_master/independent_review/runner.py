"""Provider-neutral, fail-closed M9 AI capture automation."""
from __future__ import annotations

import json
import os
import shlex
import shutil
import subprocess
import tempfile
from collections.abc import Callable, Mapping, Sequence
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from english_master.curriculum_review.loading import load_strict_document
from english_master.lesson_generation.canonical import canonical_json, identity, sha256_json, sha256_text
from english_master.schema_validation import validate_instance

from .authority import VerifiedM9Authority
from .machine import build_machine_report
from .review import CHECKLISTS, build_review_prompt, parse_orderable_timestamp

JsonObject = dict[str, Any]
RunnerInvoker = Callable[[Sequence[str], Mapping[str, Any], float], Mapping[str, Any]]
EXPECTED_OPERATION_COUNT = 120
MAX_STDOUT_BYTES = 2_000_000


class RunnerOperationalError(RuntimeError):
    """An external runner operation failed without creating capture evidence."""


def _now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def parse_runner_command(value: str | None) -> tuple[str, ...]:
    """Parse the configured command into argv without invoking a shell."""
    if value is None or not value.strip():
        raise RunnerOperationalError("ENGLISH_MASTER_M9_AI_RUNNER is not configured")
    try:
        parts = shlex.split(value, posix=os.name != "nt")
    except ValueError as error:
        raise RunnerOperationalError(f"invalid ENGLISH_MASTER_M9_AI_RUNNER command: {error}") from error
    if os.name == "nt":
        parts = [part[1:-1] if len(part) >= 2 and part[0] == part[-1] == '"' else part for part in parts]
    if not parts or not parts[0]:
        raise RunnerOperationalError("ENGLISH_MASTER_M9_AI_RUNNER has no executable")
    return tuple(parts)


def _unique_object(pairs: list[tuple[str, Any]]) -> JsonObject:
    result: JsonObject = {}
    for key, value in pairs:
        if key in result:
            raise RunnerOperationalError(f"runner stdout contains duplicate JSON key {key!r}")
        result[key] = value
    return result


def invoke_external_runner(argv: Sequence[str], request: Mapping[str, Any], timeout_seconds: float) -> Mapping[str, Any]:
    """Send one canonical request and accept exactly one canonical JSON response."""
    if timeout_seconds <= 0:
        raise RunnerOperationalError("runner timeout must be positive")
    payload = (canonical_json(request) + "\n").encode("utf-8")
    try:
        completed = subprocess.run(
            list(argv), input=payload, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
            shell=False, check=False, timeout=timeout_seconds,
        )
    except (OSError, subprocess.TimeoutExpired) as error:
        raise RunnerOperationalError(f"runner execution failed: {error}") from error
    if completed.returncode != 0:
        stderr = completed.stderr.decode("utf-8", errors="backslashreplace").strip()
        detail = stderr[:1000] if stderr else "no stderr"
        raise RunnerOperationalError(f"runner exited {completed.returncode}: {detail}")
    if len(completed.stdout) > MAX_STDOUT_BYTES:
        raise RunnerOperationalError("runner stdout exceeds the 2000000-byte limit")
    try:
        text = completed.stdout.decode("utf-8")
        response = json.loads(text, object_pairs_hook=_unique_object)
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        raise RunnerOperationalError(f"runner stdout is not one UTF-8 JSON document: {error}") from error
    if not isinstance(response, dict):
        raise RunnerOperationalError("runner stdout JSON must be an object")
    # Canonical output prevents unnoticed alternate encodings or multiple JSON values.
    if text != canonical_json(response) + "\n":
        raise RunnerOperationalError("runner stdout must be canonical JSON followed by one newline")
    validate_instance(response, "m9-ai-runner-response")
    if response["request_id"] != request["request_id"]:
        raise RunnerOperationalError("runner response request_id does not match the request")
    return response


def _load_config(path: Path | None) -> JsonObject | None:
    if path is None:
        return None
    return load_strict_document(path)


def _resolved_executable(argv: Sequence[str]) -> str:
    resolved = shutil.which(argv[0])
    if resolved is not None:
        return str(Path(resolved).resolve())
    return str(Path(argv[0]).resolve())


def build_runner_request(
    *, selection: Mapping[str, Any], subject_id: str, content_type: str, role: str,
    prompt: str, config: Mapping[str, Any] | None, operation_index: int,
) -> JsonObject:
    """Construct one canonical, hash-bound runner request."""
    request: JsonObject = {
        "schema_version": "1.0", "record_type": "m9_ai_runner_request", "request_id": "PENDING",
        "operation_index": operation_index, "operation_count": EXPECTED_OPERATION_COUNT,
        "selection_id": selection["selection_id"], "subject_id": subject_id, "content_type": content_type,
        "review_role": role, "checklist": list(CHECKLISTS[role]), "prompt": prompt,
        "prompt_sha256": sha256_text(prompt), "config": dict(config) if config is not None else None,
        "config_sha256": sha256_json(config),
    }
    request["request_id"] = identity("m9airunreq", request, "request_id")
    validate_instance(request, "m9-ai-runner-request")
    return request


def capture_development(
    *, authority: VerifiedM9Authority, prepared_directory: Path, output_directory: Path,
    runner_command: str | None = None, config_path: Path | None = None,
    timeout_seconds: float = 600.0, invoke: RunnerInvoker = invoke_external_runner,
) -> Path:
    """Atomically publish captures only after all 120 runner operations succeed."""
    if output_directory.exists():
        raise FileExistsError(f"M9 capture directory already exists: {output_directory}")
    argv = parse_runner_command(runner_command if runner_command is not None else os.environ.get("ENGLISH_MASTER_M9_AI_RUNNER"))
    configured_path = os.environ.get("ENGLISH_MASTER_M9_AI_RUNNER_CONFIG")
    effective_config_path = config_path if config_path is not None else (Path(configured_path) if configured_path else None)
    config = _load_config(effective_config_path)
    selection = load_strict_document(prepared_directory / "selection.json")
    selection_schema = "m9-selection-manifest-v2" if selection.get("schema_version") == "2.0" else "m9-selection-manifest"
    validate_instance(selection, selection_schema)
    selected = selection.get("subjects")
    expected_subjects = [
        {
            "subject_id": subject.subject_id,
            "content_type": subject.content_type,
            "lesson_id": subject.lesson_id,
            "artifact_path": subject.artifact_path,
            "artifact_sha256": subject.artifact_sha256,
            "machine_audit_path": subject.audit_path,
            "machine_audit_sha256": subject.audit_sha256,
            **({"modality": subject.modality} if subject.modality is not None else {}),
        }
        for subject in authority.subjects
    ]
    if selected != expected_subjects:
        raise RunnerOperationalError("prepared selection does not match current M9 authority")
    operation_count = len(authority.subjects) * len(CHECKLISTS)
    if operation_count != EXPECTED_OPERATION_COUNT:
        raise RunnerOperationalError(f"M9 capture requires exactly 120 operations, found {operation_count}")

    output_directory.parent.mkdir(parents=True, exist_ok=True)
    staging = Path(tempfile.mkdtemp(prefix=f".{output_directory.name}.staging-", dir=output_directory.parent))
    entries: list[JsonObject] = []
    executable = _resolved_executable(argv)
    try:
        operation_index = 0
        seen_execution_ids: set[tuple[str, str, str]] = set()
        for subject in authority.subjects:
            report = load_strict_document(prepared_directory / "machine" / f"{subject.subject_id}.json")
            report_at_value = report.get("reviewed_at")
            if not isinstance(report_at_value, str) or report != build_machine_report(
                authority, selection, subject, reviewed_at=report_at_value
            ):
                raise RunnerOperationalError(f"prepared machine report drift for {subject.subject_id}")
            for role in CHECKLISTS:
                operation_index += 1
                prompt = build_review_prompt(role, subject, report)
                stored_prompt = (prepared_directory / "prompts" / f"{subject.subject_id}--{role.lower()}.txt").read_text(encoding="utf-8")
                if stored_prompt != prompt + "\n":
                    raise RunnerOperationalError(f"prepared prompt drift for {subject.subject_id} {role}")
                request = build_runner_request(
                    selection=selection, subject_id=subject.subject_id, content_type=subject.content_type,
                    role=role, prompt=prompt, config=config, operation_index=operation_index,
                )
                response = dict(invoke(argv, request, timeout_seconds))
                validate_instance(response, "m9-ai-runner-response")
                if response.get("request_id") != request["request_id"]:
                    raise RunnerOperationalError("runner response request_id does not match the request")
                execution_key = (str(response["provider"]), str(response["model"]), str(response["execution_id"]))
                if execution_key in seen_execution_ids:
                    raise RunnerOperationalError(f"duplicate runner execution identity: {execution_key!r}")
                seen_execution_ids.add(execution_key)
                observed_at = _now()
                report_at = parse_orderable_timestamp(report.get("reviewed_at"))
                if report_at is None or parse_orderable_timestamp(observed_at) < report_at:
                    raise RunnerOperationalError("runner observation predates the machine report")
                wrapper: JsonObject = {
                    "capture": {
                        "capture_mode": "PROVIDER_CAPTURED", "runner_executable": executable,
                        "provider": response["provider"], "model": response["model"],
                        "execution_id": response["execution_id"], "provider_authenticated": False,
                        "observed_at": observed_at,
                    },
                    "raw_response": response["raw_response"], "reviewed_at": observed_at,
                }
                validate_instance(wrapper, "m9-ai-capture-wrapper")
                filename = f"{subject.subject_id}--{role.lower()}.json"
                (staging / filename).write_text(canonical_json(wrapper) + "\n", encoding="utf-8")
                entries.append({
                    "subject_id": subject.subject_id, "review_role": role, "path": filename,
                    "sha256": sha256_json(wrapper), "request_id": request["request_id"],
                })
        manifest: JsonObject = {
            "schema_version": "1.0", "record_type": "m9_ai_capture_manifest",
            "selection_id": selection["selection_id"], "runner_executable": executable,
            "config_sha256": sha256_json(config), "expected_operation_count": EXPECTED_OPERATION_COUNT,
            "successful_operation_count": len(entries), "complete": True, "captures": entries,
        }
        validate_instance(manifest, "m9-ai-capture-manifest")
        (staging / "capture-manifest.json").write_text(canonical_json(manifest) + "\n", encoding="utf-8")
        os.replace(staging, output_directory)
    except BaseException:
        shutil.rmtree(staging, ignore_errors=True)
        raise
    return output_directory
