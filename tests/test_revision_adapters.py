from __future__ import annotations

from english_master.revision_cycle.adapters import required_closure_issues


def test_m10_closure_requires_exact_request_scope() -> None:
    request = {"target_milestone": "M6", "rebuild_closure": [{"target_milestone": "M7", "artifact_kind": "EXERCISE_SET", "scope": "SUBJECT_LESSON", "lesson_id": "A1-U01-L01"}]}
    assert required_closure_issues(request, {"closure": list(request["rebuild_closure"])}) == ()
    assert required_closure_issues(request, {"closure": []})[0].code == "DEPENDENCY_REBUILD"


def test_m10_m82_closure_requires_complete_pilot() -> None:
    request = {"target_milestone": "M8_2", "rebuild_closure": []}
    assert required_closure_issues(request, {"closure": [], "pilot_artifact_count": 39})[0].code == "CLOSED_INVENTORY"
