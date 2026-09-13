"""Algorithm-first, cross-level QA for the six immutable full-corpus runs."""

from __future__ import annotations

import hashlib
import json
import unicodedata
from collections import defaultdict
from pathlib import Path
from statistics import median
from typing import Any, Callable, Mapping, Sequence

from english_master.a1_full.service import verify_full_a1
from english_master.a2_full.service import verify_full_a2
from english_master.b1_full.service import verify_full_b1
from english_master.b2_full.service import verify_full_b2
from english_master.c1_full.service import verify_full_c1
from english_master.c2_full.service import verify_full_c2
from english_master.lesson_generation.canonical import sha256_json
from english_master.schema_validation import load_document, validate_instance

LEVEL_ORDER = ("A1", "A2", "B1", "B2", "C1", "C2")
RULESET_VERSION = "CROSS_LEVEL_QA_V2"
SAMPLE_ALGORITHM_VERSION = "CROSS_LEVEL_QA_FLAGGED_REGION_SAMPLE_V2"
NO_API_MODE = "NO_API_DETERMINISTIC_FLAGGED_REGION_MANIFEST"
MODALITIES = frozenset(("listening", "speaking", "pronunciation", "writing"))
_NEAR_LIMIT = 250
_TOPIC_NEAR_LIMIT = 100

Verifier = Callable[[Path, Path, Path, Path, Path], tuple[dict[str, Any], list[dict[str, Any]]]]
_VERIFIERS: dict[str, Verifier] = {
    "A1": verify_full_a1, "A2": verify_full_a2, "B1": verify_full_b1,
    "B2": verify_full_b2, "C1": verify_full_c1, "C2": verify_full_c2,
}


def _canonical_bytes(value: Any) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")


def _write_no_overwrite(path: Path, value: Mapping[str, Any]) -> None:
    if path.exists():
        raise FileExistsError(f"refusing to overwrite cross-level QA artifact: {path}")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(_canonical_bytes(value) + b"\n")


def _without_hash(value: Mapping[str, Any], field: str) -> dict[str, Any]:
    copy = dict(value)
    copy.pop(field, None)
    return copy


def _normal(value: str) -> str:
    return " ".join(unicodedata.normalize("NFKC", value).casefold().split())


def _region_id(code: str, lesson_id: str | None, location: str, message: str) -> str:
    payload = {"code": code, "lesson_id": lesson_id, "location": location, "message": message}
    return "clq-region-" + hashlib.sha256(_canonical_bytes(payload)).hexdigest()


def _finding(code: str, severity: str, lesson_id: str | None, location: str, message: str) -> dict[str, Any]:
    return {"code": code, "severity": severity, "lesson_id": lesson_id, "location": location, "message": message, "region_id": _region_id(code, lesson_id, location, message)}


def build_request(levels: Sequence[Mapping[str, str]], output_path: Path | None = None) -> dict[str, Any]:
    """Create a hash-bound six-level input request without accessing any corpus."""
    request = {
        "schema_version": "2.0", "record_type": "cross_level_qa_request",
        "ruleset_version": RULESET_VERSION, "content_status": "UNREVIEWED",
        "levels": [dict(level) for level in levels],
    }
    request["request_sha256"] = sha256_json(request)
    validate_instance(request, "cross-level-qa-request-v2")
    _validate_request(request)
    if output_path is not None:
        _write_no_overwrite(output_path, request)
    return request


def _validate_request(request: Mapping[str, Any]) -> None:
    if request["request_sha256"] != sha256_json(_without_hash(request, "request_sha256")):
        raise ValueError("cross-level QA request hash mismatch")
    actual = [row["level"] for row in request["levels"]]
    if actual != list(LEVEL_ORDER):
        raise ValueError(f"cross-level QA levels must be exactly ordered {list(LEVEL_ORDER)!r}")


def _load_request(path: Path) -> dict[str, Any]:
    request = load_document(path)
    validate_instance(request, "cross-level-qa-request-v2")
    _validate_request(request)
    return request


def _verify_inputs(request: Mapping[str, Any]) -> tuple[list[dict[str, Any]], list[dict[str, Any]], str, dict[str, Mapping[str, Any]]]:
    all_packets: list[dict[str, Any]] = []
    level_inputs: list[dict[str, Any]] = []
    population_hashes: list[str] = []
    population_nodes: dict[str, Mapping[str, Any]] = {}
    for level_index, row in enumerate(request["levels"]):
        paths = {key: Path(row[key]) for key in ("run_dir", "population_path", "blueprint_path", "allocation_path", "content_manifest_path")}
        manifest, packets = _VERIFIERS[row["level"]](paths["run_dir"], paths["population_path"], paths["blueprint_path"], paths["allocation_path"], paths["content_manifest_path"])
        if len(packets) != 50:
            raise ValueError(f"{row['level']} verification did not return exactly fifty packets")
        source_hash = manifest["source"].get("population_sha256")
        population = load_document(paths["population_path"])
        calculated_hash = sha256_json(population)
        if source_hash != calculated_hash:
            raise ValueError(f"{row['level']} manifest M15 population hash binding drift")
        population_hashes.append(calculated_hash)
        for node in population["nodes"]:
            existing = population_nodes.setdefault(node["id"], node)
            if existing != node:
                raise ValueError(f"M15 node definition drift for {node['id']}")
        allocation = load_document(paths["allocation_path"])
        targets = {target["id"]: target for target in allocation["targets"]}
        if len(targets) != len(allocation["targets"]):
            raise ValueError(f"{row['level']} allocation has duplicate target IDs")
        level_inputs.append({"level": row["level"], "run_id": manifest["run_id"], "run_manifest_sha256": manifest["manifest_sha256"], "packet_count": len(packets)})
        for packet in packets:
            copy = dict(packet)
            copy["_cross_level"] = row["level"]
            copy["_targets"] = {target_id: targets[target_id] for target_id in copy["objective_target_ids"]}
            copy["_global_sequence"] = level_index * 50 + int(packet["sequence"])
            all_packets.append(copy)
    if len(all_packets) != 300:
        raise ValueError("cross-level QA requires exactly 300 verified packets")
    if len(set(population_hashes)) != 1:
        raise ValueError("cross-level QA requires one common M15 population hash")
    return level_inputs, all_packets, population_hashes[0], population_nodes


def _target_links(packets: Sequence[Mapping[str, Any]]) -> list[dict[str, Any]]:
    """Require explicit grammar/vocabulary introduction and learner-facing linkage."""
    findings: list[dict[str, Any]] = []
    for packet in packets:
        lesson_id = packet["lesson_id"]
        declared = set(packet["objective_target_ids"])
        usages = {row["target_id"]: row["usage"] for row in packet["target_usage"]}
        outline_nodes = {item["node_id"] for item in packet["outline_targets"]}
        linked: list[tuple[str, Sequence[str]]] = []
        linked.extend((f"{lesson_id}/section/{section['id']}", section["target_ids"]) for section in packet["content_sections"])
        linked.extend((f"{lesson_id}/exercise/{exercise['id']}", exercise["target_ids"]) for exercise in packet["exercises"])
        linked.extend((f"{lesson_id}/practice/{modality}", protocol["target_ids"]) for modality, protocol in packet["practice"].items())
        linked_targets = {target_id for _, target_ids in linked for target_id in target_ids}
        if declared != set(usages):
            findings.append(_finding("CLQ_DECLARED_TARGET_LINKAGE", "BLOCKING", lesson_id, f"{lesson_id}/objective_target_ids", "Declared objective targets do not equal allocated target usage."))
        for location, target_ids in linked:
            if not set(target_ids).issubset(declared):
                findings.append(_finding("CLQ_DECLARED_TARGET_LINKAGE", "BLOCKING", lesson_id, location, "Learner-facing component links a target not declared by the packet."))
        for target_id, target in packet["_targets"].items():
            dimension = target["dimension"]
            if dimension not in {"grammar", "vocabulary_senses"} or usages.get(target_id) != "INTRODUCE":
                continue
            if target["broad_target_id"] not in outline_nodes:
                findings.append(_finding("CLQ_GRAMMAR_VOCAB_INTRODUCE_LINKAGE", "BLOCKING", lesson_id, f"{lesson_id}/target/{target_id}", f"Introduced {dimension} target is not linked to its declared M15 outline node."))
            if target_id not in linked_targets:
                findings.append(_finding("CLQ_GRAMMAR_VOCAB_INTRODUCE_LINKAGE", "BLOCKING", lesson_id, f"{lesson_id}/target/{target_id}", f"Introduced {dimension} target has no learner-facing section, exercise, or practice linkage."))
    return findings


def _global_target_introduction_order(packets: Sequence[Mapping[str, Any]]) -> list[dict[str, Any]]:
    """Ensure every target use follows a globally earlier INTRODUCE event."""
    findings: list[dict[str, Any]] = []
    introduced_at: dict[str, int] = {}
    for packet in packets:
        lesson_id = packet["lesson_id"]
        for usage in packet["target_usage"]:
            target_id, action = usage["target_id"], usage["usage"]
            if action == "INTRODUCE":
                if target_id in introduced_at:
                    findings.append(_finding("CLQ_GLOBAL_TARGET_INTRODUCTION_ORDER", "BLOCKING", lesson_id, f"{lesson_id}/target/{target_id}", "Target is introduced more than once in the global sequence."))
                introduced_at[target_id] = packet["_global_sequence"]
            elif target_id not in introduced_at or introduced_at[target_id] >= packet["_global_sequence"]:
                findings.append(_finding("CLQ_GLOBAL_TARGET_INTRODUCTION_ORDER", "BLOCKING", lesson_id, f"{lesson_id}/target/{target_id}", f"{action} use occurs before a global INTRODUCE event."))
    return findings


def _global_order(packets: Sequence[Mapping[str, Any]], nodes: Mapping[str, Mapping[str, Any]]) -> list[dict[str, Any]]:
    findings: list[dict[str, Any]] = []
    lesson_position = {packet["lesson_id"]: packet["_global_sequence"] for packet in packets}
    for packet in packets:
        for prerequisite in packet["prerequisite_lesson_ids"]:
            if prerequisite not in lesson_position or lesson_position[prerequisite] >= packet["_global_sequence"]:
                findings.append(_finding("CLQ_GLOBAL_PREREQUISITE_ORDER", "BLOCKING", packet["lesson_id"], f"{packet['lesson_id']}/prerequisite_lesson_ids", f"Prerequisite {prerequisite!r} is missing or does not precede this packet globally."))
    first_node: dict[str, int] = {}
    node_owner: dict[str, str] = {}
    for packet in packets:
        for target in packet["outline_targets"]:
            node_id = target["node_id"]
            first_node.setdefault(node_id, packet["_global_sequence"])
            node_owner.setdefault(node_id, packet["lesson_id"])
    for node_id, position in first_node.items():
        node = nodes.get(node_id)
        if node is None:
            findings.append(_finding("CLQ_M15_NODE_ORDER", "BLOCKING", node_owner[node_id], f"{node_owner[node_id]}/outline_targets", f"M15 node {node_id!r} is not in the common population."))
            continue
        for prerequisite in node["prerequisites"]:
            prerequisite_position = first_node.get(prerequisite)
            if prerequisite_position is None or prerequisite_position > position:
                findings.append(_finding("CLQ_M15_NODE_ORDER", "BLOCKING", node_owner[node_id], f"{node_owner[node_id]}/outline_targets/{node_id}", f"M15 prerequisite {prerequisite!r} is absent or not introduced earlier."))
    return findings


def _answer_projection(exercise: Mapping[str, Any]) -> list[str]:
    """Return learner-visible answer-key projections without volatile metadata."""
    values: list[str] = []
    for key in ("correct_answer", "acceptable_answers", "correct_order", "pairs"):
        value = exercise.get(key)
        if isinstance(value, str):
            values.append(value)
        elif isinstance(value, list):
            values.extend(item for item in value if isinstance(item, str))
            if value and not all(isinstance(item, str) for item in value):
                values.append(json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")))
    for question in exercise.get("questions", []):
        for key in ("acceptable_answers", "correct_answer", "answer"):
            value = question.get(key)
            if isinstance(value, str):
                values.append(value)
            elif isinstance(value, list):
                values.extend(item for item in value if isinstance(item, str))
    return values


def _learner_entries(packets: Sequence[Mapping[str, Any]]) -> list[tuple[str, str, str, str]]:
    entries: list[tuple[str, str, str, str]] = []
    for packet in packets:
        lesson_id = packet["lesson_id"]
        entries.append((lesson_id, f"{lesson_id}/title", "title", packet["title"]))
        entries.extend((lesson_id, f"{lesson_id}/objective/{index}", "objective", objective) for index, objective in enumerate(packet["objectives"], 1))
        for section in packet["content_sections"]:
            entries.append((lesson_id, f"{lesson_id}/section/{section['id']}/body", "section", section["body"]))
        for exercise in packet["exercises"]:
            entries.append((lesson_id, f"{lesson_id}/exercise/{exercise['id']}/prompt", "exercise_prompt", exercise["prompt"]))
            entries.extend((lesson_id, f"{lesson_id}/exercise/{exercise['id']}/answer/{index}", "answer", answer) for index, answer in enumerate(_answer_projection(exercise), 1))
            if "stimulus" in exercise:
                entries.append((lesson_id, f"{lesson_id}/exercise/{exercise['id']}/stimulus", "exercise_stimulus", exercise["stimulus"]))
            for index, question in enumerate(exercise.get("questions", []), 1):
                question_id = question.get("id", question.get("question_id", str(index)))
                question_text = question.get("prompt", question.get("question", ""))
                if question_text:
                    entries.append((lesson_id, f"{lesson_id}/exercise/{exercise['id']}/question/{question_id}", "exercise_question", question_text))
        for modality, protocol in packet["practice"].items():
            entries.append((lesson_id, f"{lesson_id}/practice/{modality}/instruction", f"practice_{modality}", protocol["instruction"]))
            if "transcript" in protocol:
                entries.append((lesson_id, f"{lesson_id}/practice/{modality}/transcript", f"practice_{modality}", protocol["transcript"]))
    return entries


def _duplicates(entries: Sequence[tuple[str, str, str, str]]) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    exact: list[dict[str, Any]] = []
    grouped: dict[tuple[str, str], list[tuple[str, str]]] = defaultdict(list)
    for lesson_id, location, kind, text in entries:
        normalized = _normal(text)
        if normalized:
            grouped[(kind, normalized)].append((lesson_id, location))
    for (kind, _), occurrences in sorted(grouped.items()):
        if len(occurrences) > 1:
            joined = ", ".join(location for _, location in sorted(occurrences))
            for lesson_id, location in sorted(occurrences):
                exact.append(_finding("CLQ_EXACT_LEARNER_TEXT_DUPLICATE", "FLAG", lesson_id, location, f"Normalized exact {kind} duplicate also occurs at: {joined}"))
    near: list[dict[str, Any]] = []
    by_kind: dict[str, list[tuple[str, str, str]]] = defaultdict(list)
    for lesson_id, location, kind, text in entries:
        normalized = _normal(text)
        if len(normalized) >= 48:
            by_kind[kind].append((lesson_id, location, normalized))
    for kind, values in sorted(by_kind.items()):
        shingles = []
        for _, _, value in values:
            tokens = value.split()
            shingles.append({" ".join(tokens[index:index + 3]) for index in range(len(tokens) - 2)})
        buckets: dict[str, list[int]] = defaultdict(list)
        for index, shingle_set in enumerate(shingles):
            for shingle in shingle_set:
                buckets[shingle].append(index)
        candidate_pairs: set[tuple[int, int]] = set()
        for indexes in buckets.values():
            if len(indexes) > 1:
                candidate_pairs.update((left, right) for offset, left in enumerate(indexes) for right in indexes[offset + 1:])
        for left, right in sorted(candidate_pairs):
            if len(near) >= _NEAR_LIMIT:
                return exact, near
            lesson_a, location_a, text_a = values[left]
            lesson_b, location_b, text_b = values[right]
            if lesson_a == lesson_b or text_a == text_b:
                continue
            union = shingles[left] | shingles[right]
            similarity = len(shingles[left] & shingles[right]) / len(union) if union else 0.0
            if similarity >= 0.84:
                near.append(_finding("CLQ_NEAR_LEARNER_TEXT_DUPLICATE", "FLAG", lesson_a, location_a, f"Near {kind} duplicate with {location_b}; 3-word-shingle Jaccard={similarity:.3f}."))
    return exact, near


def _topic_candidates(packets: Sequence[Mapping[str, Any]]) -> list[dict[str, Any]]:
    values = [(packet["_cross_level"], packet["lesson_id"], _normal(packet["topic"])) for packet in packets]
    groups: dict[str, list[tuple[str, str]]] = defaultdict(list)
    for level, lesson_id, topic in values:
        groups[topic].append((level, lesson_id))
    findings: list[dict[str, Any]] = []
    for topic, members in sorted(groups.items()):
        if len(members) > 1 and len({level for level, _ in members}) > 1:
            locations = ", ".join(f"{level}:{lesson_id}" for level, lesson_id in members)
            for level, lesson_id in members:
                findings.append(_finding("CLQ_TOPIC_CANDIDATE", "FLAG", lesson_id, f"{lesson_id}/topic", f"Cross-level topic candidate {topic!r}: {locations}"))
    near_count = 0
    for left, (level_a, lesson_a, topic_a) in enumerate(values):
        tokens_a = set(topic_a.split())
        if len(tokens_a) < 2:
            continue
        for level_b, lesson_b, topic_b in values[left + 1:]:
            if near_count >= _TOPIC_NEAR_LIMIT:
                return findings
            if level_a == level_b or topic_a == topic_b:
                continue
            tokens_b = set(topic_b.split())
            if len(tokens_b) < 2:
                continue
            similarity = len(tokens_a & tokens_b) / len(tokens_a | tokens_b)
            if similarity >= 0.5:
                findings.append(_finding("CLQ_NEAR_TOPIC_CANDIDATE", "FLAG", lesson_a, f"{lesson_a}/topic", f"Near cross-level topic candidate with {lesson_b}; token Jaccard={similarity:.3f}."))
                near_count += 1
    return findings


def _modality_checks(packets: Sequence[Mapping[str, Any]]) -> list[dict[str, Any]]:
    findings: list[dict[str, Any]] = []
    for packet in packets:
        lesson_id, practice, declared = packet["lesson_id"], packet["practice"], set(packet["objective_target_ids"])
        if set(practice) != MODALITIES:
            findings.append(_finding("CLQ_MODALITY_BOUNDARY_LINKAGE", "BLOCKING", lesson_id, f"{lesson_id}/practice", "Packet does not contain exactly the four required practice modalities."))
            continue
        for modality, protocol in practice.items():
            if not set(protocol["target_ids"]).issubset(declared):
                findings.append(_finding("CLQ_MODALITY_BOUNDARY_LINKAGE", "BLOCKING", lesson_id, f"{lesson_id}/practice/{modality}", "Practice protocol target linkage exceeds declared packet targets."))
        listening = practice["listening"]
        if listening.get("media_required") is not False or not any("transcript" in value.casefold() and "before" in value.casefold() for value in listening["constraints"]):
            findings.append(_finding("CLQ_MODALITY_BOUNDARY_LINKAGE", "BLOCKING", lesson_id, f"{lesson_id}/practice/listening", "Listening protocol violates the local transcript-only boundary."))
        if practice["pronunciation"].get("without_audio") != "NOT_ASSESSED":
            findings.append(_finding("CLQ_MODALITY_BOUNDARY_LINKAGE", "BLOCKING", lesson_id, f"{lesson_id}/practice/pronunciation", "Pronunciation protocol lacks the required no-audio fallback."))
        if practice["writing"].get("feedback_boundary") != "FEEDBACK_ONLY_NO_REPLACEMENT":
            findings.append(_finding("CLQ_MODALITY_BOUNDARY_LINKAGE", "BLOCKING", lesson_id, f"{lesson_id}/practice/writing", "Writing protocol exceeds the draft-first feedback-only boundary."))
    return findings


def _difficulty_jumps(packets: Sequence[Mapping[str, Any]]) -> list[dict[str, Any]]:
    metrics: dict[str, list[tuple[int, int, int]]] = defaultdict(list)
    for packet in packets:
        word_count = sum(len(_normal(section["body"]).split()) for section in packet["content_sections"])
        metrics[packet["_cross_level"]].append((word_count, len(packet["exercises"]), len(packet["objective_target_ids"])))
    findings: list[dict[str, Any]] = []
    previous: tuple[float, float, float] | None = None
    for level in LEVEL_ORDER:
        values = metrics[level]
        current = tuple(float(median([row[index] for row in values])) for index in range(3))
        if previous:
            for label, before, after in zip(("section_word_count", "exercise_count", "target_count"), previous, current, strict=True):
                if before and after / before >= 2.25:
                    first_lesson = next(packet["lesson_id"] for packet in packets if packet["_cross_level"] == level)
                    findings.append(_finding("CLQ_STRUCTURAL_DIFFICULTY_JUMP", "FLAG", first_lesson, f"{level}/median/{label}", f"Median {label} rises from {before:g} in the preceding level to {after:g} in {level} ({after / before:.2f}x)."))
        previous = current
    return findings


def run_qa(*, request_path: Path, output_path: Path | None = None) -> dict[str, Any]:
    """Verify six runs and produce a deterministic cross-level consistency report."""
    request = _load_request(request_path)
    level_inputs, packets, m15_hash, nodes = _verify_inputs(request)
    target_findings = _target_links(packets)
    topic_findings = _topic_candidates(packets)
    grouped = {
        "CLQ_DECLARED_TARGET_LINKAGE": [item for item in target_findings if item["code"] == "CLQ_DECLARED_TARGET_LINKAGE"],
        "CLQ_GRAMMAR_VOCAB_INTRODUCE_LINKAGE": [item for item in target_findings if item["code"] == "CLQ_GRAMMAR_VOCAB_INTRODUCE_LINKAGE"],
        "CLQ_GLOBAL_TARGET_INTRODUCTION_ORDER": _global_target_introduction_order(packets),
        "CLQ_GLOBAL_PREREQUISITE_ORDER": [],
        "CLQ_M15_NODE_ORDER": [],
        "CLQ_EXACT_LEARNER_TEXT_DUPLICATE": [],
        "CLQ_NEAR_LEARNER_TEXT_DUPLICATE": [],
        "CLQ_TOPIC_CANDIDATE": [item for item in topic_findings if item["code"] == "CLQ_TOPIC_CANDIDATE"],
        "CLQ_NEAR_TOPIC_CANDIDATE": [item for item in topic_findings if item["code"] == "CLQ_NEAR_TOPIC_CANDIDATE"],
        "CLQ_MODALITY_BOUNDARY_LINKAGE": _modality_checks(packets),
        "CLQ_STRUCTURAL_DIFFICULTY_JUMP": _difficulty_jumps(packets),
    }
    order_findings = _global_order(packets, nodes)
    grouped["CLQ_GLOBAL_PREREQUISITE_ORDER"] = [item for item in order_findings if item["code"] == "CLQ_GLOBAL_PREREQUISITE_ORDER"]
    grouped["CLQ_M15_NODE_ORDER"] = [item for item in order_findings if item["code"] == "CLQ_M15_NODE_ORDER"]
    exact, near = _duplicates(_learner_entries(packets))
    grouped["CLQ_EXACT_LEARNER_TEXT_DUPLICATE"] = exact
    grouped["CLQ_NEAR_LEARNER_TEXT_DUPLICATE"] = near
    lesson_levels = {packet["lesson_id"]: packet["_cross_level"] for packet in packets}
    findings = [{**item, "level": lesson_levels.get(item["lesson_id"])} for item in sorted((item for values in grouped.values() for item in values), key=lambda item: (item["code"], item["lesson_id"] or "", item["location"], item["message"]))]
    checks = [{"code": code, "checked_count": len(packets), "finding_count": len(grouped[code]), "result": "FAIL" if any(item["severity"] == "BLOCKING" for item in grouped[code]) else ("FLAG" if grouped[code] else "PASS")} for code in sorted(grouped)]
    report = {
        "schema_version": "2.0", "record_type": "cross_level_qa_report", "ruleset_version": RULESET_VERSION,
        "content_status": "UNREVIEWED", "request_sha256": request["request_sha256"],
        "common_m15_population_sha256": m15_hash, "level_inputs": level_inputs, "lesson_count": len(packets),
        "checks": checks, "findings": findings,
        "result": "FAIL" if any(item["severity"] == "BLOCKING" for item in findings) else "PASS",
        "limitations": [
            "This deterministic consistency report does not establish linguistic correctness, pedagogical quality, CEFR endorsement, or learner outcomes.",
            "Flagged regions are candidates for later inspection, not defects, reviews, approvals, release authority, or provider evidence.",
            "The companion sample is a deterministic manifest only: it makes no API invocation and does not assess content.",
        ],
    }
    report["report_sha256"] = sha256_json(report)
    validate_instance(report, "cross-level-qa-report-v2")
    if output_path is not None:
        _write_no_overwrite(output_path, report)
    return report


def sample_flagged_regions(*, report_path: Path, seed: str, sample_size: int = 20, output_path: Path | None = None) -> dict[str, Any]:
    """Rank report findings deterministically; this function never invokes an AI provider."""
    if not 1 <= sample_size <= 50 or not seed or len(seed) > 128:
        raise ValueError("sample size must be 1..50 and seed must contain 1..128 characters")
    report = load_document(report_path)
    validate_instance(report, "cross-level-qa-report-v2")
    if report["report_sha256"] != sha256_json(_without_hash(report, "report_sha256")):
        raise ValueError("cross-level QA report hash mismatch")
    rankings = []
    for finding in report["findings"]:
        rank = hashlib.sha256(f"{report['report_sha256']}\0{seed}\0{SAMPLE_ALGORITHM_VERSION}\0{finding['region_id']}".encode("utf-8")).hexdigest()
        level = finding.get("level") or "A1"
        rankings.append({"region_id": finding["region_id"], "finding_family": finding["code"], "affected_level": level, "lesson_id": finding["lesson_id"], "location": finding["location"], "severity": finding["severity"], "rank_sha256": rank})
    rankings.sort(key=lambda item: (item["severity"] != "BLOCKING", item["rank_sha256"], item["region_id"]))
    strata_map: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
    for item in rankings:
        strata_map[(item["finding_family"], item["affected_level"])].append(item)
    if sample_size < len(strata_map):
        raise ValueError(f"sample size {sample_size} is below finding-strata count {len(strata_map)}")
    selected_items: list[dict[str, Any]] = [members[0] for _, members in sorted(strata_map.items())]
    selected_ids = {item["region_id"] for item in selected_items}
    for item in rankings:
        if len(selected_ids) >= sample_size:
            break
        selected_ids.add(item["region_id"])
    rankings = [{**item, "selected": item["region_id"] in selected_ids} for item in rankings]
    strata = [{"finding_family": family, "affected_level": level, "candidate_count": len(members), "selected_count": int(any(item["region_id"] in selected_ids for item in members))} for (family, level), members in sorted(strata_map.items())]
    sample = {"schema_version": "2.0", "record_type": "cross_level_qa_sample", "content_status": "UNREVIEWED", "report_sha256": report["report_sha256"], "algorithm_version": SAMPLE_ALGORITHM_VERSION, "execution_mode": NO_API_MODE, "seed": seed, "sample_size": len(selected_ids), "strata": strata, "rankings": rankings, "selected_region_ids": [item["region_id"] for item in rankings if item["selected"]]}
    sample["sample_sha256"] = sha256_json(sample)
    validate_instance(sample, "cross-level-qa-sample-v2")
    if output_path is not None:
        _write_no_overwrite(output_path, sample)
    return sample


def verify_report(*, request_path: Path, report_path: Path) -> dict[str, Any]:
    """Re-run every bound source verifier and validate an existing report."""
    request = _load_request(request_path)
    report = load_document(report_path)
    validate_instance(report, "cross-level-qa-report-v2")
    if report["report_sha256"] != sha256_json(_without_hash(report, "report_sha256")):
        raise ValueError("cross-level QA report hash mismatch")
    level_inputs, _, population_hash, _ = _verify_inputs(request)
    if report["request_sha256"] != request["request_sha256"]:
        raise ValueError("cross-level QA report request binding drift")
    if report["common_m15_population_sha256"] != population_hash:
        raise ValueError("cross-level QA report population binding drift")
    if report["level_inputs"] != level_inputs:
        raise ValueError("cross-level QA report level input binding drift")
    return {"result": "PASS", "report_sha256": report["report_sha256"], "request_sha256": request["request_sha256"], "lesson_count": report["lesson_count"]}
