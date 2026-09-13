"""Adaptive review policy implementation."""
from __future__ import annotations
import json
from datetime import timedelta
from pathlib import Path
from typing import Any
from english_master.lesson_generation.canonical import sha256_json
from english_master.schema_validation import load_document, validate_instance
from english_master.assessment_mastery.learner_state import _response_correct
from .state import INTERVALS, atomic_write, load_state, parse_utc, utc

POLICY_VERSION = "ADAPTIVE_REVIEW_V1"
REASONS = ("NEW_LESSON", "RECENT_MISTAKE", "DUE", "OLD_WEAK")

def _read(path: Path) -> Any:
    with path.open(encoding="utf-8") as fh: return json.load(fh)

def _state_hash(state: list[dict[str, Any]]) -> str: return sha256_json(state)
def _write_no_overwrite(path: Path, value: dict[str, Any]) -> None:
    if path.exists(): raise FileExistsError(f"refusing to overwrite {path}")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n", encoding="utf-8")

def _answer(item: dict[str, Any], response: Any) -> bool: return _response_correct(item, response)

def observe_submission(*, package_path: Path, submission_path: Path, adaptive_state_path: Path, output_path: Path) -> dict[str, Any]:
    package = load_document(package_path); validate_instance(package, "assessment-package-v1")
    if package["package_sha256"] != sha256_json({k:v for k,v in package.items() if k != "package_sha256"}): raise ValueError("package hash mismatch")
    submission = load_document(submission_path); validate_instance(submission, "assessment-submission-v1")
    if submission["submission_sha256"] != sha256_json({k:v for k,v in submission.items() if k != "submission_sha256"}): raise ValueError("submission hash mismatch")
    if submission["assessment_id"] != package["assessment_id"] or submission["package_sha256"] != package["package_sha256"]: raise ValueError("submission binding mismatch")
    parse_utc(submission["seen_at"])
    items = {item["item_id"]: item for item in package["items"]}; responses = submission["responses"]
    if len(responses) != len(items) or {r["item_id"] for r in responses} != set(items): raise ValueError("submission must be complete")
    outcomes: dict[str, list[bool]] = {}
    for response in responses:
        item = items[response["item_id"]]; result = _answer(item, response["answer"])
        for concept in set(item["concept_ids"]): outcomes.setdefault(concept, []).append(result)
    old = {r["concept_id"]: r for r in load_state(adaptive_state_path)}; seen = parse_utc(submission["seen_at"])
    for concept, values in sorted(outcomes.items()):
        previous = old.get(concept)
        if previous and parse_utc(previous["last_reviewed_at"]) > seen: raise ValueError("observation precedes existing adaptive state")
        wrong = not all(values); index = 0 if wrong else min((previous["interval_index"] + 1) if previous else 0, 5)
        old[concept] = {"concept_id": concept, "interval_index": index, "last_reviewed_at": submission["seen_at"], "last_mistake_at": submission["seen_at"] if wrong else (previous["last_mistake_at"] if previous else None), "next_review": utc(seen + timedelta(days=1 if wrong else INTERVALS[index]))}
    new_state = [old[k] for k in sorted(old)]
    observation = {"schema_version":"1.0","record_type":"adaptive_review_observation","policy_version":POLICY_VERSION,"assessment_id":package["assessment_id"],"package_sha256":package["package_sha256"],"submission_sha256":submission["submission_sha256"],"seen_at":submission["seen_at"],"concept_outcomes":[{"concept_id":k,"correct":all(v)} for k,v in sorted(outcomes.items())]}
    observation["observation_sha256"] = sha256_json(observation); validate_instance(observation, "adaptive-review-observation-v1")
    _write_no_overwrite(output_path, observation); atomic_write(adaptive_state_path, new_state)
    return observation

def _catalog(run_dir: Path) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    manifest = load_document(run_dir / "manifest.json"); validate_instance(manifest, "assessment-run-manifest-v1")
    if manifest["counts"] != {"lesson_quizzes":300,"unit_tests":60,"level_tests":6,"placement_packages":1,"packages":367}: raise ValueError("unexpected assessment inventory")
    items=[]
    for entry in manifest["package_inventory"]:
        if entry["assessment_type"] != "LESSON_QUIZ": continue
        package = load_document(run_dir / entry["path"]); validate_instance(package, "assessment-package-v1")
        if package["package_sha256"] != entry["package_sha256"] or package["content_status"] != "UNREVIEWED": raise ValueError("assessment package drift")
        for item in package["items"]:
            if item["item_sha256"] != sha256_json({k:v for k,v in item.items() if k != "item_sha256"}): raise ValueError("assessment item hash mismatch")
            items.append({"package":package,"item":item})
    return manifest, items

def build_review_plan(*, assessment_run: Path, state_path: Path, adaptive_state_path: Path, lesson_id: str, as_of: str, output_path: Path, limit: int = 10) -> dict[str, Any]:
    if limit < 1 or limit > 100: raise ValueError("limit must be 1..100")
    now = parse_utc(as_of); manifest, catalog = _catalog(assessment_run)
    state = _read(state_path) if state_path.exists() else []
    validate_instance(state, "learner-concept-state-v1")
    ids=[r["concept_id"] for r in state]
    if ids != sorted(ids) or len(ids)!=len(set(ids)): raise ValueError("learner state must be sorted and unique")
    adaptive = load_state(adaptive_state_path); adapt={r["concept_id"]:r for r in adaptive}; mastery={r["concept_id"]:r for r in state}
    lesson_items=[x for x in catalog if x["item"]["source"]["lesson_id"] == lesson_id]
    if not lesson_items: raise ValueError(f"lesson not found: {lesson_id}")
    by_concept: dict[str,list[dict[str,Any]]] = {}
    for entry in catalog:
        for concept in entry["item"]["concept_ids"]: by_concept.setdefault(concept,[]).append(entry)
    new_concepts={c for e in lesson_items for c in e["item"]["concept_ids"]}
    candidates=[]
    for concept, entries in by_concept.items():
        reasons=[]; row=mastery.get(concept); ar=adapt.get(concept)
        if concept in new_concepts: reasons.append("NEW_LESSON")
        if ar and ar["last_mistake_at"] and now - parse_utc(ar["last_mistake_at"]) <= timedelta(days=7) and parse_utc(ar["last_mistake_at"]) <= now: reasons.append("RECENT_MISTAKE")
        if ar and parse_utc(ar["next_review"]) <= now: reasons.append("DUE")
        if row and row["mastery"] < .8 and now - parse_utc(row["last_seen"]) >= timedelta(days=14): reasons.append("OLD_WEAK")
        if not reasons: continue
        chosen=sorted((e for e in entries if reasons==["NEW_LESSON"] and e["item"]["source"]["lesson_id"]==lesson_id) or entries, key=lambda e: sha256_json([POLICY_VERSION,concept,e["item"]["item_sha256"]]))[0]
        candidates.append((REASONS.index(next(r for r in REASONS if r in reasons)), concept, reasons, chosen, row, ar))
    candidates.sort(key=lambda x:(x[0], -(parse_utc(x[5]["last_mistake_at"]).timestamp() if x[5] and x[5]["last_mistake_at"] and "RECENT_MISTAKE" in x[2] else 0), parse_utc(x[5]["next_review"]).timestamp() if x[5] and "DUE" in x[2] else 0, x[4]["mastery"] if x[4] else 1, x[1]))
    entries=[]
    for _, concept, reasons, chosen, _, _ in candidates[:limit]:
        entries.append({"concept_id":concept,"reasons":reasons,"item_id":chosen["item"]["item_id"],"item_sha256":chosen["item"]["item_sha256"],"assessment_id":chosen["package"]["assessment_id"],"package_sha256":chosen["package"]["package_sha256"],"source_lesson_id":chosen["item"]["source"]["lesson_id"]})
    plan={"schema_version":"1.0","record_type":"adaptive_review_plan","policy_version":POLICY_VERSION,"assessment_run_id":assessment_run.name,"manifest_sha256":manifest["manifest_sha256"],"state_sha256":_state_hash(state),"adaptive_state_sha256":_state_hash(adaptive),"lesson_id":lesson_id,"as_of":as_of,"limit":limit,"entries":entries}
    plan["plan_sha256"]=sha256_json(plan); validate_instance(plan,"adaptive-review-plan-v1"); _write_no_overwrite(output_path,plan); return plan
