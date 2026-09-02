"""Constrained provider-neutral M6 lesson generation orchestration."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from english_master.schema_validation import validate_instance

from .canonical import canonical_json, sha256_json
from .models import GenerationIssue, LessonBackend, LessonGenerationRequest, LessonGenerationResult, JsonObject
from .storage import publish, write_rejection
from .validator import postgeneration_issues, preflight_issues


class LessonGenerator:
    """Validate, generate, validate again, and publish only accepted M6 lessons."""

    def __init__(self, backend: LessonBackend) -> None:
        self.backend = backend

    @staticmethod
    def _safe_identity(request: JsonObject, key: str) -> str:
        value = request.get(key)
        return value if isinstance(value, str) else "UNAVAILABLE"

    @staticmethod
    def _request_hash(request: JsonObject) -> str:
        return sha256_json(request)

    def _audit(self, request: JsonObject, *, accepted: bool, issues: tuple[GenerationIssue, ...], output_hash: str | None) -> JsonObject:
        generation = request.get("generation") if isinstance(request.get("generation"), dict) else {}
        authorization = request.get("authorization") if isinstance(request.get("authorization"), dict) else {}
        spec = request.get("lesson_spec") if isinstance(request.get("lesson_spec"), dict) else {}
        graph = request.get("graph") if isinstance(request.get("graph"), dict) else {}
        constraints = request.get("constraints") if isinstance(request.get("constraints"), dict) else {}
        request_id = self._safe_identity(request, "request_id")
        if not request_id.startswith("req_"): request_id = "UNAVAILABLE"
        lesson_id = self._safe_identity(spec, "id")
        if lesson_id == "UNAVAILABLE" or "-U" not in lesson_id: lesson_id = "UNAVAILABLE"
        failed_codes = {issue.code for issue in issues}
        preflight_ok = not failed_codes.intersection({"REQUEST_SCHEMA", "REQUEST_ID_MISMATCH", "AUTHORIZATION_ID_MISMATCH", "VERSION_MISMATCH", "DUPLICATE_AUTHORIZED_ID", "UNRESOLVED_REFERENCE", "WRONG_REFERENCE_TYPE", "ABOVE_TARGET_CEFR"})
        report: JsonObject = {
            "schema_version": "1.0", "request_id": request_id, "lesson_id": lesson_id,
            "status": "ACCEPTED" if accepted else "REJECTED",
            "input_hashes": {"request": self._request_hash(request), "authorization": sha256_json(authorization), "lesson_spec": sha256_json(spec), "graph": sha256_json(graph)},
            "versions": {"generator": str(generation.get("generator_version", "UNAVAILABLE")), "prompt": str(generation.get("prompt_version", "UNAVAILABLE")), "curriculum": str(generation.get("curriculum_version", "UNAVAILABLE")), "taxonomy": str(generation.get("taxonomy_version", "UNAVAILABLE")), "lesson_schema": str(generation.get("lesson_schema_version", "UNAVAILABLE"))},
            "constraints_applied": constraints,
            "generator_metadata": {"provider": str(generation.get("provider", "UNAVAILABLE")), "model": str(generation.get("model", "UNAVAILABLE")), "parameters": generation.get("parameters", {}) if isinstance(generation.get("parameters", {}), dict) else {}, "seed": generation.get("seed") if isinstance(generation.get("seed"), int) else None},
            "checks": {
                "request_schema": "REQUEST_SCHEMA" not in failed_codes,
                "authorization": preflight_ok,
                "lesson_schema": accepted or "LESSON_SCHEMA" not in failed_codes,
                "constraints": accepted or not any(code in failed_codes for code in ("REFERENCE_SCOPE_MISMATCH", "FORBIDDEN_REFERENCE", "FORBIDDEN_TERM", "SECTION_LIMIT", "SECTION_SIZE_LIMIT", "TOTAL_SIZE_LIMIT", "UNDECLARED_EMBEDDED_REFERENCE")),
                "cefr": accepted or not any(code in failed_codes for code in ("CEFR_MISMATCH", "ABOVE_TARGET_CEFR")),
                "prerequisites": accepted or not any("PREREQUISITE" in code or code == "GRAPH_CYCLE" for code in failed_codes),
                "provenance_copyright": preflight_ok,
                "m7_plus_exclusion": accepted or not any(code in failed_codes for code in ("M7_LEAKAGE", "LATER_MILESTONE_LEAKAGE")),
            },
            "output_hash": output_hash,
            "qa_status": "UNREVIEWED" if accepted else "REJECTED",
            "unresolved_issues": [issue.as_dict() for issue in issues],
            "reproducibility": {"canonical_json": True, "byte_identical_claimed": generation.get("provider") == "offline-mock"},
        }
        validate_instance(report, "lesson-generation-audit")
        return report

    def _rejection(self, request: JsonObject, stage: str, issues: tuple[GenerationIssue, ...], candidate: JsonObject | None) -> JsonObject:
        request_id = self._safe_identity(request, "request_id")
        if not request_id.startswith("req_"): request_id = "UNAVAILABLE"
        spec = request.get("lesson_spec") if isinstance(request.get("lesson_spec"), dict) else {}
        lesson_id = self._safe_identity(spec, "id")
        if lesson_id == "UNAVAILABLE" or "-U" not in lesson_id: lesson_id = "UNAVAILABLE"
        auth = request.get("authorization") if isinstance(request.get("authorization"), dict) else {}
        rejected_at = auth.get("approved_at", "1970-01-01T00:00:00Z")
        rejection: JsonObject = {
            "schema_version": "1.0", "request_id": request_id, "lesson_id": lesson_id,
            "stage": stage, "rejected_at": rejected_at,
            "reasons": [issue.as_dict() for issue in issues], "request_hash": sha256_json(request),
            "candidate_output_hash": sha256_json(candidate) if candidate is not None else None,
            "candidate_output": candidate, "published": False,
        }
        validate_instance(rejection, "lesson-generation-rejection")
        return rejection

    @staticmethod
    def build_prompt(request: JsonObject) -> str:
        """Create a deterministic provider-neutral prompt with the full pinned request."""
        return (
            "Return exactly one JSON lesson object and no prose. Obey this M6 request exactly. "
            "Do not add scope, infer IDs, approve content, or generate exercises, assessments, "
            "AI prompts, answer keys, or media. Use original project-authored wording. REQUEST="
            + canonical_json(request)
        )

    def generate(self, request: LessonGenerationRequest, *, output_directory: Path | None = None, rejection_path: Path | None = None) -> LessonGenerationResult:
        payload = request.as_dict()
        preflight = preflight_issues(payload)
        if preflight:
            audit = self._audit(payload, accepted=False, issues=preflight, output_hash=None)
            rejection = self._rejection(payload, "PREFLIGHT", preflight, None)
            paths = (write_rejection(rejection_path, rejection),) if rejection_path else ()
            return LessonGenerationResult(False, None, audit, rejection, paths)
        generation = payload["generation"]
        try:
            candidate = self.backend.generate(self.build_prompt(payload), parameters=generation["parameters"], seed=generation.get("seed"))
            if not isinstance(candidate, dict):
                raise TypeError("backend response is not a JSON object")
        except Exception as error:
            issues = (GenerationIssue("PROVIDER_FAILURE", "$", f"backend failed: {type(error).__name__}: {error}"),)
            audit = self._audit(payload, accepted=False, issues=issues, output_hash=None)
            rejection = self._rejection(payload, "PROVIDER", issues, None)
            paths = (write_rejection(rejection_path, rejection),) if rejection_path else ()
            return LessonGenerationResult(False, None, audit, rejection, paths)
        post = postgeneration_issues(payload, candidate)
        candidate_hash = sha256_json(candidate)
        if post:
            audit = self._audit(payload, accepted=False, issues=post, output_hash=candidate_hash)
            rejection = self._rejection(payload, "POSTVALIDATION", post, candidate)
            paths = (write_rejection(rejection_path, rejection),) if rejection_path else ()
            return LessonGenerationResult(False, None, audit, rejection, paths)
        audit = self._audit(payload, accepted=True, issues=(), output_hash=candidate_hash)
        paths = publish(output_directory, candidate, audit) if output_directory else ()
        return LessonGenerationResult(True, candidate, audit, None, paths)
