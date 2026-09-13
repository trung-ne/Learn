"""Deterministic assessment assembly over the immutable A1-C2 full corpora."""

from __future__ import annotations

import hashlib
import json
import os
import shutil
import tempfile
import unicodedata
from collections import defaultdict
from pathlib import Path
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
TIER_ORDER = ("A1.1", "A1.2", "A2.1", "A2.2", "B1.1", "B1.2", "B2.1", "B2.2", "C1.1", "C1.2", "C2.1", "C2.2")
POLICY_VERSION = "ASSESSMENT_MASTERY_V1"
ELIGIBLE_TYPES = frozenset(("multiple_choice", "fill_blank", "matching", "ordering", "reading", "listening"))
Verifier = Callable[[Path, Path, Path, Path, Path], tuple[dict[str, Any], list[dict[str, Any]]]]
_VERIFIERS: dict[str, Verifier] = {
    "A1": verify_full_a1, "A2": verify_full_a2, "B1": verify_full_b1,
    "B2": verify_full_b2, "C1": verify_full_c1, "C2": verify_full_c2,
}
_PATH_KEYS = ("run_dir", "population_path", "blueprint_path", "allocation_path", "content_manifest_path")


def _canonical_bytes(value: Any) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")


def _without_hash(value: Mapping[str, Any], field: str) -> dict[str, Any]:
    result = dict(value)
    result.pop(field, None)
    return result


def _write_no_overwrite(path: Path, value: Mapping[str, Any]) -> None:
    if path.exists():
        raise FileExistsError(f"refusing to overwrite assessment artifact: {path}")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(_canonical_bytes(value) + b"\n")


def build_request(levels: Sequence[Mapping[str, str]], output_path: Path | None = None) -> dict[str, Any]:
    """Build a hash-bound request for exactly the six ordered full-corpus runs."""
    request = {
        "schema_version": "1.0", "record_type": "assessment_build_request",
        "policy_version": POLICY_VERSION, "content_status": "UNREVIEWED",
        "levels": [dict(row) for row in levels],
    }
    request["request_sha256"] = sha256_json(request)
    validate_instance(request, "assessment-build-request-v1")
    _validate_request(request)
    if output_path is not None:
        _write_no_overwrite(output_path, request)
    return request


def _validate_request(request: Mapping[str, Any]) -> None:
    if request["request_sha256"] != sha256_json(_without_hash(request, "request_sha256")):
        raise ValueError("assessment build request hash mismatch")
    if [row["level"] for row in request["levels"]] != list(LEVEL_ORDER):
        raise ValueError(f"assessment levels must be exactly ordered {list(LEVEL_ORDER)!r}")


def _load_request(path: Path) -> dict[str, Any]:
    request = load_document(path)
    validate_instance(request, "assessment-build-request-v1")
    _validate_request(request)
    return request


def _verify_sources(request: Mapping[str, Any]) -> tuple[list[dict[str, Any]], list[dict[str, Any]], str]:
    packets: list[dict[str, Any]] = []
    inputs: list[dict[str, Any]] = []
    population_hashes: set[str] = set()
    for level_index, row in enumerate(request["levels"]):
        level = row["level"]
        paths = {key: Path(row[key]) for key in _PATH_KEYS}
        manifest, level_packets = _VERIFIERS[level](
            paths["run_dir"], paths["population_path"], paths["blueprint_path"],
            paths["allocation_path"], paths["content_manifest_path"],
        )
        if len(level_packets) != 50:
            raise ValueError(f"{level} source verifier did not return exactly fifty packets")
        population = load_document(paths["population_path"])
        population_hash = sha256_json(population)
        if manifest["source"].get("population_sha256") != population_hash:
            raise ValueError(f"{level} source population binding drift")
        population_hashes.add(population_hash)
        allocation = load_document(paths["allocation_path"])
        targets = {target["id"]: target for target in allocation["targets"]}
        if len(targets) != len(allocation["targets"]):
            raise ValueError(f"{level} allocation contains duplicate target IDs")
        blueprint = load_document(paths["blueprint_path"])
        inputs.append({
            "level": level, "run_id": manifest["run_id"],
            "run_manifest_sha256": manifest["manifest_sha256"],
            "blueprint_sha256": sha256_json(blueprint), "packet_count": len(level_packets),
        })
        for packet in level_packets:
            if packet.get("content_status") != "UNREVIEWED":
                raise ValueError(f"source packet {packet.get('packet_id')} must remain UNREVIEWED")
            copy = dict(packet)
            copy["_level"] = level
            copy["_level_index"] = level_index
            copy["_targets"] = targets
            copy["_blueprint"] = blueprint
            packets.append(copy)
    if len(packets) != 300:
        raise ValueError("assessment build requires exactly 300 verified packets")
    if len(population_hashes) != 1:
        raise ValueError("assessment build requires one common M15 population hash")
    return inputs, packets, next(iter(population_hashes))


def _concept_ids(target_ids: Sequence[str], targets: Mapping[str, Mapping[str, Any]]) -> list[str]:
    concepts: set[str] = set()
    for target_id in target_ids:
        target = targets.get(target_id)
        if target is None:
            raise ValueError(f"objective item references unknown allocation target {target_id!r}")
        concept_id = target.get("broad_target_id")
        if not isinstance(concept_id, str) or not concept_id:
            raise ValueError(f"allocation target {target_id!r} has no broad concept mapping")
        concepts.add(concept_id)
    if not concepts:
        raise ValueError("objective item has no broad concept mapping")
    return sorted(concepts)


def _target_dimensions(target_ids: Sequence[str], targets: Mapping[str, Mapping[str, Any]]) -> list[str]:
    dimensions: set[str] = set()
    for target_id in target_ids:
        target = targets.get(target_id)
        if target is None:
            raise ValueError(f"objective item references unknown allocation target {target_id!r}")
        dimension = target.get("dimension")
        if not isinstance(dimension, str) or not dimension:
            raise ValueError(f"allocation target {target_id!r} has no dimension")
        dimensions.add(dimension)
    return sorted(dimensions)


def _atomic_item(packet: Mapping[str, Any], exercise: Mapping[str, Any], question: Mapping[str, Any] | None, question_index: int | None) -> dict[str, Any]:
    item_type = exercise["type"]
    suffix = f"-q{question_index:02d}" if question_index is not None else ""
    item_id = f"item-{packet['packet_id']}-{exercise['id']}{suffix}"
    source = {
        "level": packet["_level"], "tier": packet["tier"], "unit_id": packet["unit_id"],
        "lesson_id": packet["lesson_id"], "packet_id": packet["packet_id"],
        "packet_sha256": packet["packet_sha256"], "exercise_id": exercise["id"],
    }
    if question_index is not None:
        source["question_index"] = question_index
    item: dict[str, Any] = {
        "item_id": item_id, "item_type": item_type, "media_required": False,
        "source": source, "target_ids": list(exercise["target_ids"]),
        "target_dimensions": _target_dimensions(exercise["target_ids"], packet["_targets"]),
        "concept_ids": _concept_ids(exercise["target_ids"], packet["_targets"]),
    }
    if question is not None:
        item.update({"prompt": exercise["prompt"], "stimulus": exercise["stimulus"], "question": question["question"], "answer_contract": {"acceptable_answers": list(question["acceptable_answers"])}})
    elif item_type == "multiple_choice":
        item.update({"prompt": exercise["prompt"], "options": list(exercise["options"]), "answer_contract": {"correct_answer": exercise["correct_answer"]}})
    elif item_type == "fill_blank":
        item.update({"prompt": exercise["prompt"], "answer_contract": {"acceptable_answers": list(exercise["acceptable_answers"])}})
    elif item_type == "matching":
        item.update({"prompt": exercise["prompt"], "answer_contract": {"pairs": [dict(pair) for pair in exercise["pairs"]]}})
    elif item_type == "ordering":
        item.update({"prompt": exercise["prompt"], "items": list(exercise["items"]), "answer_contract": {"correct_order": list(exercise["correct_order"])}})
    else:
        raise ValueError(f"unsupported atomic objective type {item_type!r}")
    item["item_sha256"] = sha256_json(item)
    return item


def _project_items(packet: Mapping[str, Any]) -> list[dict[str, Any]]:
    items: list[dict[str, Any]] = []
    for exercise in packet["exercises"]:
        item_type = exercise["type"]
        if item_type not in ELIGIBLE_TYPES or exercise.get("media_required") is not False:
            continue
        if item_type in {"reading", "listening"}:
            for index, question in enumerate(exercise.get("questions", []), 1):
                items.append(_atomic_item(packet, exercise, question, index))
        else:
            items.append(_atomic_item(packet, exercise, None, None))
    if not items:
        raise ValueError(f"source lesson {packet['lesson_id']} has no eligible objective item")
    return items


def _rank(item: Mapping[str, Any], assessment_id: str) -> str:
    return hashlib.sha256(f"{POLICY_VERSION}\0{assessment_id}\0{item['item_sha256']}".encode()).hexdigest()


def _select(items: Sequence[Mapping[str, Any]], assessment_id: str, count: int, *, coverage_key: str) -> list[dict[str, Any]]:
    if len(items) < count:
        raise ValueError(f"assessment {assessment_id} has only {len(items)} eligible items; {count} required")
    ranked = sorted((dict(item) for item in items), key=lambda item: (_rank(item, assessment_id), item["item_id"]))
    groups: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for item in ranked:
        if coverage_key == "lesson_id":
            groups[item["source"]["lesson_id"]].append(item)
        elif coverage_key == "unit_id":
            groups[item["source"]["unit_id"]].append(item)
        else:
            raise ValueError(f"unsupported coverage key {coverage_key}")
    selected: list[dict[str, Any]] = []
    used: set[str] = set()
    for group in sorted(groups):
        candidate = groups[group][0]
        selected.append(candidate)
        used.add(candidate["item_id"])
    if len(selected) > count:
        raise ValueError(f"assessment {assessment_id} cannot cover {len(selected)} groups with {count} items")
    # Prefer a new objective type and a new mapped dimension before pure hash fill.
    while len(selected) < count:
        selected_types = {item["item_type"] for item in selected}
        selected_concepts = {concept for item in selected for concept in item["concept_ids"]}
        selected_dimensions = {dimension for item in selected for dimension in item["target_dimensions"]}
        remaining = [item for item in ranked if item["item_id"] not in used]
        remaining.sort(key=lambda item: (
            item["item_type"] in selected_types,
            not bool(set(item["target_dimensions"]) - selected_dimensions),
            not bool(set(item["concept_ids"]) - selected_concepts),
            _rank(item, assessment_id), item["item_id"],
        ))
        candidate = remaining[0]
        selected.append(candidate)
        used.add(candidate["item_id"])
    return selected


def _package(assessment_id: str, assessment_type: str, scope: Mapping[str, Any], items: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    package = {
        "schema_version": "1.0", "record_type": "assessment_package",
        "assessment_id": assessment_id, "assessment_type": assessment_type,
        "policy_version": POLICY_VERSION, "content_status": "UNREVIEWED",
        "scope": dict(scope), "items": [dict(item) for item in items],
    }
    package["package_sha256"] = sha256_json(package)
    validate_instance(package, "assessment-package-v1")
    return package


def _unit_outlines(level: str, blueprint: Mapping[str, Any]) -> list[dict[str, Any]]:
    if level == "A1":
        return [{
            "id": row["id"], "unit_id": row["placement_after_unit_id"], "tier": row["tier"],
            "assessed_lesson_ids": row["assessed_lesson_ids"], "target_dimensions": row["target_dimensions"],
        } for row in blueprint["assessments"] if row["kind"] == "unit_check"]
    return [{
        "id": row["id"], "unit_id": row["unit_id"], "tier": row["tier"],
        "assessed_lesson_ids": row["assessed_lesson_ids"], "target_dimensions": row["target_dimensions"],
    } for row in blueprint["unit_tests"]]


def _build_packages(packets: Sequence[Mapping[str, Any]]) -> list[dict[str, Any]]:
    all_items: dict[str, list[dict[str, Any]]] = {}
    packages: list[dict[str, Any]] = []
    for packet in packets:
        items = _project_items(packet)
        all_items[packet["lesson_id"]] = items
        packages.append(_package(
            f"lesson-quiz-{packet['lesson_id']}", "LESSON_QUIZ",
            {"levels": [packet["_level"]], "tiers": [packet["tier"]], "unit_ids": [packet["unit_id"]], "lesson_ids": [packet["lesson_id"]]}, items,
        ))
    by_level = {level: [packet for packet in packets if packet["_level"] == level] for level in LEVEL_ORDER}
    for level in LEVEL_ORDER:
        level_packets = by_level[level]
        blueprint = level_packets[0]["_blueprint"]
        outlines = _unit_outlines(level, blueprint)
        if len(outlines) != 10:
            raise ValueError(f"{level} blueprint must supply exactly ten unit-test outlines")
        packet_by_lesson = {packet["lesson_id"]: packet for packet in level_packets}
        for outline in outlines:
            if len(outline["assessed_lesson_ids"]) != 5 or any(lesson not in packet_by_lesson for lesson in outline["assessed_lesson_ids"]):
                raise ValueError(f"unit-test outline {outline['id']} has invalid assessed lesson scope")
            candidates = [item for lesson in outline["assessed_lesson_ids"] for item in all_items[lesson]]
            assessment_id = f"unit-test-{outline['unit_id']}"
            selected = _select(candidates, assessment_id, 10, coverage_key="lesson_id")
            packages.append(_package(assessment_id, "UNIT_TEST", {
                "levels": [level], "tiers": [outline["tier"]], "unit_ids": [outline["unit_id"]],
                "lesson_ids": list(outline["assessed_lesson_ids"]), "outline_assessment_id": outline["id"],
                "target_dimensions": list(outline["target_dimensions"]),
            }, selected))
        candidates = [item for packet in level_packets for item in all_items[packet["lesson_id"]]]
        level_id = f"level-test-{level.lower()}"
        selected = _select(candidates, level_id, 20, coverage_key="unit_id")
        packages.append(_package(level_id, "LEVEL_TEST", {
            "levels": [level], "tiers": [f"{level}.1", f"{level}.2"],
            "unit_ids": sorted({packet["unit_id"] for packet in level_packets}),
            "lesson_ids": [packet["lesson_id"] for packet in level_packets],
            "target_dimensions": sorted({dimension for item in candidates for dimension in item["target_dimensions"]}),
        }, selected))
    placement_items: list[dict[str, Any]] = []
    for tier in TIER_ORDER:
        candidates = [item for packet in packets if packet["tier"] == tier for item in all_items[packet["lesson_id"]]]
        tier_id = f"placement-{tier.lower()}"
        ranked = sorted(candidates, key=lambda item: (_rank(item, tier_id), item["item_id"]))
        first = ranked[0]
        second = next((item for item in ranked[1:] if item["source"]["lesson_id"] != first["source"]["lesson_id"]), None)
        if second is None:
            raise ValueError(f"placement tier {tier} cannot select two distinct lessons")
        placement_items.extend((first, second))
    packages.append(_package("placement-a1-c2", "PLACEMENT", {
        "levels": list(LEVEL_ORDER), "tiers": list(TIER_ORDER),
        "unit_ids": sorted({packet["unit_id"] for packet in packets}),
        "lesson_ids": [packet["lesson_id"] for packet in packets], "items_per_tier": 2,
        "passing_correct_per_tier": 2, "output_field": "suggested_start_tier",
    }, placement_items))
    counts = defaultdict(int)
    for package in packages:
        counts[package["assessment_type"]] += 1
    expected = {"LESSON_QUIZ": 300, "UNIT_TEST": 60, "LEVEL_TEST": 6, "PLACEMENT": 1}
    if dict(counts) != expected:
        raise ValueError(f"assessment package inventory mismatch: {dict(counts)!r}")
    return packages


def _expected_run(request: Mapping[str, Any]) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    source_inputs, packets, population_hash = _verify_sources(request)
    packages = _build_packages(packets)
    package_inventory = [{
        "assessment_id": package["assessment_id"], "assessment_type": package["assessment_type"],
        "path": f"packages/{package['assessment_id']}.json", "package_sha256": package["package_sha256"],
        "item_count": len(package["items"]),
    } for package in packages]
    run_basis = {"request_sha256": request["request_sha256"], "policy_version": POLICY_VERSION, "package_inventory": package_inventory}
    run_id = "assessment_" + sha256_json(run_basis)
    manifest = {
        "schema_version": "1.0", "record_type": "assessment_run_manifest", "run_id": run_id,
        "policy_version": POLICY_VERSION, "content_status": "UNREVIEWED",
        "request_sha256": request["request_sha256"], "common_m15_population_sha256": population_hash,
        "source_inputs": source_inputs,
        "counts": {"lesson_quizzes": 300, "unit_tests": 60, "level_tests": 6, "placement_packages": 1, "packages": 367},
        "package_inventory": package_inventory,
        "limitations": [
            "Packages project existing objective no-media items and remain UNREVIEWED.",
            "Automatic scores do not assess speaking, writing, pronunciation, pedagogical quality, learner proficiency, or CEFR certification.",
            "Placement suggested_start_tier is a fixed offline heuristic, not a validated diagnostic or endorsement.",
        ],
    }
    manifest["manifest_sha256"] = sha256_json(manifest)
    validate_instance(manifest, "assessment-run-manifest-v1")
    return manifest, packages


def build_run(*, request_path: Path, output_root: Path) -> dict[str, Any]:
    """Reverify all sources and atomically publish one immutable assessment run."""
    request = _load_request(request_path)
    manifest, packages = _expected_run(request)
    final_dir = output_root / manifest["run_id"]
    if final_dir.exists():
        raise FileExistsError(f"refusing to overwrite assessment run: {final_dir}")
    output_root.mkdir(parents=True, exist_ok=True)
    temporary = Path(tempfile.mkdtemp(prefix=f".{manifest['run_id']}.", dir=output_root))
    try:
        (temporary / "packages").mkdir()
        for package in packages:
            (temporary / "packages" / f"{package['assessment_id']}.json").write_bytes(_canonical_bytes(package) + b"\n")
        (temporary / "manifest.json").write_bytes(_canonical_bytes(manifest) + b"\n")
        os.replace(temporary, final_dir)
    except BaseException:
        shutil.rmtree(temporary, ignore_errors=True)
        raise
    return manifest


def verify_run(*, request_path: Path, run_dir: Path) -> dict[str, Any]:
    """Reconstruct expected packages and reject any source, inventory, or payload drift."""
    request = _load_request(request_path)
    expected_manifest, expected_packages = _expected_run(request)
    actual_manifest = load_document(run_dir / "manifest.json")
    validate_instance(actual_manifest, "assessment-run-manifest-v1")
    if actual_manifest != expected_manifest or run_dir.name != expected_manifest["run_id"]:
        raise ValueError("assessment run manifest does not match deterministic reconstruction")
    expected_paths = {"manifest.json"} | {row["path"] for row in expected_manifest["package_inventory"]}
    actual_paths = {path.relative_to(run_dir).as_posix() for path in run_dir.rglob("*") if path.is_file()}
    if actual_paths != expected_paths:
        raise ValueError("assessment run file inventory is not closed")
    by_id = {package["assessment_id"]: package for package in expected_packages}
    for row in expected_manifest["package_inventory"]:
        actual = load_document(run_dir / row["path"])
        validate_instance(actual, "assessment-package-v1")
        if actual != by_id[row["assessment_id"]]:
            raise ValueError(f"assessment package reconstruction mismatch: {row['assessment_id']}")
    return {"result": "PASS", "run_id": actual_manifest["run_id"], "manifest_sha256": actual_manifest["manifest_sha256"], "package_count": 367}
