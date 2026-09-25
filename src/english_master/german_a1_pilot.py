"""Deterministic, offline German A1 ten-lesson pilot builder."""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import shutil
import unicodedata
from pathlib import Path
from typing import Any, Mapping, Sequence

from english_master.german_a1_blueprint import validate_blueprint
from english_master.german_bootstrap import validate_population
from english_master.lesson_generation.canonical import sha256_json
from english_master.schema_validation import load_document, validate_instance

_MODALITIES = {"listening", "speaking", "pronunciation", "writing"}
_FORBIDDEN = {"human_reviewed", "release_approved", "provider_authenticated", "network_used", "external_content_used"}


def _canonical_bytes(value: Any) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")


def _file_hash(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _normalized(value: str) -> str:
    return " ".join(unicodedata.normalize("NFKC", value).casefold().split())


def _no_forbidden_claims(value: Any) -> None:
    if isinstance(value, Mapping):
        forbidden = _FORBIDDEN.intersection(value)
        if forbidden:
            raise ValueError(f"German pilot must not contain claim fields: {sorted(forbidden)!r}")
        for child in value.values():
            _no_forbidden_claims(child)
    elif isinstance(value, list):
        for child in value:
            _no_forbidden_claims(child)


def _outlines(blueprint: Mapping[str, Any]) -> list[dict[str, Any]]:
    return [lesson for unit in sorted(blueprint["units"], key=lambda item: item["sequence"]) for lesson in sorted(unit["lessons"], key=lambda item: item["sequence"])]


def _validate_prompts(prompts: Sequence[Mapping[str, Any]], lesson_id: str) -> None:
    if len(prompts) != 4 or {prompt.get("modality") for prompt in prompts} != _MODALITIES:
        raise ValueError(f"{lesson_id} must have exactly four static modalities")
    by_modality = {prompt["modality"]: prompt for prompt in prompts}
    listening = by_modality["listening"]
    if listening.get("mode") != "TRANSCRIPT_ONLY" or not all(isinstance(listening.get(field), str) and listening[field].strip() for field in ("transcript", "question", "answer")):
        raise ValueError(f"{lesson_id} listening must be transcript-only with question and answer")
    pronunciation = by_modality["pronunciation"]
    if pronunciation.get("assessment") != "NOT_ASSESSED":
        raise ValueError(f"{lesson_id} pronunciation must be NOT_ASSESSED without audio")
    writing = by_modality["writing"]
    if not writing.get("checklist") or "Entwurf" not in writing["instruction"]:
        raise ValueError(f"{lesson_id} writing must be draft-first with a checklist")


def _validate_content(content: Mapping[str, Any], outline: Mapping[str, Any]) -> None:
    lesson_id = outline["id"]
    if content.get("outline_id") != lesson_id:
        raise ValueError(f"content record does not match outline: {lesson_id}")
    if not 15 <= content["duration_minutes"] <= 45 or not 2 <= len(content["sections"]) <= 4 or not 3 <= len(content["exercises"]) <= 6:
        raise ValueError(f"invalid duration, section, or exercise bounds: {lesson_id}")
    exercise_ids = {exercise["id"] for exercise in content["exercises"]}
    if len(exercise_ids) != len(content["exercises"]) or any(not exercise.get("answer") and not exercise.get("rubric") for exercise in content["exercises"]):
        raise ValueError(f"{lesson_id} exercises need unique IDs and answer or rubric")
    _validate_prompts(content["prompts"], lesson_id)


def _learner_text(packet: Mapping[str, Any]) -> list[tuple[str, str]]:
    result: list[tuple[str, str]] = []
    for section in packet["sections"]:
        result.append((f"{packet['lesson_id']}/section", section["body"]))
    for exercise in packet["exercises"]:
        result.append((f"{packet['lesson_id']}/{exercise['id']}", exercise["prompt"]))
    for prompt in packet["prompts"]:
        result.append((f"{packet['lesson_id']}/{prompt['modality']}", prompt["instruction"]))
        if prompt["modality"] == "listening":
            result.extend([(f"{packet['lesson_id']}/transcript", prompt["transcript"]), (f"{packet['lesson_id']}/question", prompt["question"])])
    return result


def _validate_duplicates(packets: Sequence[Mapping[str, Any]]) -> None:
    seen: dict[str, str] = {}
    for packet in packets:
        for location, value in _learner_text(packet):
            key = _normalized(value)
            if len(key) >= 24 and key in seen:
                raise ValueError(f"duplicate learner-facing text: {seen[key]!r}, {location!r}")
            if len(key) >= 24:
                seen[key] = location


def _packet(outline: Mapping[str, Any], content: Mapping[str, Any], sequence: int) -> dict[str, Any]:
    packet = {"schema_version": "1.0", "record_type": "german_a1_pilot_lesson_packet", "packet_id": f"dea1pilot-packet-{sequence:02d}", "language_code": "de", "lesson_id": outline["id"], "tier": outline["tier"], "sequence": sequence, "outline_targets": outline["targets"], "prerequisite_lesson_ids": outline["prerequisites"], "title": content["title"], "duration_minutes": content["duration_minutes"], "objectives": content["objectives"], "sections": content["sections"], "exercises": content["exercises"], "prompts": content["prompts"], "content_status": "UNREVIEWED", "provenance": {"content_origin": "PROJECT_AUTHORED", "content_input_id": content["outline_id"]}}
    packet["packet_sha256"] = sha256_json(packet)
    validate_instance(packet, "german-a1-pilot-lesson-packet-v1")
    return packet


def _validate_packet(packet: Mapping[str, Any]) -> None:
    validate_instance(packet, "german-a1-pilot-lesson-packet-v1")
    actual = dict(packet)
    if actual.pop("packet_sha256") != sha256_json(actual):
        raise ValueError(f"packet hash mismatch: {packet['packet_id']}")
    _no_forbidden_claims(packet)
    _validate_prompts(packet["prompts"], packet["lesson_id"])


def build_pilot(*, population_path: Path, blueprint_path: Path, content_path: Path, output_root: Path, built_at: str) -> Path:
    population, blueprint, content = (load_document(path) for path in (population_path, blueprint_path, content_path))
    validate_population(population)
    validate_blueprint(blueprint, population)
    validate_instance(content, "german-a1-pilot-content-input-v1")
    _no_forbidden_claims(content)
    outlines = _outlines(blueprint)
    if len(outlines) != 10:
        raise ValueError("German blueprint must provide ten pilot outlines")
    by_id = {item["outline_id"]: item for item in content["lessons"]}
    lesson_ids = [outline["id"] for outline in outlines]
    if len(by_id) != 10 or set(by_id) != set(lesson_ids):
        raise ValueError("German pilot content must cover exactly the ten blueprint lessons")
    packets = []
    for sequence, outline in enumerate(outlines, 1):
        item = by_id[outline["id"]]
        _validate_content(item, outline)
        packets.append(_packet(outline, item, sequence))
    _validate_duplicates(packets)
    source = {"population_sha256": sha256_json(population), "blueprint_sha256": sha256_json(blueprint), "content_input_sha256": sha256_json(content)}
    pilot_id = "dea1pilot_" + hashlib.sha256(_canonical_bytes({"source": source, "lesson_ids": lesson_ids, "built_at": built_at})).hexdigest()
    destination = output_root / pilot_id
    temporary = output_root / f".{pilot_id}.tmp"
    if destination.exists() or temporary.exists():
        raise FileExistsError(f"refusing to overwrite German pilot: {destination}")
    temporary.mkdir(parents=True)
    try:
        packets_dir = temporary / "packets"; packets_dir.mkdir()
        inventory = []
        for packet in packets:
            relative = f"packets/{packet['packet_id']}.json"; path = temporary / relative
            path.write_bytes(_canonical_bytes(packet) + b"\n")
            inventory.append({"path": relative, "sha256": _file_hash(path)})
        manifest = {"schema_version": "1.0", "record_type": "german_a1_pilot_manifest", "pilot_id": pilot_id, "language_code": "de", "built_at": built_at, "content_status": "UNREVIEWED", "source": source, "lesson_ids": lesson_ids, "inventory": inventory}
        manifest["manifest_sha256"] = sha256_json(manifest)
        validate_instance(manifest, "german-a1-pilot-manifest-v1")
        (temporary / "manifest.json").write_bytes(_canonical_bytes(manifest) + b"\n")
        temporary.replace(destination)
    except BaseException:
        shutil.rmtree(temporary, ignore_errors=True)
        raise
    return destination


def verify_pilot(*, pilot_dir: Path, population_path: Path, blueprint_path: Path) -> dict[str, Any]:
    population, blueprint = (load_document(path) for path in (population_path, blueprint_path))
    validate_population(population); validate_blueprint(blueprint, population)
    manifest = load_document(pilot_dir / "manifest.json")
    validate_instance(manifest, "german-a1-pilot-manifest-v1")
    declared = dict(manifest)
    if declared.pop("manifest_sha256") != sha256_json(declared):
        raise ValueError("manifest hash mismatch")
    source = manifest["source"]
    if source["population_sha256"] != sha256_json(population) or source["blueprint_sha256"] != sha256_json(blueprint):
        raise ValueError("pilot source binding drift")
    outlines = _outlines(blueprint)
    if manifest["lesson_ids"] != [item["id"] for item in outlines]:
        raise ValueError("pilot lesson ordering drift")
    expected_paths = {"manifest.json"}; packets = []
    for index, item in enumerate(manifest["inventory"], 1):
        relative = item["path"]; path = pilot_dir / relative
        if not re.fullmatch(r"packets/dea1pilot-packet-(0[1-9]|10)\.json", relative) or not path.is_file() or _file_hash(path) != item["sha256"]:
            raise ValueError(f"pilot inventory mismatch: {relative}")
        expected_paths.add(relative); packet = load_document(path); _validate_packet(packet)
        outline = outlines[index - 1]
        if packet["lesson_id"] != outline["id"] or packet["sequence"] != index or packet["outline_targets"] != outline["targets"] or packet["prerequisite_lesson_ids"] != outline["prerequisites"]:
            raise ValueError(f"pilot packet blueprint mismatch: {packet['packet_id']}")
        packets.append(packet)
    actual_paths = {path.relative_to(pilot_dir).as_posix() for path in pilot_dir.rglob("*") if path.is_file()}
    if actual_paths != expected_paths or len(packets) != 10:
        raise ValueError("pilot must have a closed ten-packet inventory")
    _validate_duplicates(packets)
    return manifest


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__); commands = parser.add_subparsers(dest="command", required=True)
    build = commands.add_parser("build")
    for name in ("population", "blueprint", "content"):
        build.add_argument(f"--{name}", type=Path, required=True)
    build.add_argument("--output-root", type=Path, required=True); build.add_argument("--built-at", required=True)
    verify = commands.add_parser("verify"); verify.add_argument("pilot_dir", type=Path)
    verify.add_argument("--population", type=Path, required=True); verify.add_argument("--blueprint", type=Path, required=True)
    args = parser.parse_args()
    if args.command == "build": print(build_pilot(population_path=args.population, blueprint_path=args.blueprint, content_path=args.content, output_root=args.output_root, built_at=args.built_at))
    else: verify_pilot(pilot_dir=args.pilot_dir, population_path=args.population, blueprint_path=args.blueprint); print("PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
