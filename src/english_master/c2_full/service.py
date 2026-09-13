"""Deterministic Full C2 construction, verification, audit, and sampling."""

from __future__ import annotations

import hashlib
import json
import re
import shutil
import unicodedata
from collections import defaultdict
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence

from english_master.c2_curriculum_blueprint import validate as validate_blueprint
from english_master.knowledge_graph.service import validate_population
from english_master.lesson_generation.canonical import sha256_json
from english_master.schema_validation import load_document, validate_instance

LESSON_COUNT = 50
UNIT_COUNT = 10
UNIT_LESSON_COUNT = 5
MODALITIES = ("listening", "speaking", "pronunciation", "writing")
EXERCISE_TYPES = {
    "multiple_choice", "fill_blank", "matching", "ordering",
    "reading", "listening", "speaking", "writing",
}
RULESET_VERSION = "C2_FULL_LIGHTWEIGHT_V2"
SAMPLE_POLICY_VERSION = "C2_FULL_SHA256_UNIT_STRATIFIED_V1"
_FORBIDDEN_CLAIM_KEYS = {
    "human_reviewed", "human_approved", "release_approved",
    "provider_authenticated", "provider_verified",
}


def _canonical_bytes(value: Any) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")


def _write_json(path: Path, value: Any) -> None:
    path.write_bytes(_canonical_bytes(value) + b"\n")


def _sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _normalized(value: str) -> str:
    return " ".join(unicodedata.normalize("NFKC", value).casefold().split())


def _without_hash(value: Mapping[str, Any], field: str) -> dict[str, Any]:
    copy = dict(value)
    copy.pop(field, None)
    return copy


def _assert_no_claims(value: Any) -> None:
    if isinstance(value, Mapping):
        found = _FORBIDDEN_CLAIM_KEYS.intersection(value)
        if found:
            raise ValueError(f"Full C2 records must not contain approval/provider claim fields: {sorted(found)!r}")
        for child in value.values():
            _assert_no_claims(child)
    elif isinstance(value, list):
        for child in value:
            _assert_no_claims(child)


def _ordered_sources(blueprint: Mapping[str, Any]) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    units = sorted(blueprint["units"], key=lambda unit: unit["sequence"])
    unit_order = {unit["id"]: index for index, unit in enumerate(units)}
    lessons = sorted(blueprint["lessons"], key=lambda lesson: (unit_order[lesson["unit_id"]], lesson["sequence"]))
    if len(units) != UNIT_COUNT or len(lessons) != LESSON_COUNT:
        raise ValueError("Full C2 requires the M16 ten-unit, fifty-lesson scope")
    if any(lesson["tier"] not in {"C2.1", "C2.2"} for lesson in lessons):
        raise ValueError("Full C2 source includes a non-C2 lesson")
    return units, lessons


def _acyclic_target_order(targets: Mapping[str, Mapping[str, Any]]) -> list[str]:
    state: dict[str, int] = {}
    order: list[str] = []

    def visit(target_id: str) -> None:
        marker = state.get(target_id, 0)
        if marker == 1:
            raise ValueError(f"cyclic Full C2 target prerequisites at {target_id}")
        if marker == 2:
            return
        state[target_id] = 1
        for prerequisite in targets[target_id]["prerequisites"]:
            if prerequisite not in targets:
                raise ValueError(f"unknown Full C2 target prerequisite: {prerequisite}")
            visit(prerequisite)
        state[target_id] = 2
        order.append(target_id)

    for target_id in targets:
        visit(target_id)
    return order


def _validate_allocation(
    allocation: Mapping[str, Any], population: Mapping[str, Any], blueprint: Mapping[str, Any]
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    validate_instance(allocation, "c2-full-allocation-v1")
    _assert_no_claims(allocation)
    if allocation["population_sha256"] != sha256_json(population):
        raise ValueError("Full C2 allocation population binding drift")
    if allocation["blueprint_sha256"] != sha256_json(blueprint):
        raise ValueError("Full C2 allocation blueprint binding drift")
    units, outlines = _ordered_sources(blueprint)
    broad_targets = {node["id"]: node for node in population["nodes"]}
    target_list = allocation["targets"]
    targets = {target["id"]: target for target in target_list}
    if len(targets) != len(target_list):
        raise ValueError("Full C2 granular target IDs must be unique")
    _acyclic_target_order(targets)
    for target in target_list:
        broad = broad_targets.get(target["broad_target_id"])
        if broad is None:
            raise ValueError(f"unknown broad M16 target binding: {target['broad_target_id']}")
        if broad["tier"] != target["tier"] or broad["dimension"] != target["dimension"]:
            raise ValueError(f"granular target tier/dimension drift: {target['id']}")
    rows = allocation["lessons"]
    if len({row["lesson_id"] for row in rows}) != LESSON_COUNT:
        raise ValueError("Full C2 allocation lesson IDs must be unique")
    if [row["sequence"] for row in rows] != list(range(1, LESSON_COUNT + 1)):
        raise ValueError("Full C2 allocation must use ordered global sequences 1 through 50")
    introduced_at: dict[str, int] = {}
    usages_by_lesson: dict[str, set[str]] = {}
    for row, outline in zip(rows, outlines, strict=True):
        if row["lesson_id"] != outline["id"]:
            raise ValueError(f"allocation order or lesson ID drift at {outline['id']}")
        if row["tier"] != outline["tier"] or row["unit_id"] != outline["unit_id"]:
            raise ValueError(f"allocation tier/unit drift for {outline['id']}")
        if row["lesson_kind"] != outline["lesson_kind"]:
            raise ValueError(f"allocation lesson kind drift for {outline['id']}")
        if row["prerequisite_lesson_ids"] != outline["prerequisite_lesson_ids"]:
            raise ValueError(f"allocation prerequisite drift for {outline['id']}")
        if not set(row["allowed_exercise_types"]).issubset(EXERCISE_TYPES):
            raise ValueError(f"unsupported exercise type allocation for {outline['id']}")
        usages = row["target_usage"]
        ids = [usage["target_id"] for usage in usages]
        if len(ids) != len(set(ids)):
            raise ValueError(f"duplicate target usage in {outline['id']}")
        outline_broad = {target["node_id"] for target in outline["targets"]}
        for usage in usages:
            target = targets.get(usage["target_id"])
            if target is None:
                raise ValueError(f"unknown allocated target {usage['target_id']}")
            if target["tier"] != row["tier"] or target["broad_target_id"] not in outline_broad:
                raise ValueError(f"target tier/scope jump in {outline['id']}: {target['id']}")
            if usage["usage"] == "INTRODUCE":
                if target["id"] in introduced_at:
                    raise ValueError(f"target introduced more than once: {target['id']}")
                for prerequisite in target["prerequisites"]:
                    if prerequisite not in introduced_at:
                        raise ValueError(f"target prerequisite not introduced before {target['id']}")
                introduced_at[target["id"]] = row["sequence"]
            elif target["id"] not in introduced_at:
                raise ValueError(f"{usage['usage']} target not previously introduced: {target['id']}")
        usages_by_lesson[row["lesson_id"]] = set(ids)
    if set(introduced_at) != set(targets):
        missing = sorted(set(targets) - set(introduced_at))
        raise ValueError(f"Full C2 targets must each be introduced exactly once: {missing!r}")
    return units, outlines


def _load_content(
    content_manifest_path: Path, allocation: Mapping[str, Any], source_units: Sequence[Mapping[str, Any]]
) -> tuple[dict[str, Any], list[dict[str, Any]], dict[str, str]]:
    manifest = load_document(content_manifest_path)
    validate_instance(manifest, "c2-full-content-manifest-v1")
    _assert_no_claims(manifest)
    if manifest["manifest_sha256"] != sha256_json(_without_hash(manifest, "manifest_sha256")):
        raise ValueError("Full C2 content manifest hash mismatch")
    if manifest["allocation_sha256"] != sha256_json(allocation):
        raise ValueError("Full C2 content manifest allocation binding drift")
    base = content_manifest_path.parent
    expected_paths = {"content-manifest.json"}
    content_lessons: list[dict[str, Any]] = []
    unit_hashes: dict[str, str] = {}
    for item, source_unit in zip(manifest["units"], source_units, strict=True):
        relative = item["path"]
        if not re.fullmatch(r"units/unit-\d{2}\.json", relative):
            raise ValueError(f"unsafe Full C2 content path: {relative}")
        if item["unit_id"] != source_unit["id"] or item["tier"] != source_unit["tier"]:
            raise ValueError(f"Full C2 content unit order/tier drift: {item['unit_id']}")
        path = base / relative
        if not path.is_file() or _sha256_file(path) != item["sha256"]:
            raise ValueError(f"Full C2 content unit hash mismatch: {relative}")
        expected_paths.add(relative)
        unit = load_document(path)
        validate_instance(unit, "c2-full-content-unit-v1")
        _assert_no_claims(unit)
        if unit["unit_id"] != item["unit_id"] or unit["tier"] != item["tier"]:
            raise ValueError(f"Full C2 content unit identity drift: {relative}")
        content_lessons.extend(unit["lessons"])
        unit_hashes[unit["unit_id"]] = item["sha256"]
    actual_paths = {path.relative_to(base).as_posix() for path in base.rglob("*") if path.is_file()}
    # Allocation, source snapshots, runs, reports, and samples are sibling artifacts,
    # while this manifest closes only itself and the complete units/ tree.
    actual_content_paths = {path for path in actual_paths if path == "content-manifest.json" or path.startswith("units/")}
    if actual_content_paths != expected_paths:
        raise ValueError("Full C2 content manifest inventory is not closed")
    return manifest, content_lessons, unit_hashes


def _answer_projection(exercise: Mapping[str, Any]) -> list[str]:
    exercise_type = exercise["type"]
    if exercise_type == "multiple_choice":
        return [exercise["correct_answer"]]
    if exercise_type == "fill_blank":
        return list(exercise["acceptable_answers"])
    if exercise_type == "matching":
        return [json.dumps(exercise["pairs"], ensure_ascii=False, sort_keys=True)]
    if exercise_type == "ordering":
        return [json.dumps(exercise["correct_order"], ensure_ascii=False)]
    if exercise_type in {"reading", "listening"}:
        return [answer for question in exercise["questions"] for answer in question["acceptable_answers"]]
    return []


def _validate_exercise(exercise: Mapping[str, Any], lesson_id: str) -> None:
    exercise_type = exercise["type"]
    keys = set(exercise)
    common = {"id", "type", "target_ids", "prompt", "media_required"}
    required: dict[str, set[str]] = {
        "multiple_choice": {"options", "correct_answer"},
        "fill_blank": {"acceptable_answers"},
        "matching": {"pairs"},
        "ordering": {"items", "correct_order"},
        "reading": {"stimulus", "questions"},
        "listening": {"stimulus", "questions"},
        "speaking": {"rubric"},
        "writing": {"rubric"},
    }
    allowed = common | required[exercise_type]
    if keys != allowed:
        raise ValueError(f"{lesson_id} exercise {exercise['id']} has invalid fields for {exercise_type}")
    if exercise["media_required"] is not False:
        raise ValueError(f"{lesson_id} exercise {exercise['id']} must not require media")
    if exercise_type == "multiple_choice" and exercise["correct_answer"] not in exercise["options"]:
        raise ValueError(f"{lesson_id} multiple-choice answer is not one of its options")
    if exercise_type == "fill_blank" and "____" not in exercise["prompt"]:
        raise ValueError(f"{lesson_id} fill-blank task must contain a visible blank")
    if exercise_type == "matching":
        left = [pair["left"] for pair in exercise["pairs"]]
        right = [pair["right"] for pair in exercise["pairs"]]
        if len(left) != len(set(left)) or len(right) != len(set(right)):
            raise ValueError(f"{lesson_id} matching pairs must be one-to-one")
    if exercise_type == "ordering" and sorted(exercise["items"]) != sorted(exercise["correct_order"]):
        raise ValueError(f"{lesson_id} ordering answer must be a permutation of the items")


def _validate_content(
    content_lessons: Sequence[Mapping[str, Any]], allocation: Mapping[str, Any], outlines: Sequence[Mapping[str, Any]]
) -> None:
    expected_ids = [row["lesson_id"] for row in allocation["lessons"]]
    actual_ids = [lesson["lesson_id"] for lesson in content_lessons]
    if actual_ids != expected_ids or len(set(actual_ids)) != LESSON_COUNT:
        raise ValueError("Full C2 content must match the ordered allocation exactly")
    for lesson, row, outline in zip(content_lessons, allocation["lessons"], outlines, strict=True):
        if lesson["lesson_id"] != outline["id"]:
            raise ValueError(f"Full C2 content/M16 lesson mismatch: {lesson['lesson_id']}")
        allocated_targets = {usage["target_id"] for usage in row["target_usage"]}
        if set(lesson["objective_target_ids"]) != allocated_targets:
            raise ValueError(f"objective targets do not equal allocated targets in {lesson['lesson_id']}")
        section_ids = [section["id"] for section in lesson["content_sections"]]
        exercise_ids = [exercise["id"] for exercise in lesson["exercises"]]
        if len(section_ids) != len(set(section_ids)) or len(exercise_ids) != len(set(exercise_ids)):
            raise ValueError(f"duplicate local content ID in {lesson['lesson_id']}")
        target_fields: Iterable[Sequence[str]] = (
            [target for section in lesson["content_sections"] for target in section["target_ids"]],
            [target for exercise in lesson["exercises"] for target in exercise["target_ids"]],
            [target for practice in lesson["practice"].values() for target in practice["target_ids"]],
        )
        if any(not set(target_ids).issubset(allocated_targets) for target_ids in target_fields):
            raise ValueError(f"content target scope drift in {lesson['lesson_id']}")
        allowed_types = set(row["allowed_exercise_types"])
        for exercise in lesson["exercises"]:
            if exercise["type"] not in allowed_types:
                raise ValueError(f"exercise type not allocated in {lesson['lesson_id']}: {exercise['type']}")
            _validate_exercise(exercise, lesson["lesson_id"])
        if set(lesson["practice"]) != set(MODALITIES):
            raise ValueError(f"{lesson['lesson_id']} must contain exactly four practice protocols")
        listening = lesson["practice"]["listening"]
        if listening["media_required"] is not False or not any("transcript" in item.casefold() and "before" in item.casefold() for item in listening["constraints"]):
            raise ValueError(f"{lesson['lesson_id']} listening protocol violates transcript-only privacy")
        if lesson["practice"]["pronunciation"]["without_audio"] != "NOT_ASSESSED":
            raise ValueError(f"{lesson['lesson_id']} pronunciation protocol lacks the audio fallback")
        if lesson["practice"]["writing"]["feedback_boundary"] != "FEEDBACK_ONLY_NO_REPLACEMENT":
            raise ValueError(f"{lesson['lesson_id']} writing protocol is not feedback-only")


def _packet(
    outline: Mapping[str, Any], row: Mapping[str, Any], lesson: Mapping[str, Any], source: Mapping[str, str], unit_hash: str
) -> dict[str, Any]:
    packet = {
        "schema_version": "1.0", "record_type": "c2_full_packet",
        "packet_id": f"c2full-packet-{row['sequence']:02d}",
        "lesson_id": row["lesson_id"], "tier": row["tier"], "unit_id": row["unit_id"], "sequence": row["sequence"], "lesson_kind": row["lesson_kind"],
        "topic": row["topic"], "language_focus": row["language_focus"],
        "outline_targets": outline["targets"], "prerequisite_lesson_ids": row["prerequisite_lesson_ids"],
        "target_usage": row["target_usage"], "allowed_exercise_types": row["allowed_exercise_types"],
        "title": lesson["title"], "duration_minutes": lesson["duration_minutes"],
        "objective_target_ids": lesson["objective_target_ids"], "objectives": lesson["objectives"],
        "content_sections": lesson["content_sections"], "exercises": lesson["exercises"], "practice": lesson["practice"],
        "content_status": "UNREVIEWED",
        "provenance": {"content_origin": "PROJECT_AUTHORED", **source, "content_unit_sha256": unit_hash},
    }
    packet["packet_sha256"] = sha256_json(packet)
    validate_instance(packet, "c2-full-packet-v1")
    _assert_no_claims(packet)
    return packet


def _load_sources(
    population_path: Path, blueprint_path: Path, allocation_path: Path, content_manifest_path: Path
) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any], dict[str, Any], list[dict[str, Any]], list[dict[str, Any]], dict[str, str]]:
    population = load_document(population_path)
    blueprint = load_document(blueprint_path)
    allocation = load_document(allocation_path)
    validate_population(population)
    validate_blueprint(blueprint, population)
    units, outlines = _validate_allocation(allocation, population, blueprint)
    content_manifest, content_lessons, unit_hashes = _load_content(content_manifest_path, allocation, units)
    _validate_content(content_lessons, allocation, outlines)
    return population, blueprint, allocation, content_manifest, outlines, content_lessons, unit_hashes


def build_full_c2(*, population_path: Path, blueprint_path: Path, allocation_path: Path, content_manifest_path: Path, output_root: Path, built_at: str) -> Path:
    """Build one atomic, no-overwrite run containing all fifty canonical packets."""
    population, blueprint, allocation, content_manifest, outlines, content_lessons, unit_hashes = _load_sources(population_path, blueprint_path, allocation_path, content_manifest_path)
    source = {"population_sha256": sha256_json(population), "blueprint_sha256": sha256_json(blueprint), "allocation_sha256": sha256_json(allocation), "content_manifest_sha256": sha256_json(content_manifest)}
    packets = [_packet(outline, row, lesson, source, unit_hashes[row["unit_id"]]) for outline, row, lesson in zip(outlines, allocation["lessons"], content_lessons, strict=True)]
    run_id = "c2full_" + hashlib.sha256(_canonical_bytes({"built_at": built_at, "source": source, "packet_hashes": [packet["packet_sha256"] for packet in packets]})).hexdigest()
    destination, temporary = output_root / run_id, output_root / f".{run_id}.tmp"
    if destination.exists() or temporary.exists():
        raise FileExistsError(f"refusing to overwrite Full C2 run or temporary path: {destination}")
    temporary.mkdir(parents=True)
    try:
        packet_dir = temporary / "packets"
        packet_dir.mkdir()
        inventory = []
        for packet in packets:
            relative = f"packets/{packet['packet_id']}.json"
            path = temporary / relative
            _write_json(path, packet)
            inventory.append({"path": relative, "sha256": _sha256_file(path)})
        manifest = {"schema_version": "1.0", "record_type": "c2_full_run_manifest", "run_id": run_id, "built_at": built_at, "content_status": "UNREVIEWED", "source": source, "lesson_ids": [packet["lesson_id"] for packet in packets], "inventory": inventory}
        manifest["manifest_sha256"] = sha256_json(manifest)
        validate_instance(manifest, "c2-full-run-manifest-v1")
        _write_json(temporary / "manifest.json", manifest)
        temporary.replace(destination)
    except BaseException:
        shutil.rmtree(temporary, ignore_errors=True)
        raise
    return destination


def verify_full_c2(run_dir: Path, population_path: Path, blueprint_path: Path, allocation_path: Path, content_manifest_path: Path) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    """Recompute source-derived packets and verify the run's closed inventory."""
    population, blueprint, allocation, content_manifest, outlines, content_lessons, unit_hashes = _load_sources(population_path, blueprint_path, allocation_path, content_manifest_path)
    manifest = load_document(run_dir / "manifest.json")
    validate_instance(manifest, "c2-full-run-manifest-v1")
    _assert_no_claims(manifest)
    if manifest["manifest_sha256"] != sha256_json(_without_hash(manifest, "manifest_sha256")):
        raise ValueError("Full C2 run manifest hash mismatch")
    source = {"population_sha256": sha256_json(population), "blueprint_sha256": sha256_json(blueprint), "allocation_sha256": sha256_json(allocation), "content_manifest_sha256": sha256_json(content_manifest)}
    if manifest["source"] != source:
        raise ValueError("Full C2 run source binding drift")
    expected_paths = {"manifest.json"}
    packets = []
    for item in manifest["inventory"]:
        relative = item["path"]
        if not re.fullmatch(r"packets/c2full-packet-\d{2}\.json", relative):
            raise ValueError(f"unsafe Full C2 run inventory path: {relative}")
        expected_paths.add(relative)
        path = run_dir / relative
        if not path.is_file() or _sha256_file(path) != item["sha256"]:
            raise ValueError(f"Full C2 run inventory hash mismatch: {relative}")
        packet = load_document(path)
        validate_instance(packet, "c2-full-packet-v1")
        _assert_no_claims(packet)
        if packet["packet_sha256"] != sha256_json(_without_hash(packet, "packet_sha256")):
            raise ValueError(f"Full C2 packet hash mismatch: {packet.get('packet_id')}")
        packets.append(packet)
    actual_paths = {path.relative_to(run_dir).as_posix() for path in run_dir.rglob("*") if path.is_file()}
    if actual_paths != expected_paths:
        raise ValueError("Full C2 run inventory is not closed")
    if len(packets) != LESSON_COUNT or [packet["lesson_id"] for packet in packets] != manifest["lesson_ids"]:
        raise ValueError("Full C2 run does not contain the declared ordered fifty lessons")
    for packet, outline, row, lesson in zip(packets, outlines, allocation["lessons"], content_lessons, strict=True):
        expected = _packet(outline, row, lesson, source, unit_hashes[row["unit_id"]])
        if packet != expected:
            raise ValueError(f"Full C2 source-derived packet drift: {packet['lesson_id']}")
    return manifest, packets


def _duplicates(entries: Iterable[tuple[str, str, str]], code: str) -> list[dict[str, Any]]:
    occurrences: dict[str, list[tuple[str, str]]] = defaultdict(list)
    for lesson_id, location, text in entries:
        normalized = _normalized(text)
        if normalized:
            occurrences[normalized].append((lesson_id, location))
    findings = []
    for locations in occurrences.values():
        if len(locations) > 1:
            joined = ", ".join(location for _, location in sorted(locations))
            for lesson_id, location in sorted(locations):
                findings.append({"code": code, "lesson_id": lesson_id, "location": location, "message": f"Normalized exact duplicate also occurs at: {joined}"})
    return findings


def _audit_findings(packets: Sequence[Mapping[str, Any]]) -> dict[str, list[dict[str, Any]]]:
    section_entries, prompt_entries, answer_entries, protocol_entries = [], [], [], []
    for packet in packets:
        lesson_id = packet["lesson_id"]
        for section in packet["content_sections"]:
            section_entries.append((lesson_id, f"{lesson_id}/section/{section['id']}", section["body"]))
        for exercise in packet["exercises"]:
            prompt_entries.append((lesson_id, f"{lesson_id}/exercise/{exercise['id']}/prompt", exercise["prompt"]))
            answer_entries.extend((lesson_id, f"{lesson_id}/exercise/{exercise['id']}/answer/{index}", answer) for index, answer in enumerate(_answer_projection(exercise), 1))
        for modality, protocol in packet["practice"].items():
            protocol_entries.append((lesson_id, f"{lesson_id}/practice/{modality}/instruction", protocol["instruction"]))
    return {
        "C2F_DUPLICATE_SECTION": _duplicates(section_entries, "C2F_DUPLICATE_SECTION"),
        "C2F_DUPLICATE_EXERCISE_PROMPT": _duplicates(prompt_entries, "C2F_DUPLICATE_EXERCISE_PROMPT"),
        "C2F_DUPLICATE_ANSWER": _duplicates(answer_entries, "C2F_DUPLICATE_ANSWER"),
        "C2F_DUPLICATE_PROTOCOL": _duplicates(protocol_entries, "C2F_DUPLICATE_PROTOCOL"),
    }


def audit_full_c2(*, run_dir: Path, population_path: Path, blueprint_path: Path, allocation_path: Path, content_manifest_path: Path, output_path: Path | None = None) -> dict[str, Any]:
    """Publish stable full-population consistency findings; never an approval claim."""
    manifest, packets = verify_full_c2(run_dir, population_path, blueprint_path, allocation_path, content_manifest_path)
    grouped = _audit_findings(packets)
    grouped.update({
        "C2F_REFERENCE_INTEGRITY": [], "C2F_TIER_SCOPE": [], "C2F_PREREQUISITE": [],
        "C2F_EXERCISE_CONTRACT": [], "C2F_MEDIA_BOUNDARY": [], "C2F_CLAIM_BOUNDARY": [],
    })
    findings = sorted((finding for values in grouped.values() for finding in values), key=lambda item: (item["code"], item["lesson_id"] or "", item["location"], item["message"]))
    checks = [{"code": code, "checked_count": len(packets), "finding_count": len(grouped[code]), "result": "PASS" if not grouped[code] else "FAIL"} for code in sorted(grouped)]
    report = {
        "schema_version": "1.0", "record_type": "c2_full_audit_report", "run_id": manifest["run_id"],
        "manifest_sha256": manifest["manifest_sha256"], "ruleset_version": RULESET_VERSION,
        "lesson_count": len(packets), "checks": checks, "findings": findings,
        "result": "PASS" if not findings else "FAIL",
        "limitations": [
            "This consistency audit does not establish prose-level linguistic correctness, pedagogical quality, or learner outcomes.",
            "It is not human review, approval, release authority, provider evidence, live AI execution, or real-media validation.",
        ],
    }
    report["report_sha256"] = sha256_json(report)
    validate_instance(report, "c2-full-audit-report-v1")
    if output_path is not None:
        if output_path.exists():
            raise FileExistsError(f"refusing to overwrite Full C2 audit report: {output_path}")
        output_path.parent.mkdir(parents=True, exist_ok=True)
        _write_json(output_path, report)
    return report


def sample_full_c2(*, run_dir: Path, audit_report_path: Path, population_path: Path, blueprint_path: Path, allocation_path: Path, content_manifest_path: Path, seed: str, sample_size: int = 12, output_path: Path | None = None) -> dict[str, Any]:
    """Create a SHA-256-ranked 10-unit-stratified sample from a passing audit."""
    if not 10 <= sample_size <= 15:
        raise ValueError("Full C2 sample size must be between 10 and 15")
    if not seed or len(seed) > 128:
        raise ValueError("Full C2 sample seed must contain 1 to 128 characters")
    manifest, packets = verify_full_c2(run_dir, population_path, blueprint_path, allocation_path, content_manifest_path)
    report = load_document(audit_report_path)
    validate_instance(report, "c2-full-audit-report-v1")
    if report["report_sha256"] != sha256_json(_without_hash(report, "report_sha256")):
        raise ValueError("Full C2 audit report hash mismatch")
    if report["result"] != "PASS":
        raise ValueError("Full C2 sampling requires a passing audit report")
    if report["run_id"] != manifest["run_id"] or report["manifest_sha256"] != manifest["manifest_sha256"]:
        raise ValueError("Full C2 audit report does not bind the verified run")
    rank = lambda lesson_id: hashlib.sha256(f"{report['report_sha256']}\0{seed}\0{SAMPLE_POLICY_VERSION}\0{lesson_id}".encode("utf-8")).hexdigest()
    ranked = [{"lesson_id": packet["lesson_id"], "unit_id": packet["unit_id"], "tier": packet["tier"], "rank_hash": rank(packet["lesson_id"])} for packet in packets]
    by_unit: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for item in ranked:
        by_unit[item["unit_id"]].append(item)
    selected_ids = {min(items, key=lambda item: (item["rank_hash"], item["lesson_id"]))["lesson_id"] for items in by_unit.values()}
    extras = sorted((item for item in ranked if item["lesson_id"] not in selected_ids), key=lambda item: (item["rank_hash"], item["lesson_id"]))[: sample_size - UNIT_COUNT]
    selected_ids.update(item["lesson_id"] for item in extras)
    sequence = {packet["lesson_id"]: packet["sequence"] for packet in packets}
    selected_ordered = sorted(selected_ids, key=sequence.__getitem__)
    rankings = [{**item, "selected": item["lesson_id"] in selected_ids} for item in sorted(ranked, key=lambda item: (item["rank_hash"], item["lesson_id"]))]
    sample = {
        "schema_version": "1.0", "record_type": "c2_full_sample_manifest", "run_id": manifest["run_id"],
        "run_manifest_sha256": manifest["manifest_sha256"], "audit_report_sha256": report["report_sha256"],
        "algorithm_version": SAMPLE_POLICY_VERSION, "seed": seed, "sample_size": sample_size,
        "input_hashes": manifest["source"], "rankings": rankings, "selected_lesson_ids": selected_ordered,
    }
    sample["sample_manifest_sha256"] = sha256_json(sample)
    validate_instance(sample, "c2-full-sample-manifest-v1")
    if output_path is not None:
        if output_path.exists():
            raise FileExistsError(f"refusing to overwrite Full C2 sample manifest: {output_path}")
        output_path.parent.mkdir(parents=True, exist_ok=True)
        _write_json(output_path, sample)
    return sample
