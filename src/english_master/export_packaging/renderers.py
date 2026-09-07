"""Standard-library renderers for the required M11 distribution formats."""
from __future__ import annotations

import csv
import html
import io
import json
import zipfile
from collections import defaultdict
from pathlib import Path
from typing import Any, Iterable, Mapping
from xml.etree import ElementTree as ET

from .canonical import canonical_json_bytes
from .models import ExportArtifact, ExportModel

JsonObject = dict[str, Any]


def _write(path: Path, value: bytes) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(value)
    return path


def _json_text(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def _groups(model: ExportModel) -> dict[str, list[ExportArtifact]]:
    grouped: dict[str, list[ExportArtifact]] = defaultdict(list)
    for artifact in model.artifacts:
        grouped[artifact.lesson_id].append(artifact)
    return grouped


def render_json(root: Path, model: ExportModel) -> list[Path]:
    catalog = {
        "schema_version": model.schema_version,
        "package_version": model.package_version,
        "exported_at": model.exported_at,
        "artifacts": [
            {
                "content_type": item.content_type,
                "content_id": item.content_id,
                "lesson_id": item.lesson_id,
                "source_sha256": item.sha256,
                "href": f"artifacts/{item.content_type.lower()}/{item.content_id}.json",
            }
            for item in model.artifacts
        ],
    }
    paths = [_write(root / "json" / "catalog.json", canonical_json_bytes(catalog))]
    for item in model.artifacts:
        paths.append(_write(root / "json" / "artifacts" / item.content_type.lower() / f"{item.content_id}.json", canonical_json_bytes(item.content)))
    return paths


def _csv_bytes(headers: list[str], rows: Iterable[Mapping[str, Any]]) -> bytes:
    stream = io.StringIO(newline="")
    writer = csv.DictWriter(stream, fieldnames=headers, extrasaction="ignore", lineterminator="\r\n")
    writer.writeheader()
    for row in rows:
        writer.writerow({key: row.get(key, "") for key in headers})
    return stream.getvalue().encode("utf-8")


def _walk_provenance(value: Any, owner_id: str, pointer: str = "$") -> Iterable[JsonObject]:
    if isinstance(value, Mapping):
        if {"source_id", "license", "attribution"}.issubset(value):
            yield {"content_id": owner_id, "json_pointer": pointer, "source_id": value.get("source_id", ""), "source_url": value.get("source_url", ""), "source_record_id": value.get("source_record_id", ""), "license": value.get("license", ""), "attribution": value.get("attribution", ""), "content_hash": value.get("content_hash", "")}
        for key in sorted(value):
            yield from _walk_provenance(value[key], owner_id, f"{pointer}/{key}")
    elif isinstance(value, list):
        for index, item in enumerate(value):
            yield from _walk_provenance(item, owner_id, f"{pointer}/{index}")


def render_csv(root: Path, model: ExportModel) -> list[Path]:
    lessons: list[JsonObject] = []
    sections: list[JsonObject] = []
    exercises: list[JsonObject] = []
    references: list[JsonObject] = []
    provenance: list[JsonObject] = []
    for artifact in model.artifacts:
        record = artifact.content
        provenance.extend(_walk_provenance(record, artifact.content_id))
        if artifact.content_type == "LESSON":
            lessons.append({"lesson_id": record["id"], "unit_id": record["unit_id"], "cefr_level": record["cefr_level"], "lesson_number": record["lesson_number"], "title": record["title"], "duration_minutes": record["duration_minutes"], "objectives_json": _json_text(record["objectives"])})
            for position, section in enumerate(record.get("content_sections", []), 1):
                sections.append({"lesson_id": record["id"], "position": position, "section_id": section["id"], "section_type": section["section_type"], "title": section["title"], "body_text": section["body_text"], "embedded_examples_json": _json_text(section.get("embedded_examples", []))})
            for field in ("grammar_introduced", "grammar_reviewed", "vocabulary_introduced", "vocabulary_reviewed", "communicative_functions", "taxonomy_concepts"):
                for target in record.get(field, []): references.append({"content_id": artifact.content_id, "relation": field, "target_id": target})
        elif artifact.content_type == "EXERCISE_SET":
            for exercise in record.get("exercises", []):
                exercises.append({"exercise_set_id": record["exercise_set_id"], "lesson_id": artifact.lesson_id, "exercise_id": exercise["id"], "sequence": exercise["sequence"], "exercise_type": exercise["exercise_type"], "difficulty": exercise["difficulty"], "title": exercise["title"], "instructions": exercise["instructions"], "scoring_mode": exercise["scoring_mode"], "payload_json": _json_text(exercise["payload"])})
                for field in ("target_references", "review_references"):
                    for target in exercise.get(field, []): references.append({"content_id": exercise["id"], "relation": field, "target_id": target})
        else:
            for field in ("target_vocabulary", "target_grammar", "known_references", "target_references"):
                for target in record.get(field, []): references.append({"content_id": artifact.content_id, "relation": field, "target_id": target})
    specs = (
        ("lessons.csv", ["lesson_id", "unit_id", "cefr_level", "lesson_number", "title", "duration_minutes", "objectives_json"], sorted(lessons, key=lambda row: row["lesson_id"])),
        ("sections.csv", ["lesson_id", "position", "section_id", "section_type", "title", "body_text", "embedded_examples_json"], sorted(sections, key=lambda row: (row["lesson_id"], row["position"]))),
        ("exercises.csv", ["exercise_set_id", "lesson_id", "exercise_id", "sequence", "exercise_type", "difficulty", "title", "instructions", "scoring_mode", "payload_json"], sorted(exercises, key=lambda row: (row["lesson_id"], row["sequence"]))),
        ("references.csv", ["content_id", "relation", "target_id"], sorted(references, key=lambda row: (row["content_id"], row["relation"], row["target_id"]))),
        ("provenance.csv", ["content_id", "json_pointer", "source_id", "source_url", "source_record_id", "license", "attribution", "content_hash"], sorted(provenance, key=lambda row: (row["content_id"], row["json_pointer"]))),
    )
    return [_write(root / "csv" / name, _csv_bytes(headers, rows)) for name, headers, rows in specs]


def _lesson_bundle(group: list[ExportArtifact]) -> tuple[Mapping[str, Any], list[Mapping[str, Any]], list[Mapping[str, Any]]]:
    lessons = [item.content for item in group if item.content_type == "LESSON"]
    if len(lessons) != 1:
        raise ValueError("each exported lesson must have exactly one lesson record")
    exercises = [item.content for item in group if item.content_type == "EXERCISE_SET"]
    prompts = [item.content for item in group if item.content_type == "AI_PRACTICE_PROMPT"]
    return lessons[0], exercises, prompts


def _exercise_answer(payload: Mapping[str, Any]) -> str:
    keys = ("primary_answer", "answers", "acceptable_variants", "rubric", "scoring_rubric", "sample_answer")
    selected = {key: payload[key] for key in keys if key in payload}
    return _json_text(selected) if selected else "Subjective response; use the recorded scoring guidance."


def _lesson_html(lesson: Mapping[str, Any], exercise_sets: list[Mapping[str, Any]], prompts: list[Mapping[str, Any]], *, answers: bool) -> str:
    pieces = [f'<article id="{html.escape(str(lesson["id"]), quote=True)}">', f"<h1>{html.escape(str(lesson['title']))}</h1>", f"<p>{html.escape(str(lesson['cefr_level']))} · {int(lesson['duration_minutes'])} minutes</p>"]
    for section in lesson.get("content_sections", []):
        pieces.extend((f"<section><h2>{html.escape(str(section['title']))}</h2>", f"<p>{html.escape(str(section['body_text']))}</p></section>"))
    if exercise_sets:
        pieces.append("<section><h2>Exercises</h2><ol>")
        for exercise_set in exercise_sets:
            for exercise in exercise_set.get("exercises", []):
                pieces.append(f"<li><strong>{html.escape(str(exercise['title']))}</strong>: {html.escape(str(exercise['instructions']))}")
                if answers: pieces.append(f'<div class="answer"><b>Answer material:</b> {html.escape(_exercise_answer(exercise["payload"]))}</div>')
                pieces.append("</li>")
        pieces.append("</ol></section>")
    if prompts:
        pieces.append("<section><h2>Static AI-practice protocols</h2><p>These records do not provide or verify live provider behavior.</p><ul>")
        for prompt in sorted(prompts, key=lambda item: str(item.get("modality"))): pieces.append(f"<li>{html.escape(str(prompt['modality']).title())}</li>")
        pieces.append("</ul></section>")
    pieces.append("</article>")
    return "".join(pieces)


_CSS = "body{font-family:system-ui,sans-serif;max-width:52rem;margin:auto;padding:1rem;line-height:1.5}article{margin-bottom:3rem}.answer{border-left:.25rem solid #555;padding:.5rem;margin:.5rem 0}@media print{body{max-width:none}.answer{break-inside:avoid}article{break-after:page}}\n"


def _static_site(root: Path, model: ExportModel, family: str) -> list[Path]:
    base = root / family
    paths = [_write(base / "styles.css", _CSS.encode("utf-8"))]
    index_items: list[str] = []
    catalog: list[JsonObject] = []
    for lesson_id, group in sorted(_groups(model).items()):
        lesson, exercises, prompts = _lesson_bundle(group)
        href = f"lessons/{lesson_id}.html"
        index_items.append(f'<li><a href="{href}">{html.escape(str(lesson["title"]))}</a></li>')
        catalog.append({"lesson_id": lesson_id, "title": lesson["title"], "cefr_level": lesson["cefr_level"], "href": href})
        document = '<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><link rel="stylesheet" href="../styles.css"><title>' + html.escape(str(lesson["title"])) + "</title></head><body>" + _lesson_html(lesson, exercises, prompts, answers=False) + "</body></html>\n"
        paths.append(_write(base / href, document.encode("utf-8")))
    index = '<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><link rel="stylesheet" href="styles.css"><title>English Master</title></head><body><h1>English Master</h1><ul>' + "".join(index_items) + "</ul></body></html>\n"
    paths.extend((_write(base / "index.html", index.encode("utf-8")), _write(base / "catalog.json", canonical_json_bytes({"schema_version": "1.0", "lessons": catalog, "runtime": "STATIC_OFFLINE"}))))
    return paths


def render_mobile(root: Path, model: ExportModel) -> list[Path]: return _static_site(root, model, "mobile")
def render_web(root: Path, model: ExportModel) -> list[Path]: return _static_site(root, model, "web")


def render_print(root: Path, model: ExportModel) -> list[Path]:
    bundles = [_lesson_bundle(group) for _, group in sorted(_groups(model).items())]
    paths: list[Path] = []
    for edition, answers in (("learner", False), ("instructor-answer-key", True)):
        body = "".join(_lesson_html(*bundle, answers=answers) for bundle in bundles)
        label = "Learner edition" if not answers else "Instructor answer-key edition — separate file is not access control"
        document = f'<!doctype html><html lang="en"><head><meta charset="utf-8"><title>English Master — {html.escape(label)}</title><style>{_CSS}</style></head><body><header><h1>{html.escape(label)}</h1></header>{body}</body></html>\n'
        paths.append(_write(root / "print" / f"{edition}.html", document.encode("utf-8")))
    return paths


def _xhtml(lesson: Mapping[str, Any], exercises: list[Mapping[str, Any]], prompts: list[Mapping[str, Any]]) -> bytes:
    title = html.escape(str(lesson["title"]))
    return ('<?xml version="1.0" encoding="UTF-8"?>\n<!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.0 Strict//EN" "http://www.w3.org/TR/xhtml1/DTD/xhtml1-strict.dtd">\n<html xmlns="http://www.w3.org/1999/xhtml" lang="en"><head><title>' + title + '</title><meta http-equiv="Content-Type" content="text/html; charset=utf-8" /></head><body>' + _lesson_html(lesson, exercises, prompts, answers=False) + "</body></html>\n").encode("utf-8")


def common_cartridge_bytes(model: ExportModel) -> bytes:
    namespace = "http://www.imsglobal.org/xsd/imsccv1p3/imscp_v1p1"
    ET.register_namespace("", namespace)
    manifest = ET.Element(f"{{{namespace}}}manifest", {"identifier": "english-master"})
    organizations = ET.SubElement(manifest, f"{{{namespace}}}organizations")
    organization = ET.SubElement(organizations, f"{{{namespace}}}organization", {"identifier": "course", "structure": "rooted-hierarchy"})
    ET.SubElement(organization, f"{{{namespace}}}title").text = "English Master"
    resources = ET.SubElement(manifest, f"{{{namespace}}}resources")
    members: dict[str, bytes] = {}
    for lesson_id, group in sorted(_groups(model).items()):
        lesson, exercises, prompts = _lesson_bundle(group)
        href = f"resources/{lesson_id}.xhtml"
        item = ET.SubElement(organization, f"{{{namespace}}}item", {"identifier": f"item-{lesson_id}", "identifierref": f"res-{lesson_id}"})
        ET.SubElement(item, f"{{{namespace}}}title").text = str(lesson["title"])
        resource = ET.SubElement(resources, f"{{{namespace}}}resource", {"identifier": f"res-{lesson_id}", "type": "webcontent", "href": href})
        ET.SubElement(resource, f"{{{namespace}}}file", {"href": href})
        members[href] = _xhtml(lesson, exercises, prompts)
    members["imsmanifest.xml"] = ET.tostring(manifest, encoding="utf-8", xml_declaration=True) + b"\n"
    output = io.BytesIO()
    with zipfile.ZipFile(output, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as archive:
        for name in sorted(members):
            info = zipfile.ZipInfo(name, date_time=(1980, 1, 1, 0, 0, 0))
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = 0o100644 << 16
            info.create_system = 3
            archive.writestr(info, members[name], compress_type=zipfile.ZIP_DEFLATED, compresslevel=9)
    return output.getvalue()


def render_common_cartridge(root: Path, model: ExportModel) -> list[Path]:
    return [_write(root / "lms" / "english-master.imscc", common_cartridge_bytes(model))]


RENDERERS = {
    "JSON": render_json,
    "CSV": render_csv,
    "STATIC_MOBILE": render_mobile,
    "STATIC_WEB": render_web,
    "PRINT_HTML": render_print,
    "IMS_COMMON_CARTRIDGE_1_3": render_common_cartridge,
}
