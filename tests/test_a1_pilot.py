from __future__ import annotations

import json
from pathlib import Path

import pytest

from english_master.a1_pilot.service import build_pilot, build_review_template, summarize_review, verify_pilot
from english_master.curriculum_blueprint import build as build_blueprint
from english_master.knowledge_graph.service import build_population
from english_master.lesson_generation.canonical import sha256_json


BUILT_AT = "2026-09-12T10:00:00Z"


def _write_json(path: Path, value: dict) -> Path:
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding="utf-8")
    return path


def _content(blueprint: dict) -> dict:
    records = []
    for number, outline in enumerate(blueprint["lessons"][:10], start=1):
        lesson_id = outline["id"]
        records.append(
            {
                "outline_id": lesson_id,
                "title": f"A1 pilot focus {number}",
                "duration_minutes": 25,
                "objectives": [f"Use a controlled A1 idea for lesson {number}."],
                "content_sections": [
                    {"id": "notice", "title": "Notice", "body": f"This is original explanation text for lesson {number}."},
                    {"id": "practice", "title": "Practice", "body": f"Try the new language in a short situation {number}."},
                ],
                "exercises": [
                    {"id": "choose", "type": "multiple_choice", "prompt": f"Choose the best answer for situation {number}.", "answer": "The stated answer."},
                    {"id": "complete", "type": "fill_blank", "prompt": f"Complete the short sentence for lesson {number}.", "answer": "A suitable word."},
                    {"id": "say", "type": "speaking", "prompt": f"Say one new sentence for activity {number}.", "rubric": "Uses the target idea clearly."},
                ],
                "prompts": {
                    "listening": {"instruction": f"Listen to a short original greeting exchange {number}, then answer one question.", "goal": "Understand a simple message."},
                    "speaking": {"instruction": f"Take one short turn in an original roleplay {number}.", "goal": "Speak a simple response."},
                    "pronunciation": {"instruction": f"Read the target words for lesson {number} aloud; without audio, return NOT_ASSESSED.", "goal": "Notice a basic sound pattern."},
                    "writing": {"instruction": f"Write two short original sentences for scenario {number}; give feedback, not a replacement.", "goal": "Write controlled A1 sentences."},
                },
            }
        )
    return {"schema_version": "1.0", "record_type": "a1_pilot_content_input", "lessons": records}


def _inputs(tmp_path: Path) -> tuple[Path, Path, Path, dict]:
    population = build_population()
    blueprint = build_blueprint(population)
    population_path = _write_json(tmp_path / "population.json", population)
    blueprint_path = _write_json(tmp_path / "blueprint.json", blueprint)
    content = _content(blueprint)
    content_path = _write_json(tmp_path / "content.json", content)
    return population_path, blueprint_path, content_path, content


def test_build_and_verify_closed_a1_pilot(tmp_path: Path) -> None:
    population, blueprint, content, _ = _inputs(tmp_path)

    directory = build_pilot(population_path=population, blueprint_path=blueprint, content_path=content, output_root=tmp_path / "out", built_at=BUILT_AT)

    manifest = verify_pilot(directory, population, blueprint)
    assert len(manifest["lesson_ids"]) == 10
    assert len(manifest["inventory"]) == 10
    assert manifest["content_status"] == "UNREVIEWED"


def test_build_rejects_missing_prompt_modality(tmp_path: Path) -> None:
    population, blueprint, content_path, content = _inputs(tmp_path)
    del content["lessons"][0]["prompts"]["writing"]
    _write_json(content_path, content)

    with pytest.raises(Exception, match="writing"):
        build_pilot(population_path=population, blueprint_path=blueprint, content_path=content_path, output_root=tmp_path / "out", built_at=BUILT_AT)


def test_build_rejects_duplicate_learner_text(tmp_path: Path) -> None:
    population, blueprint, content_path, content = _inputs(tmp_path)
    content["lessons"][1]["content_sections"][0]["body"] = content["lessons"][0]["content_sections"][0]["body"]
    _write_json(content_path, content)

    with pytest.raises(ValueError, match="duplicated learner-facing text"):
        build_pilot(population_path=population, blueprint_path=blueprint, content_path=content_path, output_root=tmp_path / "out", built_at=BUILT_AT)


def test_verify_rejects_inventory_hash_drift(tmp_path: Path) -> None:
    population, blueprint, content, _ = _inputs(tmp_path)
    directory = build_pilot(population_path=population, blueprint_path=blueprint, content_path=content, output_root=tmp_path / "out", built_at=BUILT_AT)
    packet = next((directory / "packets").glob("*.json"))
    packet.write_text("{}", encoding="utf-8")

    with pytest.raises(ValueError, match="inventory hash mismatch"):
        verify_pilot(directory, population, blueprint)


def test_review_summary_classifies_systemic_and_isolated_findings(tmp_path: Path) -> None:
    population, blueprint, content, _ = _inputs(tmp_path)
    directory = build_pilot(population_path=population, blueprint_path=blueprint, content_path=content, output_root=tmp_path / "out", built_at=BUILT_AT)
    manifest = verify_pilot(directory, population, blueprint)
    lessons = []
    for index, lesson_id in enumerate(manifest["lesson_ids"]):
        findings = []
        if index == 0:
            findings.append({"dimension": "grammar_correctness", "classification": "SYSTEMIC", "severity": "BLOCKING", "description": "A shared template needs a grammar constraint.", "generator_rule": "Require subject-verb agreement check."})
        if index == 1:
            findings.append({"dimension": "lesson_duration", "classification": "ISOLATED", "severity": "INFO", "description": "This packet needs a shorter example."})
        lessons.append({"lesson_id": lesson_id, "dimensions": {dimension: "PASS" for dimension in ("explanation_clarity", "grammar_correctness", "vocabulary_difficulty", "exercise_quality", "prompt_usability", "lesson_duration", "duplication")}, "findings": findings})
    review = {"schema_version": "1.0", "record_type": "a1_pilot_review", "pilot_id": manifest["pilot_id"], "manifest_sha256": manifest["manifest_sha256"], "reviewers": [{"reviewer_type": "USER", "identifier": "pilot-user"}, {"reviewer_type": "AI", "identifier": "development-ai", "provider": "UNKNOWN", "model": "UNKNOWN"}], "lessons": lessons}
    review_path = _write_json(tmp_path / "review.json", review)
    output = summarize_review(pilot_dir=directory, population_path=population, blueprint_path=blueprint, review_path=review_path, output_path=tmp_path / "summary.json")

    summary = json.loads(output.read_text(encoding="utf-8"))
    assert summary["next_action"] == "FIX_GENERATOR"
    assert len(summary["systemic_findings"]) == 1
    assert len(summary["isolated_findings"]) == 1


def test_review_template_is_explicitly_incomplete(tmp_path: Path) -> None:
    population, blueprint, content, _ = _inputs(tmp_path)
    directory = build_pilot(population_path=population, blueprint_path=blueprint, content_path=content, output_root=tmp_path / "out", built_at=BUILT_AT)

    template_path = build_review_template(pilot_dir=directory, population_path=population, blueprint_path=blueprint, output_path=tmp_path / "review-template.json")
    template = json.loads(template_path.read_text(encoding="utf-8"))

    assert len(template["lessons"]) == 10
    assert all(set(entry["dimensions"].values()) == {"NOT_RUN"} for entry in template["lessons"])
    with pytest.raises(ValueError, match="cannot contain NOT_RUN"):
        summarize_review(pilot_dir=directory, population_path=population, blueprint_path=blueprint, review_path=template_path, output_path=tmp_path / "summary.json")


def test_review_rejects_systemic_finding_without_generator_rule(tmp_path: Path) -> None:
    population, blueprint, content, _ = _inputs(tmp_path)
    directory = build_pilot(population_path=population, blueprint_path=blueprint, content_path=content, output_root=tmp_path / "out", built_at=BUILT_AT)
    manifest = verify_pilot(directory, population, blueprint)
    dimensions = {dimension: "PASS" for dimension in ("explanation_clarity", "grammar_correctness", "vocabulary_difficulty", "exercise_quality", "prompt_usability", "lesson_duration", "duplication")}
    review = {"schema_version": "1.0", "record_type": "a1_pilot_review", "pilot_id": manifest["pilot_id"], "manifest_sha256": manifest["manifest_sha256"], "reviewers": [{"reviewer_type": "USER", "identifier": "pilot-user"}], "lessons": [{"lesson_id": lesson_id, "dimensions": dimensions, "findings": ([{"dimension": "duplication", "classification": "SYSTEMIC", "severity": "BLOCKING", "description": "Repeated prompt text."}] if index == 0 else [])} for index, lesson_id in enumerate(manifest["lesson_ids"])]}
    review_path = _write_json(tmp_path / "review.json", review)

    with pytest.raises(ValueError, match="must identify a generator rule"):
        summarize_review(pilot_dir=directory, population_path=population, blueprint_path=blueprint, review_path=review_path, output_path=tmp_path / "summary.json")
