from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

from english_master.independent_review.cli import _prepare
from english_master.independent_review.authority import VerifiedM9Authority
from english_master.independent_review.runner import (
    RunnerOperationalError,
    build_runner_request,
    capture_development,
    invoke_external_runner,
    parse_runner_command,
)
from english_master.independent_review.review import CHECKLISTS, build_ai_review
from english_master.independent_review.selection import build_selection
from english_master.schema_validation import load_document, validate_instance

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture(scope="module")
def authority() -> VerifiedM9Authority:
    return VerifiedM9Authority.from_files(
        structure_path=ROOT / "curriculum" / "structure.json",
        snapshot_directory=ROOT / "data" / "reviews" / "m5" / "development-20260903-062008",
        source_registry_path=ROOT / "sources" / "registry.yaml",
        m6_batch_path=ROOT / "data" / "generated" / "m6" / "development-batches" / "20260903-v6" / "development-batch.json",
        m6_root=ROOT / "data" / "generated" / "m6" / "development-candidates" / "20260903-v6-selected",
        exercise_root=ROOT / "curriculum" / "exercises",
        m7_batch_path=ROOT / "curriculum" / "exercises" / "development-batches" / "20260903-v3" / "development-batch.json",
        pilot_directory=ROOT / "curriculum" / "ai-practice" / "pilot-batches" / "20260905-v13",
    )


def _response(request: dict[str, object], *, execution_id: str) -> dict[str, object]:
    role = str(request["review_role"])
    return {
        "schema_version": "1.0",
        "record_type": "m9_ai_runner_response",
        "request_id": request["request_id"],
        "provider": "UNKNOWN",
        "model": "UNKNOWN",
        "execution_id": execution_id,
        "raw_response": {
            "decision": "APPROVE",
            "checklist": [
                {"criterion": criterion, "result": "PASS", "notes": "The immutable subject satisfies this criterion."}
                for criterion in CHECKLISTS[role]
            ],
            "findings": [],
            "limitations": ["Static AI review only; no live-provider behavior or Internet-wide search is claimed."],
        },
    }


def _write_runner(path: Path, body: str) -> Path:
    path.write_text(body, encoding="utf-8")
    return path


def test_external_runner_uses_one_canonical_json_request_and_allows_no_config(tmp_path: Path) -> None:
    script = _write_runner(
        tmp_path / "runner.py",
        """import json, sys\nr=json.loads(sys.stdin.read())\nassert r['config'] is None\no={'schema_version':'1.0','record_type':'m9_ai_runner_response','request_id':r['request_id'],'provider':'UNKNOWN','model':'UNKNOWN','execution_id':'exec-1','raw_response':{'decision':'APPROVE','checklist':[{'criterion':c,'result':'PASS','notes':'checked'} for c in r['checklist']],'findings':[],'limitations':['static review only']}}\nsys.stdout.buffer.write((json.dumps(o,ensure_ascii=False,sort_keys=True,separators=(',',':'))+'\\n').encode())\n""",
    )
    selection = {"selection_id": "m9select_" + "a" * 64}
    request = build_runner_request(
        selection=selection, subject_id="m9sub_" + "b" * 64, content_type="LESSON",
        role="LINGUISTIC_AI_REVIEWER", prompt="Review this.", config=None, operation_index=1,
    )
    response = invoke_external_runner((sys.executable, str(script)), request, 10)
    assert response["request_id"] == request["request_id"]
    assert response["provider"] == "UNKNOWN"


@pytest.mark.parametrize(
    "stdout",
    [
        "not-json\\n",
        '{"schema_version":"1.0","schema_version":"1.0"}\\n',
        '{"record_type":"m9_ai_runner_response"}\\n{"extra":true}\\n',
    ],
)
def test_external_runner_rejects_malformed_or_duplicate_stdout(tmp_path: Path, stdout: str) -> None:
    script = _write_runner(tmp_path / "bad.py", f"import sys\nsys.stdin.read()\nsys.stdout.write({stdout!r})\n")
    request = build_runner_request(
        selection={"selection_id": "m9select_" + "a" * 64}, subject_id="m9sub_" + "b" * 64,
        content_type="LESSON", role="LINGUISTIC_AI_REVIEWER", prompt="Review.", config=None,
        operation_index=1,
    )
    with pytest.raises(RunnerOperationalError):
        invoke_external_runner((sys.executable, str(script)), request, 10)


def test_runner_command_is_required_and_never_uses_a_shell() -> None:
    with pytest.raises(RunnerOperationalError, match="not configured"):
        parse_runner_command(None)
    assert parse_runner_command(f'{sys.executable} "runner path.py"') == (sys.executable, "runner path.py")


def test_capture_development_is_closed_atomic_and_publish_compatible(authority, tmp_path: Path) -> None:
    prepared = _prepare(authority, tmp_path / "prepared", "2026-09-05T10:00:00Z")
    config_path = tmp_path / "runner-config.json"
    config_path.write_text('{"temperature":0}', encoding="utf-8")
    calls: list[dict[str, object]] = []

    def invoke(argv, request, timeout):
        assert argv == (sys.executable,)
        assert timeout == 12
        assert request["config"] == {"temperature": 0}
        calls.append(dict(request))
        return _response(dict(request), execution_id=f"exec-{len(calls):03d}")

    captures = capture_development(
        authority=authority, prepared_directory=prepared, output_directory=tmp_path / "captures",
        runner_command=sys.executable, config_path=config_path, timeout_seconds=12, invoke=invoke,
    )
    assert len(calls) == 120
    assert [call["operation_index"] for call in calls] == list(range(1, 121))
    manifest = load_document(captures / "capture-manifest.json")
    validate_instance(manifest, "m9-ai-capture-manifest")
    assert manifest["successful_operation_count"] == 120
    subject = authority.subjects[0]
    role = "LINGUISTIC_AI_REVIEWER"
    wrapper = load_document(captures / f"{subject.subject_id}--{role.lower()}.json")
    review = build_ai_review(
        selection=load_document(prepared / "selection.json"), subject=subject,
        machine_report=load_document(prepared / "machine" / f"{subject.subject_id}.json"),
        role=role, capture=wrapper["capture"], raw_response=wrapper["raw_response"],
        reviewed_at=wrapper["reviewed_at"],
    )
    assert review["capture"]["runner_executable"]
    with pytest.raises(FileExistsError):
        capture_development(
            authority=authority, prepared_directory=prepared, output_directory=captures,
            runner_command=sys.executable, invoke=invoke,
        )


def test_capture_failure_leaves_no_partial_output(authority, tmp_path: Path) -> None:
    prepared = _prepare(authority, tmp_path / "prepared", "2026-09-05T10:00:00Z")
    output = tmp_path / "captures"
    count = 0

    def fail_second(argv, request, timeout):
        nonlocal count
        count += 1
        if count == 2:
            raise RunnerOperationalError("provider unavailable")
        return _response(dict(request), execution_id=f"exec-{count}")

    with pytest.raises(RunnerOperationalError, match="provider unavailable"):
        capture_development(
            authority=authority, prepared_directory=prepared, output_directory=output,
            runner_command=sys.executable, invoke=fail_second,
        )
    assert not output.exists()
    assert not list(tmp_path.glob(".captures.staging-*"))
