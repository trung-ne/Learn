"""Deterministic construction and review summaries for the bounded A1 pilot."""

from __future__ import annotations

import hashlib
import json
import re
import shutil
import unicodedata
from collections import Counter
from pathlib import Path
from typing import Any, Mapping, Sequence

from english_master.curriculum_blueprint import validate as validate_blueprint
from english_master.knowledge_graph.service import validate_population
from english_master.lesson_generation.canonical import sha256_json
from english_master.schema_validation import load_document, validate_instance

PILOT_LESSON_COUNT = 10
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
            raise ValueError(f"A1 pilot must not contain approval/provider claim fields: {sorted(forbidden)!r}")
        for child in value.values():
            _assert_no_claims(child)
    elif isinstance(value, list):
        for child in value:
            _assert_no_claims(child)


def _first_ten_a1_outlines(blueprint: Mapping[str, Any]) -> list[dict[str, Any]]:
    units = {unit["id"]: unit for unit in blueprint["units"]}
    selected = [lesson for lesson in blueprint["lessons"] if lesson["tier"] == "A1.1"]
    selected.sort(key=lambda lesson: (units[lesson["unit_id"]]["sequence"], lesson["sequence"]))
    if len(selected) < PILOT_LESSON_COUNT:
        raise ValueError("M16 blueprint does not contain ten A1.1 lessons for the pilot")
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
        "record_type": "a1_pilot_lesson_packet",
        "packet_id": f"a1pilot-packet-{index:02d}",
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
    validate_instance(packet, "a1-pilot-lesson-packet")
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
    """Build a closed, no-overwrite ten-packet A1.1 pilot."""

    population = load_document(population_path)
    blueprint = load_document(blueprint_path)
    content_input = load_document(content_path)
    validate_instance(content_input, "a1-pilot-content-input")
    validate_population(population)
    validate_blueprint(blueprint, population)
    _assert_no_claims(content_input)
    outlines = _first_ten_a1_outlines(blueprint)
    content_records = content_input["lessons"]
    content_by_id = {_adapt_content_record(record)["lesson_id"]: _adapt_content_record(record) for record in content_records}
    selected_ids = [outline["id"] for outline in outlines]
    if set(content_by_id) != set(selected_ids) or len(content_by_id) != PILOT_LESSON_COUNT:
        raise ValueError("content input must contain exactly the ten selected A1.1 outline lesson IDs")

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
    pilot_id = "a1pilot_" + hashlib.sha256(_canonical_bytes({"source": source, "lesson_ids": selected_ids})).hexdigest()
    _assert_safe_name(pilot_id, "pilot_id")
    destination = output_root / pilot_id
    if destination.exists():
        raise FileExistsError(f"refusing to overwrite existing A1 pilot: {destination}")
    temporary = output_root / f".{pilot_id}.tmp"
    if temporary.exists():
        raise FileExistsError(f"temporary A1 pilot path already exists: {temporary}")
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
            "record_type": "a1_pilot_manifest",
            "pilot_id": pilot_id,
            "built_at": built_at,
            "content_status": "UNREVIEWED",
            "source": source,
            "lesson_ids": selected_ids,
            "inventory": inventory,
        }
        manifest["manifest_sha256"] = sha256_json(manifest)
        validate_instance(manifest, "a1-pilot-manifest")
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
    manifest = load_document(pilot_dir / "manifest.json")
    validate_instance(manifest, "a1-pilot-manifest")
    declared_manifest = dict(manifest)
    manifest_sha256 = declared_manifest.pop("manifest_sha256")
    if manifest_sha256 != sha256_json(declared_manifest):
        raise ValueError("A1 pilot manifest hash mismatch")
    source = manifest["source"]
    if source["population_sha256"] != sha256_json(population) or source["blueprint_sha256"] != sha256_json(blueprint):
        raise ValueError("A1 pilot source binding drift")
    expected_paths = {"manifest.json"}
    packets: list[dict[str, Any]] = []
    for item in manifest["inventory"]:
        relative = item["path"]
        if not re.fullmatch(r"packets/a1pilot-packet-\d{2}\.json", relative):
            raise ValueError(f"unsafe A1 pilot inventory path: {relative}")
        expected_paths.add(relative)
        path = pilot_dir / relative
        if not path.is_file() or _sha256_file(path) != item["sha256"]:
            raise ValueError(f"A1 pilot inventory hash mismatch: {relative}")
        packet = load_document(path)
        _validate_packet(packet)
        packets.append(packet)
    actual_paths = {path.relative_to(pilot_dir).as_posix() for path in pilot_dir.rglob("*") if path.is_file()}
    if actual_paths != expected_paths:
        raise ValueError("A1 pilot has a non-closed file inventory")
    if len(packets) != PILOT_LESSON_COUNT or [packet["lesson_id"] for packet in packets] != manifest["lesson_ids"]:
        raise ValueError("A1 pilot lesson inventory is not the declared ordered ten-lesson scope")
    if [packet["sequence"] for packet in packets] != list(range(1, PILOT_LESSON_COUNT + 1)):
        raise ValueError("A1 pilot packet sequence is invalid")
    _validate_duplicate_text(packets)
    return manifest


def build_review_template(*, pilot_dir: Path, population_path: Path, blueprint_path: Path, output_path: Path) -> Path:
    """Write a blank, explicitly incomplete review template for a verified pilot."""

    manifest = verify_pilot(pilot_dir, population_path, blueprint_path)
    template = {
        "schema_version": "1.0",
        "record_type": "a1_pilot_review",
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
    validate_instance(template, "a1-pilot-review")
    if output_path.exists():
        raise FileExistsError(f"refusing to overwrite A1 review template: {output_path}")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_bytes(_canonical_bytes(template) + b"\n")
    return output_path


def summarize_review(*, pilot_dir: Path, population_path: Path, blueprint_path: Path, review_path: Path, output_path: Path) -> Path:
    """Validate one user/AI development review and write its deterministic summary."""

    manifest = verify_pilot(pilot_dir, population_path, blueprint_path)
    review = load_document(review_path)
    validate_instance(review, "a1-pilot-review")
    _assert_no_claims(review)
    if review["pilot_id"] != manifest["pilot_id"] or review["manifest_sha256"] != manifest["manifest_sha256"]:
        raise ValueError("review does not bind this A1 pilot manifest")
    for reviewer in review["reviewers"]:
        if reviewer["reviewer_type"] == "AI" and (not reviewer.get("provider") or not reviewer.get("model")):
            raise ValueError("AI review provenance requires provider and model facts or UNKNOWN")
    for entry in review["lessons"]:
        if any(result == "NOT_RUN" for result in entry["dimensions"].values()):
            raise ValueError("a completed A1 pilot review cannot contain NOT_RUN dimensions")
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
        "record_type": "a1_pilot_review_summary",
        "pilot_id": manifest["pilot_id"],
        "manifest_sha256": manifest["manifest_sha256"],
        "review_sha256": sha256_json(review),
        "content_status": "UNREVIEWED",
        "systemic_findings": systemic,
        "isolated_findings": isolated,
        "next_action": "FIX_GENERATOR" if systemic else "REPLACE_LOCAL_PACKETS" if isolated else "NO_BLOCKING_FINDINGS",
    }
    validate_instance(summary, "a1-pilot-review-summary")
    if output_path.exists():
        raise FileExistsError(f"refusing to overwrite A1 review summary: {output_path}")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_bytes(_canonical_bytes(summary) + b"\n")
    return output_path
