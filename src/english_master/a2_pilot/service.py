"""Deterministic construction and review summaries for the bounded A2 pilot."""

from __future__ import annotations

import hashlib
import json
import re
import shutil
import unicodedata
from collections import Counter
from pathlib import Path
from typing import Any, Mapping, Sequence

from english_master.a2_curriculum_blueprint import validate as validate_blueprint
from english_master.knowledge_graph.service import validate_population
from english_master.lesson_generation.canonical import sha256_json
from english_master.schema_validation import load_document, validate_instance

PILOT_LESSON_COUNT = 10
SAMPLE_POLICY_VERSION = "A2_PILOT_SHA256_UNIT_STRATIFIED_V1"
PROMPT_MODALITIES = ("listening", "speaking", "pronunciation", "writing")
REVIEW_DIMENSIONS = (
    "explanation_clarity",
    "grammar_correctness",
    "vocabulary_difficulty",
    "exercise_quality",
    "prompt_usability",
    "lesson_duration",
    "duplication",
)
_FORBIDDEN_CLAIMS = {"human_reviewed", "release_approved", "provider_authenticated"}


def _canonical_bytes(value: Any) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")


def _sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _normalized(value: str) -> str:
    return " ".join(unicodedata.normalize("NFKC", value).casefold().split())


def _assert_safe_name(value: str, label: str) -> None:
    if not re.fullmatch(r"[a-z0-9][a-z0-9_-]*", value):
        raise ValueError(f"{label} is not a safe lowercase identifier: {value!r}")


def _assert_no_claims(value: Any) -> None:
    if isinstance(value, Mapping):
        forbidden = _FORBIDDEN_CLAIMS.intersection(value)
        if forbidden:
            raise ValueError(f"A2 pilot must not contain approval/provider claim fields: {sorted(forbidden)!r}")
        for child in value.values():
            _assert_no_claims(child)
    elif isinstance(value, list):
        for child in value:
            _assert_no_claims(child)


def _first_ten_a2_outlines(blueprint: Mapping[str, Any]) -> list[dict[str, Any]]:
    units = {unit["id"]: unit for unit in blueprint["units"]}
    selected = [lesson for lesson in blueprint["lessons"] if lesson["tier"] == "A2.1"]
    selected.sort(key=lambda lesson: (units[lesson["unit_id"]]["sequence"], lesson["sequence"]))
    if len(selected) < PILOT_LESSON_COUNT:
        raise ValueError("M16 blueprint does not contain ten A2.1 lessons for the pilot")
    return selected[:PILOT_LESSON_COUNT]


def _adapt_content_record(raw: Mapping[str, Any]) -> dict[str, Any]:
    """Convert the human-friendly authored input into the compact packet shape."""

    sections = []
    for index, section in enumerate(raw.get("content_sections", []), start=1):
        sections.append({
            "id": f"section-{index}",
            "title": section.get("title", ""),
            "body": section.get("body", ""),
            "section_type": section.get("section_type", "explanation"),
        })
    exercises = []
    for index, exercise in enumerate(raw.get("exercises", []), start=1):
        rubric = exercise.get("rubric")
        if isinstance(rubric, Mapping):
            rubric = "; ".join(str(value) for value in rubric.get("criteria", []))
        answer = exercise.get("answer")
        if not answer and "answer_data" in exercise:
            answer = json.dumps(exercise["answer_data"], ensure_ascii=False, sort_keys=True)
        if not answer and "items" in exercise:
            answer = json.dumps(exercise["items"], ensure_ascii=False, sort_keys=True)
        exercises.append({
            "id": f"exercise-{index}",
            "type": exercise.get("exercise_type", exercise.get("type", "practice")),
            "prompt": exercise.get("instructions", exercise.get("prompt", "")),
            "answer": answer,
            "rubric": rubric,
            "items": exercise.get("items", []),
        })
    prompts = {}
    for modality, prompt in raw.get("prompts", {}).items():
        prompts[modality] = {
            "instruction": prompt.get("prompt", prompt.get("instruction", "")),
            "goal": prompt.get("goal", f"Practise the {modality} target for this lesson."),
            "constraints": prompt.get("constraints", []),
        }
    return {
        "lesson_id": raw.get("lesson_id", raw.get("outline_id")),
        "title": raw.get("title", ""),
        "duration_minutes": raw.get("duration_minutes"),
        "objectives": raw.get("objectives", []),
        "content_sections": sections,
        "exercises": exercises,
        "prompts": prompts,
    }


def _validate_content_record(record: Mapping[str, Any], outline: Mapping[str, Any]) -> None:
    if record.get("lesson_id") != outline["id"]:
        raise ValueError(f"content record lesson_id does not match selected outline {outline['id']}")
    if not isinstance(record.get("duration_minutes"), int) or not 15 <= record["duration_minutes"] <= 45:
        raise ValueError(f"{outline['id']} duration_minutes must be between 15 and 45")
    sections = record.get("content_sections")
    if not isinstance(sections, list) or not 2 <= len(sections) <= 4:
        raise ValueError(f"{outline['id']} must have two to four content sections")
    exercises = record.get("exercises")
    if not isinstance(exercises, list) or not 3 <= len(exercises) <= 6:
        raise ValueError(f"{outline['id']} must have three to six exercises")
    identifiers: set[str] = set()
    for exercise in exercises:
        exercise_id = exercise.get("id")
        if not isinstance(exercise_id, str) or not exercise_id or exercise_id in identifiers:
            raise ValueError(f"{outline['id']} has missing or duplicate exercise IDs")
        identifiers.add(exercise_id)
        if not isinstance(exercise.get("prompt"), str) or not exercise["prompt"].strip():
            raise ValueError(f"{outline['id']} exercise {exercise_id} has no prompt")
        answer = exercise.get("answer")
        rubric = exercise.get("rubric")
        if not (isinstance(answer, str) and answer.strip()) and not (isinstance(rubric, str) and rubric.strip()):
            raise ValueError(f"{outline['id']} exercise {exercise_id} needs an answer or rubric")
        exercise_type = exercise.get("type")
        if exercise_type == "multiple_choice":
            items = exercise.get("items")
            if not isinstance(items, list) or len(items) < 3 or not all(isinstance(item, str) and item.strip() for item in items):
                raise ValueError(f"{outline['id']} exercise {exercise_id} multiple choice needs at least three options")
        if exercise_type == "reading" and "Read the text:" not in exercise["prompt"]:
            raise ValueError(f"{outline['id']} exercise {exercise_id} reading task needs an included text")
    prompts = record.get("prompts")
    if not isinstance(prompts, Mapping) or set(prompts) != set(PROMPT_MODALITIES) or len(prompts) != len(PROMPT_MODALITIES):
        raise ValueError(f"{outline['id']} must provide exactly {PROMPT_MODALITIES!r} prompts")
    for modality, prompt in prompts.items():
        if not isinstance(prompt, Mapping) or not isinstance(prompt.get("instruction"), str) or not prompt["instruction"].strip():
            raise ValueError(f"{outline['id']} {modality} prompt needs a nonempty instruction")


def _learner_strings(packet: Mapping[str, Any]) -> list[tuple[str, str]]:
    strings: list[tuple[str, str]] = []
    for section in packet["content_sections"]:
        strings.append((f"{packet['lesson_id']}/section/{section['id']}", section["body"]))
    for exercise in packet["exercises"]:
        strings.append((f"{packet['lesson_id']}/exercise/{exercise['id']}", exercise["prompt"]))
    for modality, prompt in packet["prompts"].items():
        strings.append((f"{packet['lesson_id']}/prompt/{modality}", prompt["instruction"]))
    return strings


def _validate_duplicate_text(packets: Sequence[Mapping[str, Any]]) -> None:
    occurrences: dict[str, list[str]] = {}
    for packet in packets:
        for location, text in _learner_strings(packet):
            key = _normalized(text)
            if len(key) >= 24:
                occurrences.setdefault(key, []).append(location)
    duplicated = [locations for locations in occurrences.values() if len(locations) > 1]
    if duplicated:
        raise ValueError(f"duplicated learner-facing text: {duplicated[0]!r}")


def _packet_payload(outline: Mapping[str, Any], content: Mapping[str, Any], index: int) -> dict[str, Any]:
    packet = {
        "schema_version": "1.0",
        "record_type": "a2_pilot_lesson_packet",
        "packet_id": f"a2pilot-packet-{index:02d}",
        "lesson_id": outline["id"],
        "tier": outline["tier"],
        "sequence": index,
        "outline_targets": outline["targets"],
        "prerequisite_lesson_ids": outline["prerequisite_lesson_ids"],
        "title": content["title"],
        "duration_minutes": content["duration_minutes"],
        "objectives": content["objectives"],
        "content_sections": content["content_sections"],
        "exercises": content["exercises"],
        "prompts": content["prompts"],
        "content_status": "UNREVIEWED",
        "provenance": {"content_origin": "PROJECT_AUTHORED", "content_input_id": content["lesson_id"]},
    }
    packet["packet_sha256"] = sha256_json(packet)
    return packet


def _validate_packet(packet: Mapping[str, Any]) -> None:
    validate_instance(packet, "a2-pilot-lesson-packet")
    actual = dict(packet)
    declared = actual.pop("packet_sha256")
    if declared != sha256_json(actual):
        raise ValueError(f"packet hash mismatch: {packet['packet_id']}")
    _assert_no_claims(packet)


def build_pilot(
    *,
    population_path: Path,
    blueprint_path: Path,
    content_path: Path,
    output_root: Path,
    built_at: str,
) -> Path:
    """Build a closed, no-overwrite ten-packet A2.1 pilot."""

    population = load_document(population_path)
    blueprint = load_document(blueprint_path)
    content_input = load_document(content_path)
    validate_instance(content_input, "a2-pilot-content-input")
    validate_population(population)
    validate_blueprint(blueprint, population)
    _assert_no_claims(content_input)
    outlines = _first_ten_a2_outlines(blueprint)
    content_records = content_input["lessons"]
    content_by_id = {_adapt_content_record(record)["lesson_id"]: _adapt_content_record(record) for record in content_records}
    selected_ids = [outline["id"] for outline in outlines]
    if set(content_by_id) != set(selected_ids) or len(content_by_id) != PILOT_LESSON_COUNT:
        raise ValueError("content input must contain exactly the ten selected A2.1 outline lesson IDs")

    packets: list[dict[str, Any]] = []
    for index, outline in enumerate(outlines, start=1):
        content = content_by_id[outline["id"]]
        _validate_content_record(content, outline)
        packet = _packet_payload(outline, content, index)
        _validate_packet(packet)
        packets.append(packet)
    _validate_duplicate_text(packets)

    source = {
        "population_sha256": sha256_json(population),
        "blueprint_sha256": sha256_json(blueprint),
        "content_input_sha256": sha256_json(content_input),
        "built_at": built_at,
    }
    pilot_id = "a2pilot_" + hashlib.sha256(_canonical_bytes({"source": source, "lesson_ids": selected_ids})).hexdigest()
    _assert_safe_name(pilot_id, "pilot_id")
    destination = output_root / pilot_id
    if destination.exists():
        raise FileExistsError(f"refusing to overwrite existing A2 pilot: {destination}")
    temporary = output_root / f".{pilot_id}.tmp"
    if temporary.exists():
        raise FileExistsError(f"temporary A2 pilot path already exists: {temporary}")
    temporary.mkdir(parents=True)
    try:
        inventory: list[dict[str, str]] = []
        packets_dir = temporary / "packets"
        packets_dir.mkdir()
        for packet in packets:
            relative = f"packets/{packet['packet_id']}.json"
            path = temporary / relative
            path.write_bytes(_canonical_bytes(packet) + b"\n")
            inventory.append({"path": relative, "sha256": _sha256_file(path)})
        manifest = {
            "schema_version": "1.0",
            "record_type": "a2_pilot_manifest",
            "pilot_id": pilot_id,
            "built_at": built_at,
            "content_status": "UNREVIEWED",
            "source": source,
            "lesson_ids": selected_ids,
            "inventory": inventory,
        }
        manifest["manifest_sha256"] = sha256_json(manifest)
        validate_instance(manifest, "a2-pilot-manifest")
        manifest_path = temporary / "manifest.json"
        manifest_path.write_bytes(_canonical_bytes(manifest) + b"\n")
        temporary.replace(destination)
    except BaseException:
        shutil.rmtree(temporary, ignore_errors=True)
        raise
    return destination


def verify_pilot(pilot_dir: Path, population_path: Path, blueprint_path: Path) -> dict[str, Any]:
    """Read-only verification of a closed pilot directory and its source bindings."""

    population = load_document(population_path)
    blueprint = load_document(blueprint_path)
    validate_population(population)
    validate_blueprint(blueprint, population)
    outlines = {outline["id"]: outline for outline in _first_ten_a2_outlines(blueprint)}
    manifest = load_document(pilot_dir / "manifest.json")
    validate_instance(manifest, "a2-pilot-manifest")
    declared_manifest = dict(manifest)
    manifest_sha256 = declared_manifest.pop("manifest_sha256")
    if manifest_sha256 != sha256_json(declared_manifest):
        raise ValueError("A2 pilot manifest hash mismatch")
    source = manifest["source"]
    if source["population_sha256"] != sha256_json(population) or source["blueprint_sha256"] != sha256_json(blueprint):
        raise ValueError("A2 pilot source binding drift")
    expected_paths = {"manifest.json"}
    packets: list[dict[str, Any]] = []
    for item in manifest["inventory"]:
        relative = item["path"]
        if not re.fullmatch(r"packets/a2pilot-packet-\d{2}\.json", relative):
            raise ValueError(f"unsafe A2 pilot inventory path: {relative}")
        expected_paths.add(relative)
        path = pilot_dir / relative
        if not path.is_file() or _sha256_file(path) != item["sha256"]:
            raise ValueError(f"A2 pilot inventory hash mismatch: {relative}")
        packet = load_document(path)
        _validate_packet(packet)
        outline = outlines.get(packet["lesson_id"])
        if outline is None or packet["tier"] != outline["tier"] or packet["outline_targets"] != outline["targets"] or packet["prerequisite_lesson_ids"] != outline["prerequisite_lesson_ids"]:
            raise ValueError(f"A2 pilot packet does not match blueprint outline: {packet['lesson_id']}")
        packets.append(packet)
    actual_paths = {path.relative_to(pilot_dir).as_posix() for path in pilot_dir.rglob("*") if path.is_file()}
    if actual_paths != expected_paths:
        raise ValueError("A2 pilot has a non-closed file inventory")
    if len(packets) != PILOT_LESSON_COUNT or [packet["lesson_id"] for packet in packets] != manifest["lesson_ids"]:
        raise ValueError("A2 pilot lesson inventory is not the declared ordered ten-lesson scope")
    if [packet["sequence"] for packet in packets] != list(range(1, PILOT_LESSON_COUNT + 1)):
        raise ValueError("A2 pilot packet sequence is invalid")
    _validate_duplicate_text(packets)
    return manifest


def build_review_template(*, pilot_dir: Path, population_path: Path, blueprint_path: Path, output_path: Path) -> Path:
    """Write a blank, explicitly incomplete review template for a verified pilot."""

    manifest = verify_pilot(pilot_dir, population_path, blueprint_path)
    template = {
        "schema_version": "1.0",
        "record_type": "a2_pilot_review",
        "pilot_id": manifest["pilot_id"],
        "manifest_sha256": manifest["manifest_sha256"],
        "reviewers": [{"reviewer_type": "USER", "identifier": "REPLACE_WITH_USER_IDENTIFIER"}],
        "lessons": [
            {
                "lesson_id": lesson_id,
                "dimensions": {dimension: "NOT_RUN" for dimension in REVIEW_DIMENSIONS},
                "findings": [],
            }
            for lesson_id in manifest["lesson_ids"]
        ],
    }
    validate_instance(template, "a2-pilot-review")
    if output_path.exists():
        raise FileExistsError(f"refusing to overwrite A2 review template: {output_path}")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_bytes(_canonical_bytes(template) + b"\n")
    return output_path


def summarize_review(*, pilot_dir: Path, population_path: Path, blueprint_path: Path, review_path: Path, output_path: Path) -> Path:
    """Validate one user/AI development review and write its deterministic summary."""

    manifest = verify_pilot(pilot_dir, population_path, blueprint_path)
    review = load_document(review_path)
    validate_instance(review, "a2-pilot-review")
    _assert_no_claims(review)
    if review["pilot_id"] != manifest["pilot_id"] or review["manifest_sha256"] != manifest["manifest_sha256"]:
        raise ValueError("review does not bind this A2 pilot manifest")
    for reviewer in review["reviewers"]:
        if reviewer["reviewer_type"] == "AI" and (not reviewer.get("provider") or not reviewer.get("model")):
            raise ValueError("AI review provenance requires provider and model facts or UNKNOWN")
    for entry in review["lessons"]:
        if any(result == "NOT_RUN" for result in entry["dimensions"].values()):
            raise ValueError("a completed A2 pilot review cannot contain NOT_RUN dimensions")
        for finding in entry["findings"]:
            if finding["classification"] == "SYSTEMIC" and not finding.get("generator_rule"):
                raise ValueError("a systemic finding must identify a generator rule to change")
    lesson_ids = manifest["lesson_ids"]
    entries = review["lessons"]
    if [entry["lesson_id"] for entry in entries] != lesson_ids:
        raise ValueError("review must cover the ordered closed ten-lesson pilot inventory")
    all_findings = [finding for entry in entries for finding in entry["findings"]]
    systemic = [finding for finding in all_findings if finding["classification"] == "SYSTEMIC"]
    isolated = [finding for finding in all_findings if finding["classification"] == "ISOLATED"]
    summary = {
        "schema_version": "1.0",
        "record_type": "a2_pilot_review_summary",
        "pilot_id": manifest["pilot_id"],
        "manifest_sha256": manifest["manifest_sha256"],
        "review_sha256": sha256_json(review),
        "content_status": "UNREVIEWED",
        "systemic_findings": systemic,
        "isolated_findings": isolated,
        "next_action": "FIX_GENERATOR" if systemic else "REPLACE_LOCAL_PACKETS" if isolated else "NO_BLOCKING_FINDINGS",
    }
    validate_instance(summary, "a2-pilot-review-summary")
    if output_path.exists():
        raise FileExistsError(f"refusing to overwrite A2 review summary: {output_path}")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_bytes(_canonical_bytes(summary) + b"\n")
    return output_path


AUDIT_CHECKS = ("run_verification", "target_scope", "exercise_contracts", "four_modalities", "duplicate_text")

def audit_pilot(*, pilot_dir: Path, population_path: Path, blueprint_path: Path, output_path: Path) -> dict[str, Any]:
    manifest = verify_pilot(pilot_dir, population_path, blueprint_path)
    report = {"schema_version":"1.0","record_type":"a2_pilot_audit","pilot_id":manifest["pilot_id"],"manifest_sha256":manifest["manifest_sha256"],"checks":[{"name":name,"result":"PASS"} for name in AUDIT_CHECKS],"result":"PASS","limitations":["Consistency checks do not establish pedagogical quality, approval, release, or live provider behavior."]}
    report["report_sha256"] = sha256_json(report)
    if output_path.exists(): raise FileExistsError(f"refusing to overwrite A2 pilot audit: {output_path}")
    output_path.parent.mkdir(parents=True, exist_ok=True); output_path.write_bytes(_canonical_bytes(report)+b"\n")
    return report

def sample_pilot(*, pilot_dir: Path, population_path: Path, blueprint_path: Path, audit_report_path: Path, seed: str, sample_size: int = 5, output_path: Path) -> dict[str, Any]:
    if not 5 <= sample_size <= 10: raise ValueError("A2 pilot sample size must be between 5 and 10")
    manifest = verify_pilot(pilot_dir, population_path, blueprint_path); audit = load_document(audit_report_path)
    declared=dict(audit); report_hash=declared.pop("report_sha256",None)
    if report_hash != sha256_json(declared) or audit["result"] != "PASS" or audit["pilot_id"] != manifest["pilot_id"]: raise ValueError("A2 pilot sampling requires a passing, hash-valid audit report")
    rankings=[]
    for index,lesson_id in enumerate(manifest["lesson_ids"],1):
        digest=hashlib.sha256(f"{report_hash}\0{seed}\0{SAMPLE_POLICY_VERSION}\0{lesson_id}".encode()).hexdigest(); rankings.append({"lesson_id":lesson_id,"rank_hash":digest,"selected":False,"sequence":index})
    rankings.sort(key=lambda row:row["rank_hash"]); selected=[]
    for prefix in ("m16a2-v1-a2-u01-","m16a2-v1-a2-u02-"): selected.append(next(row for row in rankings if row["lesson_id"].startswith(prefix)))
    for row in rankings:
        if len(selected)>=sample_size: break
        if row not in selected: selected.append(row)
    selected_ids={row["lesson_id"] for row in selected}
    for row in rankings: row["selected"]=row["lesson_id"] in selected_ids
    value={"schema_version":"1.0","record_type":"a2_pilot_sample","pilot_id":manifest["pilot_id"],"audit_report_sha256":report_hash,"seed":seed,"algorithm_version":SAMPLE_POLICY_VERSION,"sample_size":sample_size,"selected_lesson_ids":[row["lesson_id"] for row in selected],"rankings":rankings}; value["sample_sha256"]=sha256_json(value)
    if output_path.exists(): raise FileExistsError(f"refusing to overwrite A2 pilot sample: {output_path}")
    output_path.parent.mkdir(parents=True,exist_ok=True); output_path.write_bytes(_canonical_bytes(value)+b"\n"); return value
