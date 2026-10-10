"""Hash-bound, offline consistency checks for the Full A1-C2 corpus and M15 KG.

This module deliberately checks declared structure and bindings.  It does not judge
linguistic correctness, pedagogy, or CEFR suitability.
"""
from __future__ import annotations

import hashlib
import json
import unicodedata
from collections import defaultdict
from pathlib import Path
from typing import Any, Mapping, Sequence

from english_master.cross_level_qa.service import LEVEL_ORDER, _verify_inputs
from english_master.knowledge_graph.service import validate_population
from english_master.lesson_generation.canonical import sha256_json
from english_master.schema_validation import load_document, repository_root, validate_instance

RULESET_VERSION = "CONTENT_KG_QUALITY_V1"
MAX_DUPLICATE_FINDINGS = 250


def _canonical_bytes(value: Any) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")


def _write_no_overwrite(path: Path, value: Mapping[str, Any]) -> None:
    if path.exists():
        raise FileExistsError(f"refusing to overwrite Content/KG quality artifact: {path}")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(_canonical_bytes(value) + b"\n")


def _without_hash(value: Mapping[str, Any], field: str) -> dict[str, Any]:
    result = dict(value)
    result.pop(field, None)
    return result


def _normal(value: str) -> str:
    return " ".join(unicodedata.normalize("NFKC", value).casefold().split())


def _finding(
    code: str,
    severity: str,
    disposition: str,
    *,
    level: str | None = None,
    lesson_id: str | None = None,
    node_id: str | None = None,
    location: str,
    message: str,
) -> dict[str, Any]:
    identity = {
        "code": code,
        "severity": severity,
        "disposition": disposition,
        "level": level,
        "lesson_id": lesson_id,
        "node_id": node_id,
        "location": location,
        "message": message,
    }
    return {**identity, "finding_id": "ckq-" + hashlib.sha256(_canonical_bytes(identity)).hexdigest()}


def _validate_request(request: Mapping[str, Any]) -> None:
    validate_instance(dict(request), "content-kg-quality-request-v1")
    if request["request_sha256"] != sha256_json(_without_hash(request, "request_sha256")):
        raise ValueError("Content/KG quality request hash mismatch")
    levels = [row["level"] for row in request["levels"]]
    if levels != list(LEVEL_ORDER):
        raise ValueError(f"Content/KG quality levels must be exactly ordered {list(LEVEL_ORDER)!r}")


def build_request(levels: Sequence[Mapping[str, str]], *, web_validation_scope: Sequence[str] = (), output_path: Path | None = None) -> dict[str, Any]:
    """Create a closed source-path request without reading the source corpus."""
    request = {
        "schema_version": "1.0",
        "record_type": "content_kg_quality_request",
        "ruleset_version": RULESET_VERSION,
        "content_status": "UNREVIEWED",
        "levels": [dict(level) for level in levels],
        "web_validation_scope": sorted(web_validation_scope),
    }
    request["request_sha256"] = sha256_json(request)
    _validate_request(request)
    if output_path is not None:
        _write_no_overwrite(output_path, request)
    return request


def _load_request(path: Path) -> dict[str, Any]:
    request = load_document(path)
    _validate_request(request)
    return request


def _cycle_nodes(nodes: Mapping[str, Mapping[str, Any]], allowed: set[str]) -> set[str]:
    state: dict[str, int] = {}
    cyclic: set[str] = set()

    def visit(node_id: str, trail: list[str]) -> None:
        marker = state.get(node_id, 0)
        if marker == 1:
            cyclic.update(trail[trail.index(node_id):])
            return
        if marker == 2:
            return
        state[node_id] = 1
        for prerequisite in nodes[node_id].get("prerequisites", []):
            if prerequisite in allowed:
                visit(prerequisite, [*trail, prerequisite])
        state[node_id] = 2

    for node_id in sorted(allowed):
        visit(node_id, [node_id])
    return cyclic


def _packet_links(packet: Mapping[str, Any]) -> set[str]:
    linked: set[str] = set()
    for section in packet["content_sections"]:
        linked.update(section.get("target_ids", ()))
    for exercise in packet["exercises"]:
        linked.update(exercise.get("target_ids", ()))
    for protocol in packet["practice"].values():
        linked.update(protocol.get("target_ids", ()))
    return linked


def _native_exercise_findings(packet: Mapping[str, Any], level: str) -> list[dict[str, Any]]:
    findings: list[dict[str, Any]] = []
    for exercise in packet["exercises"]:
        location = f"{packet['lesson_id']}/exercise/{exercise['id']}"
        kind = exercise["type"]
        bad = False
        if exercise.get("media_required") is not False:
            findings.append(_finding("CKQ_REQUIRED_MEDIA", "BLOCKING", "DEFECT", level=level, lesson_id=packet["lesson_id"], location=location, message="Exercise requires media outside the current permitted no-media packet boundary."))
        if kind == "multiple_choice" and exercise.get("correct_answer") not in exercise.get("options", []):
            bad = True
        elif kind == "matching":
            pairs = exercise.get("pairs", [])
            bad = len({pair.get("left") for pair in pairs}) != len(pairs) or len({pair.get("right") for pair in pairs}) != len(pairs)
        elif kind == "ordering":
            bad = sorted(exercise.get("items", [])) != sorted(exercise.get("correct_order", []))
        elif kind in {"reading", "listening"}:
            questions = exercise.get("questions", [])
            bad = not questions or any(not question.get("acceptable_answers") for question in questions)
        if bad:
            findings.append(_finding("CKQ_EXERCISE_ANSWER", "BLOCKING", "DEFECT", level=level, lesson_id=packet["lesson_id"], location=location, message=f"{kind} has an invalid deterministic answer contract."))
    return findings


def _duplicates(packets: Sequence[Mapping[str, Any]]) -> list[dict[str, Any]]:
    entries: dict[str, list[tuple[str, str, str]]] = defaultdict(list)
    for packet in packets:
        level, lesson_id = packet["_quality_level"], packet["lesson_id"]
        values: list[tuple[str, str]] = [("title", packet["title"])]
        values.extend((f"section/{section['id']}", section["body"]) for section in packet["content_sections"])
        values.extend((f"exercise/{exercise['id']}/prompt", exercise["prompt"]) for exercise in packet["exercises"])
        for location, text in values:
            normal = _normal(text)
            if normal:
                entries[normal].append((level, lesson_id, location))
    findings: list[dict[str, Any]] = []
    for normal, occurrences in sorted(entries.items()):
        if len(occurrences) < 2:
            continue
        first = occurrences[0]
        for level, lesson_id, location in occurrences[1:]:
            findings.append(_finding("CKQ_EXACT_LEARNER_TEXT_DUPLICATE", "FLAG", "CANDIDATE", level=level, lesson_id=lesson_id, location=location, message=f"Normalized learner-facing text duplicates {first[1]}:{first[2]}."))
            if len(findings) == MAX_DUPLICATE_FINDINGS:
                return findings
    return findings


def _web_lane_findings(scope: str) -> list[dict[str, Any]]:
    """Check supplied lexical identities without treating a web lane as KG authority."""
    directory = repository_root() / ("curriculum/web-vocabulary/v1" if scope == "vocabulary" else "curriculum/web-dictionary/v1")
    records: list[tuple[Path, Mapping[str, Any]]] = []
    for path in sorted(directory.glob("*.json")):
        document = load_document(path)
        for record in document.get("records", []):
            if isinstance(record, Mapping):
                records.append((path, record))
    findings: list[dict[str, Any]] = []
    identities: dict[tuple[str, str, str, int], tuple[Path, str]] = {}
    required_example_count = 0
    for path, record in records:
        record_id = str(record.get("id", "<unknown>"))
        lemma = str(record.get("lemma", record.get("headword", "")))
        language = str(record.get("language", ""))
        part_of_speech = str(record.get("part_of_speech", ""))
        sense_number = record.get("sense_number", record.get("senseNumber"))
        tier = str(record.get("tier", ""))
        band = str(record.get("band", ""))
        location = f"{path.relative_to(repository_root()).as_posix()}/records/{record_id}"
        if not tier.startswith(f"{band}."):
            findings.append(_finding("CKQ_DECLARED_TIER_CONSISTENCY", "BLOCKING", "DEFECT", location=location, message="Lexical record tier does not belong to its declared band."))
        examples = record.get("examples")
        if isinstance(examples, list):
            required_example_count += 1
            if not examples or any(not isinstance(example, str) or not example.strip() for example in examples):
                findings.append(_finding("CKQ_MISSING_EXAMPLE", "BLOCKING", "DEFECT", location=location, message="Lexical record declares examples but supplies no usable example."))
        if not isinstance(sense_number, int):
            continue
        identity = (language, _normal(lemma), part_of_speech, sense_number)
        existing = identities.get(identity)
        if existing is not None:
            findings.append(_finding("CKQ_DUPLICATE_VOCABULARY_SENSE", "BLOCKING", "DEFECT", location=location, message=f"Lexical sense identity duplicates {existing[1]} in {existing[0].relative_to(repository_root()).as_posix()}."))
        else:
            identities[identity] = (path, record_id)
    if records and not required_example_count:
        findings.append(_finding("CKQ_EXAMPLE_AVAILABILITY", "INFO", "UNAVAILABLE", location=f"web/{scope}", message="The explicitly scoped lexical lane has no typed examples to validate."))
    return findings


def _evaluate(
    request: Mapping[str, Any],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], str, list[dict[str, Any]]]:
    levels, packets, population_hash, population_nodes = _verify_inputs(request)
    population_path = Path(request["levels"][0]["population_path"])
    population = load_document(population_path)
    validate_population(population)
    findings: list[dict[str, Any]] = []
    checks: dict[str, list[dict[str, Any]]] = defaultdict(list)

    grammar_ids = {node_id for node_id, node in population_nodes.items() if node["dimension"] == "grammar"}
    for node_id in sorted(_cycle_nodes(population_nodes, grammar_ids)):
        checks["CKQ_GRAMMAR_DEPENDENCY_CYCLE"].append(_finding("CKQ_GRAMMAR_DEPENDENCY_CYCLE", "BLOCKING", "DEFECT", node_id=node_id, location=f"m15/{node_id}", message="Grammar-only M15 dependency projection contains a cycle."))

    introduced: dict[str, tuple[int, str, str]] = {}
    used_nodes: set[str] = set()
    lesson_sequence: dict[str, int] = {}
    for global_sequence, packet in enumerate(packets, start=1):
        level = packet["_cross_level"]
        packet["_quality_level"] = level
        lesson_id = packet["lesson_id"]
        lesson_sequence[lesson_id] = global_sequence
        declared = set(packet["objective_target_ids"])
        linked = _packet_links(packet)
        for target in packet["outline_targets"]:
            node_id = target["node_id"]
            used_nodes.add(node_id)
            node = population_nodes.get(node_id)
            if node is None:
                checks["CKQ_BROKEN_KG_LINK"].append(_finding("CKQ_BROKEN_KG_LINK", "BLOCKING", "DEFECT", level=level, lesson_id=lesson_id, node_id=node_id, location=f"{lesson_id}/outline_targets", message="Packet outline target does not resolve in M15."))
            elif node["tier"] != packet["tier"] or node["dimension"] != target["dimension"]:
                checks["CKQ_DECLARED_TIER_CONSISTENCY"].append(_finding("CKQ_DECLARED_TIER_CONSISTENCY", "BLOCKING", "DEFECT", level=level, lesson_id=lesson_id, node_id=node_id, location=f"{lesson_id}/outline_targets", message="Packet outline target tier or dimension disagrees with M15."))
        for target_id in declared:
            target = packet["_targets"].get(target_id)
            if target is None:
                checks["CKQ_TARGET_LINKAGE"].append(_finding("CKQ_TARGET_LINKAGE", "BLOCKING", "DEFECT", level=level, lesson_id=lesson_id, location=f"{lesson_id}/objective_target_ids", message="Declared target does not resolve in the verified allocation."))
                continue
            node_id = target["broad_target_id"]
            used_nodes.add(node_id)
            if target["tier"] != packet["tier"]:
                checks["CKQ_DECLARED_TIER_CONSISTENCY"].append(_finding("CKQ_DECLARED_TIER_CONSISTENCY", "BLOCKING", "DEFECT", level=level, lesson_id=lesson_id, node_id=node_id, location=f"{lesson_id}/target/{target_id}", message="Allocation target tier disagrees with its packet tier."))
            if target_id not in linked:
                checks["CKQ_TARGET_LINKAGE"].append(_finding("CKQ_TARGET_LINKAGE", "BLOCKING", "DEFECT", level=level, lesson_id=lesson_id, node_id=node_id, location=f"{lesson_id}/target/{target_id}", message="Declared target has no learner-facing section, exercise, or protocol linkage."))
            if packet["target_usage"] and next((row for row in packet["target_usage"] if row["target_id"] == target_id), {}).get("usage") == "INTRODUCE":
                if target_id in introduced:
                    checks["CKQ_TARGET_LINKAGE"].append(_finding("CKQ_TARGET_LINKAGE", "BLOCKING", "DEFECT", level=level, lesson_id=lesson_id, node_id=node_id, location=f"{lesson_id}/target/{target_id}", message="Allocated target is introduced more than once."))
                introduced[target_id] = (global_sequence, level, lesson_id)
        for prerequisite in packet["prerequisite_lesson_ids"]:
            prior = lesson_sequence.get(prerequisite)
            if prior is None or prior >= global_sequence:
                checks["CKQ_LESSON_PREREQUISITE"].append(_finding("CKQ_LESSON_PREREQUISITE", "BLOCKING", "DEFECT", level=level, lesson_id=lesson_id, location=f"{lesson_id}/prerequisite_lesson_ids", message=f"Lesson prerequisite {prerequisite!r} is missing or not earlier in global order."))
        checks["CKQ_EXERCISE_ANSWER"].extend(_native_exercise_findings(packet, level))
        listening = packet["practice"]["listening"]
        if listening.get("media_required") is False:
            checks["CKQ_MEDIA_AVAILABILITY"].append(_finding("CKQ_MEDIA_AVAILABILITY", "INFO", "EXPECTED", level=level, lesson_id=lesson_id, location=f"{lesson_id}/practice/listening", message="Listening protocol is explicitly transcript-only and does not require an audio asset."))

    for node_id, node in sorted(population_nodes.items()):
        if node_id in used_nodes:
            continue
        if not node["prerequisites"]:
            continue
        checks["CKQ_ORPHAN_KNOWLEDGE"].append(_finding("CKQ_ORPHAN_KNOWLEDGE", "FLAG", "CANDIDATE", node_id=node_id, location=f"m15/{node_id}", message="Non-root M15 planning node has no verified Full-corpus allocation route."))
    checks["CKQ_EXACT_LEARNER_TEXT_DUPLICATE"].extend(_duplicates(packets))
    checks["CKQ_EXAMPLE_AVAILABILITY"].append(_finding("CKQ_EXAMPLE_AVAILABILITY", "INFO", "UNAVAILABLE", location="full-packets", message="Legacy Full packets do not declare typed example requirements; prose is not inferred to be an example contract."))
    for scope in request["web_validation_scope"]:
        lane_findings = _web_lane_findings(scope)
        checks["CKQ_DUPLICATE_VOCABULARY_SENSE"].extend(
            item for item in lane_findings if item["code"] == "CKQ_DUPLICATE_VOCABULARY_SENSE"
        )
        checks["CKQ_DECLARED_TIER_CONSISTENCY"].extend(
            item for item in lane_findings if item["code"] == "CKQ_DECLARED_TIER_CONSISTENCY"
        )
        checks["CKQ_MISSING_EXAMPLE"].extend(
            item for item in lane_findings if item["code"] == "CKQ_MISSING_EXAMPLE"
        )
        checks["CKQ_EXAMPLE_AVAILABILITY"].extend(
            item for item in lane_findings if item["code"] == "CKQ_EXAMPLE_AVAILABILITY"
        )
        checks["CKQ_WEB_LANE_SCOPE"].append(_finding("CKQ_WEB_LANE_SCOPE", "INFO", "EXPECTED", location=f"web/{scope}", message=f"The {scope} lexical lane was explicitly inspected as an independent learner-facing inventory."))

    all_findings = sorted((finding for group in checks.values() for finding in group), key=lambda item: (item["code"], item["level"] or "", item["lesson_id"] or "", item["node_id"] or "", item["location"], item["finding_id"]))
    check_codes = (
        "CKQ_BROKEN_KG_LINK", "CKQ_GRAMMAR_DEPENDENCY_CYCLE", "CKQ_LESSON_PREREQUISITE",
        "CKQ_TARGET_LINKAGE", "CKQ_ORPHAN_KNOWLEDGE", "CKQ_DECLARED_TIER_CONSISTENCY",
        "CKQ_EXACT_LEARNER_TEXT_DUPLICATE", "CKQ_DUPLICATE_VOCABULARY_SENSE", "CKQ_MISSING_EXAMPLE",
        "CKQ_EXAMPLE_AVAILABILITY", "CKQ_MEDIA_AVAILABILITY",
        "CKQ_EXERCISE_ANSWER", "CKQ_WEB_LANE_SCOPE",
    )
    summaries = []
    for code in check_codes:
        rows = checks[code]
        summaries.append({"code": code, "checked_count": len(packets) if code != "CKQ_BROKEN_KG_LINK" else len(population_nodes), "finding_count": len(rows), "result": "FAIL" if any(row["severity"] == "BLOCKING" for row in rows) else "FLAG" if any(row["severity"] == "FLAG" for row in rows) else "INFO" if rows else "PASS"})
    return levels, all_findings, population_hash, summaries


def run_quality(*, request_path: Path, output_path: Path | None = None) -> dict[str, Any]:
    request = _load_request(request_path)
    level_inputs, findings, population_hash, checks = _evaluate(request)
    if any(finding["severity"] == "BLOCKING" for finding in findings):
        result = "FAIL"
    elif any(finding["severity"] == "FLAG" for finding in findings):
        result = "PASS_WITH_FLAGS"
    else:
        result = "PASS"
    report = {
        "schema_version": "1.0", "record_type": "content_kg_quality_report", "ruleset_version": RULESET_VERSION,
        "content_status": "UNREVIEWED", "request_sha256": request["request_sha256"],
        "common_m15_population_sha256": population_hash, "level_inputs": level_inputs, "lesson_count": 300,
        "checks": checks, "findings": findings, "result": result,
        "limitations": [
            "This deterministic report checks declared repository structure and bindings only.",
            "It does not establish linguistic correctness, pedagogical quality, CEFR suitability, learner outcomes, approval, release, or provider behavior.",
            "Legacy packets without typed example requirements are reported as unavailable rather than inferred defects.",
        ],
    }
    report["report_sha256"] = sha256_json(report)
    validate_instance(report, "content-kg-quality-report-v1")
    if output_path is not None:
        _write_no_overwrite(output_path, report)
    return report


def verify_report(*, request_path: Path, report_path: Path) -> dict[str, Any]:
    report = load_document(report_path)
    validate_instance(report, "content-kg-quality-report-v1")
    if report["report_sha256"] != sha256_json(_without_hash(report, "report_sha256")):
        raise ValueError("Content/KG quality report hash mismatch")
    rebuilt = run_quality(request_path=request_path)
    if rebuilt != report:
        raise ValueError("Content/KG quality report does not match independently reconstructed inputs")
    return report
