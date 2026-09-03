"""Constrained, snapshot-bound M6 lesson generation orchestration."""

from __future__ import annotations

import copy
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Mapping

from english_master.schema_validation import validate_instance

from .authority import LessonGenerationAuthority
from .canonical import canonical_json, sha256_json, sha256_text
from .models import CapturedLessonResponse, GenerationIssue, JsonObject, LessonBackend, LessonGenerationRequest, LessonGenerationResult
from .storage import publish, publish_rejection
from .validator import backend_candidate_issues, postgeneration_issues, preflight_issues

CHECK_NAMES = (
    "request_schema", "m5_authority", "authorization", "identity", "graph", "constraints",
    "provenance_copyright", "backend_contract", "lesson_schema", "cefr_reference_scope",
    "prerequisites", "m7_plus_exclusion", "publication",
)
PREFLIGHT_CHECKS = CHECK_NAMES[:7]
POST_CHECKS = CHECK_NAMES[8:12]
ISSUE_CHECKS: dict[str, tuple[str, ...]] = {
    "REQUEST_SCHEMA": ("request_schema",), "AUTHORIZATION_SCHEMA": ("authorization",),
    "REQUEST_DERIVATION_MISMATCH": ("request_schema", "identity", "graph", "constraints"),
    "AUTHORIZATION_BINDING_MISMATCH": ("authorization", "identity"),
    "M5_BUNDLE_INVALID": ("m5_authority",), "M5_CONTENT_GENERATION_BLOCKED": ("m5_authority",),
    "PROVIDER_FAILURE": ("backend_contract",), "CAPTURE_MISMATCH": ("backend_contract",),
    "BACKEND_RESPONSE_INVALID": ("backend_contract",), "BACKEND_SCOPE_VIOLATION": ("backend_contract",),
    "LESSON_SCHEMA": ("lesson_schema",), "LESSON_SPEC_MISMATCH": ("identity",),
    "REFERENCE_SCOPE_MISMATCH": ("cefr_reference_scope",), "M7_LEAKAGE": ("m7_plus_exclusion",),
    "LATER_MILESTONE_LEAKAGE": ("m7_plus_exclusion",), "SECTION_LIMIT": ("constraints",),
    "EMPTY_SECTION": ("constraints",), "SECTION_SIZE_LIMIT": ("constraints",),
    "TOTAL_SIZE_LIMIT": ("constraints",), "FORBIDDEN_TERM": ("constraints",),
    "UNDECLARED_EMBEDDED_REFERENCE": ("constraints", "cefr_reference_scope"),
    "NONCANONICAL_ORDER": ("constraints",), "FORBIDDEN_REFERENCE": ("constraints", "cefr_reference_scope"),
    "GENERATION_METADATA_MISMATCH": ("identity",), "PUBLICATION_FAILURE": ("publication",),
    "REJECTION_PERSISTENCE_FAILURE": ("publication",),
}


class LessonGenerator:
    """Validate authority, bind a captured response, inject trust, and publish."""

    def __init__(
        self,
        backend: LessonBackend,
        authority: LessonGenerationAuthority,
        *,
        clock: Callable[[], datetime] | None = None,
    ) -> None:
        self.backend = backend
        self.authority = authority
        self._clock = clock or (lambda: datetime.now(timezone.utc))

    @staticmethod
    def _safe_identity(value: Mapping[str, Any], key: str, pattern: str) -> str:
        candidate = value.get(key)
        return candidate if isinstance(candidate, str) and re.fullmatch(pattern, candidate) else "UNAVAILABLE"

    @staticmethod
    def _safe_hash(value: Any) -> str | None:
        try:
            return sha256_json(value)
        except (TypeError, ValueError, OverflowError):
            return None

    def _timestamp(self) -> str:
        value = self._clock()
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("orchestration clock must return an aware datetime")
        return value.astimezone(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")

    @staticmethod
    def _safe_object(value: Any) -> JsonObject:
        if not isinstance(value, Mapping):
            return {}
        try:
            return copy.deepcopy(dict(value)) if sha256_json(value) else {}
        except (TypeError, ValueError, OverflowError):
            return {}

    @staticmethod
    def _check_outcomes(stage: str, issues: tuple[GenerationIssue, ...]) -> JsonObject:
        issue_codes = {issue.code for issue in issues}
        if stage == "PREFLIGHT":
            ran = {"request_schema", "authorization", "m5_authority"} if issue_codes & {"REQUEST_SCHEMA", "AUTHORIZATION_SCHEMA"} else set(PREFLIGHT_CHECKS)
        elif stage == "PROVIDER":
            ran = set(PREFLIGHT_CHECKS) | {"backend_contract"}
        elif stage == "POSTVALIDATION":
            ran = set(PREFLIGHT_CHECKS) | {"backend_contract"} | set(POST_CHECKS)
        elif stage == "PUBLICATION":
            ran = set(CHECK_NAMES)
        else:
            ran = set(CHECK_NAMES) - {"publication"}
        failed: set[str] = set()
        for issue in issues:
            failed.update(ISSUE_CHECKS.get(issue.code, tuple(ran)))
        return {name: "FAIL" if name in failed else "PASS" if name in ran else "NOT_RUN" for name in CHECK_NAMES}

    @staticmethod
    def _capture_provenance(capture: CapturedLessonResponse | None) -> JsonObject | None:
        return capture.provenance() if capture is not None else None

    def _audit(
        self,
        request: JsonObject,
        *,
        accepted: bool,
        stage: str,
        issues: tuple[GenerationIssue, ...],
        output_hash: str | None,
        capture: CapturedLessonResponse | None = None,
        publication_attempted: bool = False,
    ) -> JsonObject:
        spec = request.get("lesson_spec") if isinstance(request.get("lesson_spec"), Mapping) else {}
        constraints = request.get("constraints") if isinstance(request.get("constraints"), Mapping) else {}
        generation = request.get("generation_config") if isinstance(request.get("generation_config"), Mapping) else {}
        checks = self._check_outcomes(stage, issues)
        if accepted and publication_attempted:
            checks["publication"] = "PASS"
        report: JsonObject = {
            "schema_version": "2.0", "record_type": "lesson_generation_audit",
            "request_id": self._safe_identity(request, "request_id", r"req_[a-f0-9]{64}"),
            "lesson_id": self._safe_identity(spec, "id", r"(?:A1|A2|B1|B2|C1|C2)-U(?:0[1-9]|[1-9][0-9])-L(?:0[1-9]|[1-9][0-9])"),
            "status": "ACCEPTED" if accepted else "REJECTED", "validation_stage": "COMPLETE" if accepted else stage,
            "snapshot_binding": self.authority.snapshot_binding(),
            "input_hashes": {"request": self._safe_hash(request), "authorization": self._safe_hash(self.authority.authorization_dict()), **self.authority.artifact_hashes()},
            "versions": {"generator": str(generation.get("generator_version", "UNAVAILABLE")), "prompt": str(generation.get("prompt_version", "UNAVAILABLE")), "curriculum": str(generation.get("curriculum_version", "UNAVAILABLE")), "taxonomy": str(generation.get("taxonomy_version", "UNAVAILABLE")), "lesson_schema": str(generation.get("lesson_schema_version", "UNAVAILABLE"))},
            "constraints_applied": self._safe_object(constraints), "response_provenance": self._capture_provenance(capture),
            "checks": checks, "output_hash": output_hash, "qa_status": "UNREVIEWED" if accepted else "REJECTED",
            "qa_reviewer": "english_master.m6_automated_validator", "qa_timestamp": self._timestamp(),
            "qa_outcome": "AUTOMATED_CHECKS_PASSED_PENDING_INDEPENDENT_REVIEW" if accepted else "AUTOMATED_CHECKS_FAILED",
            "qa_checks_performed": sorted(name for name, outcome in checks.items() if outcome != "NOT_RUN"),
            "qa_notes": "Automated M6 checks do not constitute independent linguistic, CEFR, language-quality, or pedagogical approval.",
            "qa_issues_found": [issue.as_dict() for issue in issues],
            "outstanding_independent_reviews": ["CEFR", "GRAMMAR_LEXICAL", "LANGUAGE_QUALITY", "PEDAGOGICAL"],
            "unresolved_issues": [issue.as_dict() for issue in issues],
            "reproducibility": {"canonical_json": True, "byte_identical_claimed": getattr(self.backend, "byte_identical_output", False) is True, "backend_deterministic": capture.deterministic if capture else False, "seeded": capture.seed is not None if capture else False, "replayable_from_capture": capture.replayable_from_capture if capture else False},
        }
        validate_instance(report, "lesson-generation-audit")
        return report

    def _rejection(self, request: JsonObject, stage: str, issues: tuple[GenerationIssue, ...], candidate: JsonObject | None, capture: CapturedLessonResponse | None = None) -> JsonObject:
        spec = request.get("lesson_spec") if isinstance(request.get("lesson_spec"), Mapping) else {}
        rejection: JsonObject = {
            "schema_version": "2.0", "record_type": "lesson_generation_rejection",
            "request_id": self._safe_identity(request, "request_id", r"req_[a-f0-9]{64}"),
            "lesson_id": self._safe_identity(spec, "id", r"(?:A1|A2|B1|B2|C1|C2)-U(?:0[1-9]|[1-9][0-9])-L(?:0[1-9]|[1-9][0-9])"),
            "snapshot_binding": self.authority.snapshot_binding(), "stage": stage, "rejected_at": self._timestamp(),
            "reasons": [issue.as_dict() for issue in issues], "request_hash": self._safe_hash(request),
            "candidate_output_hash": self._safe_hash(candidate) if candidate is not None else None,
            "candidate_output": copy.deepcopy(candidate), "response_provenance": self._capture_provenance(capture), "published": False,
        }
        validate_instance(rejection, "lesson-generation-rejection")
        return rejection

    @staticmethod
    def build_prompt(request: JsonObject) -> str:
        return ("Return exactly one JSON object with one key, content_sections, and no prose. "
                "The host injects identity, references, versions, timestamps, and QA metadata. "
                "Do not add exercises, assessments, AI prompts, answer keys, or media. REQUEST=" + canonical_json(request))

    @staticmethod
    def _generation_metadata(request: JsonObject, capture: CapturedLessonResponse) -> JsonObject:
        config = request["generation_config"]
        metadata: JsonObject = {
            "generator": config["generator"], "generator_version": config["generator_version"],
            "prompt_version": config["prompt_version"], "generated_at": capture.observed_at,
            "curriculum_version": config["curriculum_version"], "qa_status": "UNREVIEWED",
            "qa_notes": "Automated M6 structural checks passed; independent review remains required.",
        }
        if capture.model is not None:
            metadata["model"] = capture.model
        return metadata

    @classmethod
    def _assemble(cls, request: JsonObject, candidate: JsonObject, capture: CapturedLessonResponse) -> JsonObject:
        spec = request["lesson_spec"]
        return {
            "schema_version": "1.0", "id": spec["id"], "title": spec["title"], "unit_id": spec["unit_id"],
            "lesson_number": spec["lesson_number"], "cefr_level": spec["cefr"], "duration_minutes": spec["duration_minutes"],
            "objectives": copy.deepcopy(spec["objectives"]), "vocabulary_introduced": sorted(spec["vocabulary_introduced"]),
            "grammar_introduced": sorted(spec["grammar_introduced"]), "vocabulary_reviewed": sorted(spec["vocabulary_reviewed"]),
            "grammar_reviewed": sorted(spec["grammar_reviewed"]), "communicative_functions": sorted(spec["functions_introduced"] + spec["functions_reviewed"]),
            "functions_introduced": sorted(spec["functions_introduced"]), "functions_reviewed": sorted(spec["functions_reviewed"]),
            "pronunciation_introduced": sorted(spec["pronunciation_introduced"]), "pronunciation_reviewed": sorted(spec["pronunciation_reviewed"]),
            "taxonomy_concepts": sorted(spec["taxonomy_concepts"]), "skills": sorted(spec["skills"]), "dimensions": sorted(spec["dimensions"]),
            "review_of": sorted(spec["review_of"]), "lesson_kind": spec["lesson_kind"], "prerequisites": copy.deepcopy(spec["prerequisites"]),
            "content_sections": copy.deepcopy(candidate["content_sections"]), "exercises": [],
            "generation_metadata": cls._generation_metadata(request, capture),
        }

    @staticmethod
    def _capture_issues(capture: Any, prompt: str, parameters: Mapping[str, Any], seed: int | None) -> tuple[GenerationIssue, ...]:
        if not isinstance(capture, CapturedLessonResponse):
            return (GenerationIssue("CAPTURE_MISMATCH", "$", "backend must return a prompt-bound CapturedLessonResponse"),)
        if capture.prompt_sha256 != sha256_text(prompt) or capture.response_sha256 != sha256_json(capture.content):
            return (GenerationIssue("CAPTURE_MISMATCH", "$", "capture hashes do not bind the exact prompt and response"),)
        if dict(capture.parameters) != dict(parameters) or capture.seed != seed:
            return (GenerationIssue("CAPTURE_MISMATCH", "$", "capture parameters or seed do not equal the trusted request configuration"),)
        try:
            datetime.fromisoformat(capture.observed_at.replace("Z", "+00:00"))
        except (AttributeError, ValueError):
            return (GenerationIssue("CAPTURE_MISMATCH", "$.observed_at", "capture observed_at must be an ISO 8601 timestamp"),)
        return ()

    def _rejected_result(self, request: JsonObject, stage: str, issues: tuple[GenerationIssue, ...], candidate: JsonObject | None, rejection_directory: Path | None, capture: CapturedLessonResponse | None = None) -> LessonGenerationResult:
        output_hash = self._safe_hash(candidate) if candidate is not None else None
        audit = self._audit(request, accepted=False, stage=stage, issues=issues, output_hash=output_hash, capture=capture)
        rejection = self._rejection(request, stage, issues, candidate, capture)
        paths: tuple[Path, ...] = ()
        if rejection_directory is not None:
            try:
                paths = publish_rejection(rejection_directory, rejection, audit)
            except (OSError, ValueError, TypeError):
                combined = tuple(sorted(set(issues + (GenerationIssue("REJECTION_PERSISTENCE_FAILURE", "$", "rejection artifacts could not be published immutably"),))))
                audit = self._audit(request, accepted=False, stage="PUBLICATION", issues=combined, output_hash=output_hash, capture=capture)
                rejection = self._rejection(request, "PUBLICATION", combined, candidate, capture)
        return LessonGenerationResult(False, None, audit, rejection, paths)

    def generate(self, request: LessonGenerationRequest, *, output_directory: Path | None = None, rejection_directory: Path | None = None) -> LessonGenerationResult:
        payload = request.as_dict()
        preflight = preflight_issues(payload, self.authority)
        if preflight:
            return self._rejected_result(payload, "PREFLIGHT", preflight, None, rejection_directory)
        config = payload["generation_config"]
        prompt = self.build_prompt(payload)
        try:
            capture = self.backend.generate(prompt, parameters=config["parameters"], seed=config["seed"])
        except Exception as error:
            return self._rejected_result(payload, "PROVIDER", (GenerationIssue("PROVIDER_FAILURE", "$", f"backend raised {type(error).__name__}"),), None, rejection_directory)
        capture_issues = self._capture_issues(capture, prompt, config["parameters"], config["seed"])
        if capture_issues:
            return self._rejected_result(payload, "PROVIDER", capture_issues, None, rejection_directory)
        backend_issues = backend_candidate_issues(capture.content)
        if backend_issues:
            candidate = capture.content if self._safe_hash(capture.content) is not None else None
            return self._rejected_result(payload, "PROVIDER", backend_issues, candidate, rejection_directory, capture)
        candidate = self._assemble(payload, capture.content, capture)
        post = postgeneration_issues(payload, candidate, expected_generation_metadata=self._generation_metadata(payload, capture))
        candidate_hash = self._safe_hash(candidate)
        if post or candidate_hash is None:
            issues = post or (GenerationIssue("BACKEND_RESPONSE_INVALID", "$", "assembled lesson is not finite canonical JSON"),)
            return self._rejected_result(payload, "POSTVALIDATION", issues, candidate if candidate_hash else None, rejection_directory, capture)
        audit = self._audit(payload, accepted=True, stage="COMPLETE", issues=(), output_hash=candidate_hash, capture=capture, publication_attempted=output_directory is not None)
        if output_directory is None:
            return LessonGenerationResult(True, candidate, audit, None, ())
        try:
            paths = publish(output_directory, candidate, audit)
        except (OSError, ValueError, TypeError):
            return self._rejected_result(payload, "PUBLICATION", (GenerationIssue("PUBLICATION_FAILURE", "$", "accepted artifacts could not be published atomically without overwrite"),), candidate, rejection_directory, capture)
        return LessonGenerationResult(True, candidate, audit, None, paths)
