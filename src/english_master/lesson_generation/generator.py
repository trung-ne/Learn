"""Constrained provider-neutral M6 lesson generation orchestration."""

from __future__ import annotations

import copy
import re
from datetime import datetime
from pathlib import Path
from typing import Any, Mapping

from english_master.schema_validation import validate_instance

from .authority import LessonGenerationAuthority
from .canonical import canonical_json, sha256_json
from .models import GenerationIssue, LessonBackend, LessonGenerationRequest, LessonGenerationResult, JsonObject
from .storage import publish, publish_rejection
from .validator import backend_candidate_issues, postgeneration_issues, preflight_issues

CHECK_NAMES = (
    "request_schema",
    "m5_authority",
    "authorization",
    "identity",
    "graph",
    "constraints",
    "provenance_copyright",
    "backend_contract",
    "lesson_schema",
    "cefr_reference_scope",
    "prerequisites",
    "m7_plus_exclusion",
    "publication",
)
PREFLIGHT_CHECKS = CHECK_NAMES[:7]
POST_CHECKS = CHECK_NAMES[8:12]
ISSUE_CHECKS: dict[str, tuple[str, ...]] = {
    "REQUEST_SCHEMA": ("request_schema",),
    "AUTHORIZATION_SCHEMA": ("authorization",),
    "REQUEST_ID_MISMATCH": ("identity",),
    "AUTHORIZATION_ID_MISMATCH": ("authorization", "identity"),
    "AUTHORIZATION_BINDING_MISMATCH": ("authorization", "identity"),
    "ARTIFACT_HASH_MISMATCH": ("m5_authority", "authorization"),
    "VERSION_MISMATCH": ("m5_authority", "authorization"),
    "LESSON_NOT_AUTHORIZED": ("authorization",),
    "M5_CONTENT_GENERATION_BLOCKED": ("m5_authority",),
    "M5_BUNDLE_INVALID": ("m5_authority",),
    "LESSON_NOT_IN_M5": ("m5_authority", "identity"),
    "M5_LESSON_MISMATCH": ("m5_authority", "identity"),
    "IDENTITY_CONTRACT_MISMATCH": ("identity",),
    "AUTHORITATIVE_GRAPH_MISMATCH": ("graph",),
    "GRAPH_CYCLE": ("graph", "prerequisites"),
    "PREVIOUS_KNOWLEDGE_MISMATCH": ("graph", "prerequisites"),
    "PREREQUISITE_SET_MISMATCH": ("graph", "prerequisites"),
    "UNRESOLVED_PREREQUISITE_CLOSURE": ("graph", "prerequisites"),
    "DUPLICATE_AUTHORIZED_ID": ("authorization",),
    "UNRESOLVED_REFERENCE": ("authorization", "cefr_reference_scope"),
    "AUTHORIZED_RECORD_MISMATCH": ("authorization",),
    "SURPLUS_AUTHORIZED_RECORD": ("authorization",),
    "SOURCE_NOT_REGISTERED": ("provenance_copyright",),
    "SOURCE_NOT_APPROVED": ("provenance_copyright",),
    "SOURCE_PERMISSION_DENIED": ("provenance_copyright",),
    "PROVENANCE_MISSING": ("provenance_copyright",),
    "PROVENANCE_REGISTRY_MISMATCH": ("provenance_copyright",),
    "PROVENANCE_CONTENT_HASH_MISMATCH": ("provenance_copyright",),
    "ATTRIBUTION_INCOMPLETE": ("provenance_copyright",),
    "ABOVE_TARGET_CEFR": ("cefr_reference_scope",),
    "CEFR_MISMATCH": ("cefr_reference_scope",),
    "M5_REFERENCE_SCOPE_MISMATCH": ("m5_authority", "cefr_reference_scope"),
    "ALLOWED_SCOPE_MISMATCH": ("constraints", "cefr_reference_scope"),
    "ALLOWED_FORBIDDEN_OVERLAP": ("constraints",),
    "WRONG_REFERENCE_TYPE": ("authorization", "cefr_reference_scope"),
    "TARGET_VOCABULARY_LIMIT": ("constraints",),
    "PROVIDER_FAILURE": ("backend_contract",),
    "BACKEND_RESPONSE_INVALID": ("backend_contract",),
    "BACKEND_SCOPE_VIOLATION": ("backend_contract",),
    "LESSON_SCHEMA": ("lesson_schema",),
    "LESSON_SPEC_MISMATCH": ("identity",),
    "REFERENCE_SCOPE_MISMATCH": ("cefr_reference_scope",),
    "M7_LEAKAGE": ("m7_plus_exclusion",),
    "LATER_MILESTONE_LEAKAGE": ("m7_plus_exclusion",),
    "SECTION_LIMIT": ("constraints",),
    "EMPTY_SECTION": ("constraints",),
    "SECTION_SIZE_LIMIT": ("constraints",),
    "TOTAL_SIZE_LIMIT": ("constraints",),
    "FORBIDDEN_TERM": ("constraints",),
    "UNDECLARED_EMBEDDED_REFERENCE": ("constraints", "cefr_reference_scope"),
    "NONCANONICAL_ORDER": ("constraints",),
    "FORBIDDEN_REFERENCE": ("constraints", "cefr_reference_scope"),
    "GENERATION_METADATA_MISMATCH": ("identity",),
    "PUBLICATION_FAILURE": ("publication",),
    "REJECTION_PERSISTENCE_FAILURE": ("publication",),
}


class LessonGenerator:
    """Validate authority, generate bounded content, inject trust, and publish."""

    def __init__(self, backend: LessonBackend, authority: LessonGenerationAuthority) -> None:
        self.backend = backend
        self.authority = authority

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

    @staticmethod
    def _safe_timestamp(request: Mapping[str, Any], authority: LessonGenerationAuthority) -> str:
        candidates: list[Any] = []
        generation = request.get("generation")
        if isinstance(generation, dict):
            candidates.append(generation.get("generated_at"))
        candidates.append(authority.authorization.get("approved_at"))
        for candidate in candidates:
            if not isinstance(candidate, str):
                continue
            try:
                datetime.fromisoformat(candidate.replace("Z", "+00:00"))
            except ValueError:
                continue
            return candidate
        return "1970-01-01T00:00:00Z"

    @staticmethod
    def _safe_object(value: Any) -> JsonObject:
        if not isinstance(value, dict):
            return {}
        try:
            sha256_json(value)
        except (TypeError, ValueError, OverflowError):
            return {}
        return copy.deepcopy(value)

    @staticmethod
    def _check_outcomes(stage: str, accepted: bool, issues: tuple[GenerationIssue, ...]) -> JsonObject:
        issue_codes = {issue.code for issue in issues}
        if stage == "PREFLIGHT":
            if issue_codes & {"REQUEST_SCHEMA", "AUTHORIZATION_SCHEMA"}:
                ran = {"request_schema", "authorization", "m5_authority"}
            else:
                ran = set(PREFLIGHT_CHECKS)
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
        outcomes: JsonObject = {}
        for name in CHECK_NAMES:
            outcomes[name] = "FAIL" if name in failed else "PASS" if name in ran else "NOT_RUN"
        return outcomes

    def _audit(
        self,
        request: JsonObject,
        *,
        accepted: bool,
        stage: str,
        issues: tuple[GenerationIssue, ...],
        output_hash: str | None,
        publication_attempted: bool = False,
    ) -> JsonObject:
        generation = request.get("generation") if isinstance(request.get("generation"), dict) else {}
        spec = request.get("lesson_spec") if isinstance(request.get("lesson_spec"), dict) else {}
        constraints = request.get("constraints") if isinstance(request.get("constraints"), dict) else {}
        authorization = self.authority.authorization_dict()
        hashes = self.authority.artifact_hashes()
        checks = self._check_outcomes(stage, accepted, issues)
        if accepted and publication_attempted:
            checks["publication"] = "PASS"
        performed = sorted(name for name, outcome in checks.items() if outcome != "NOT_RUN")
        issue_dicts = [issue.as_dict() for issue in issues]
        report: JsonObject = {
            "schema_version": "1.0",
            "request_id": self._safe_identity(request, "request_id", r"req_[a-f0-9]{64}"),
            "lesson_id": self._safe_identity(spec, "id", r"(?:A1|A2|B1|B2|C1|C2)-U(?:0[1-9]|[1-9][0-9])-L(?:0[1-9]|[1-9][0-9])"),
            "status": "ACCEPTED" if accepted else "REJECTED",
            "validation_stage": "COMPLETE" if accepted else stage,
            "input_hashes": {
                "request": self._safe_hash(request),
                "authorization": self._safe_hash(authorization),
                **hashes,
            },
            "versions": {
                "generator": str(generation.get("generator_version", "UNAVAILABLE")),
                "prompt": str(generation.get("prompt_version", "UNAVAILABLE")),
                "curriculum": str(generation.get("curriculum_version", "UNAVAILABLE")),
                "taxonomy": str(generation.get("taxonomy_version", "UNAVAILABLE")),
                "lesson_schema": str(generation.get("lesson_schema_version", "UNAVAILABLE")),
            },
            "constraints_applied": self._safe_object(constraints),
            "generator_metadata": {
                "provider": str(generation.get("provider", "UNAVAILABLE")),
                "model": str(generation.get("model", "UNAVAILABLE")),
                "parameters": self._safe_object(generation.get("parameters", {})),
                "seed": generation.get("seed") if isinstance(generation.get("seed"), int) else None,
            },
            "checks": checks,
            "output_hash": output_hash,
            "qa_status": "UNREVIEWED" if accepted else "REJECTED",
            "qa_reviewer": "english_master.m6_automated_validator",
            "qa_timestamp": self._safe_timestamp(request, self.authority),
            "qa_outcome": "AUTOMATED_CHECKS_PASSED_PENDING_INDEPENDENT_REVIEW" if accepted else "AUTOMATED_CHECKS_FAILED",
            "qa_checks_performed": performed,
            "qa_notes": "Automated M6 checks do not constitute independent linguistic, CEFR, language-quality, or pedagogical approval.",
            "qa_issues_found": issue_dicts,
            "outstanding_independent_reviews": ["CEFR", "GRAMMAR_LEXICAL", "LANGUAGE_QUALITY", "PEDAGOGICAL"],
            "unresolved_issues": issue_dicts,
            "reproducibility": {"canonical_json": True, "byte_identical_claimed": getattr(self.backend, "byte_identical_output", False) is True},
        }
        validate_instance(report, "lesson-generation-audit")
        return report

    def _rejection(self, request: JsonObject, stage: str, issues: tuple[GenerationIssue, ...], candidate: JsonObject | None) -> JsonObject:
        spec = request.get("lesson_spec") if isinstance(request.get("lesson_spec"), dict) else {}
        rejection: JsonObject = {
            "schema_version": "1.0",
            "request_id": self._safe_identity(request, "request_id", r"req_[a-f0-9]{64}"),
            "lesson_id": self._safe_identity(spec, "id", r"(?:A1|A2|B1|B2|C1|C2)-U(?:0[1-9]|[1-9][0-9])-L(?:0[1-9]|[1-9][0-9])"),
            "stage": stage,
            "rejected_at": self._safe_timestamp(request, self.authority),
            "reasons": [issue.as_dict() for issue in issues],
            "request_hash": self._safe_hash(request),
            "candidate_output_hash": self._safe_hash(candidate) if candidate is not None else None,
            "candidate_output": copy.deepcopy(candidate),
            "published": False,
        }
        validate_instance(rejection, "lesson-generation-rejection")
        return rejection

    @staticmethod
    def build_prompt(request: JsonObject) -> str:
        """Create a deterministic prompt that requests only untrusted content sections."""
        return (
            "Return exactly one JSON object with one key, content_sections, and no prose. "
            "The host injects identity, references, versions, timestamps, and QA metadata. "
            "Do not add exercises, assessments, AI prompts, answer keys, or media. REQUEST="
            + canonical_json(request)
        )

    @staticmethod
    def _assemble(request: JsonObject, candidate: JsonObject) -> JsonObject:
        spec = request["lesson_spec"]
        generation = request["generation"]
        return {
            "schema_version": "1.0",
            "id": spec["id"],
            "title": spec["title"],
            "unit_id": spec["unit_id"],
            "lesson_number": spec["lesson_number"],
            "cefr_level": spec["cefr"],
            "duration_minutes": spec["duration_minutes"],
            "objectives": copy.deepcopy(spec["objectives"]),
            "vocabulary_introduced": sorted(spec["vocabulary_introduced"]),
            "grammar_introduced": sorted(spec["grammar_introduced"]),
            "vocabulary_reviewed": sorted(spec["vocabulary_reviewed"]),
            "grammar_reviewed": sorted(spec["grammar_reviewed"]),
            "communicative_functions": sorted(spec["functions_introduced"] + spec["functions_reviewed"]),
            "functions_introduced": sorted(spec["functions_introduced"]),
            "functions_reviewed": sorted(spec["functions_reviewed"]),
            "pronunciation_introduced": sorted(spec["pronunciation_introduced"]),
            "pronunciation_reviewed": sorted(spec["pronunciation_reviewed"]),
            "prerequisites": copy.deepcopy(spec["prerequisites"]),
            "content_sections": copy.deepcopy(candidate["content_sections"]),
            "exercises": [],
            "generation_metadata": {
                "generator": generation["generator"],
                "generator_version": generation["generator_version"],
                "model": generation["model"],
                "prompt_version": generation["prompt_version"],
                "generated_at": generation["generated_at"],
                "curriculum_version": generation["curriculum_version"],
                "qa_status": "UNREVIEWED",
                "qa_notes": "Automated M6 structural checks passed; independent review remains required.",
            },
        }

    def _rejected_result(
        self,
        request: JsonObject,
        stage: str,
        issues: tuple[GenerationIssue, ...],
        candidate: JsonObject | None,
        rejection_directory: Path | None,
    ) -> LessonGenerationResult:
        output_hash = self._safe_hash(candidate) if candidate is not None else None
        audit = self._audit(request, accepted=False, stage=stage, issues=issues, output_hash=output_hash)
        rejection = self._rejection(request, stage, issues, candidate)
        paths: tuple[Path, ...] = ()
        if rejection_directory is not None:
            try:
                paths = publish_rejection(rejection_directory, rejection, audit)
            except (OSError, ValueError, TypeError):
                persistence_issue = GenerationIssue("REJECTION_PERSISTENCE_FAILURE", "$", "rejection artifacts could not be published immutably")
                combined = tuple(sorted(set(issues + (persistence_issue,))))
                audit = self._audit(request, accepted=False, stage="PUBLICATION", issues=combined, output_hash=output_hash)
                rejection = self._rejection(request, "PUBLICATION", combined, candidate)
        return LessonGenerationResult(False, None, audit, rejection, paths)

    def generate(
        self,
        request: LessonGenerationRequest,
        *,
        output_directory: Path | None = None,
        rejection_directory: Path | None = None,
    ) -> LessonGenerationResult:
        payload = request.as_dict()
        preflight = preflight_issues(payload, self.authority)
        if preflight:
            return self._rejected_result(payload, "PREFLIGHT", preflight, None, rejection_directory)
        generation = payload["generation"]
        try:
            raw_candidate = self.backend.generate(self.build_prompt(payload), parameters=generation["parameters"], seed=generation.get("seed"))
        except Exception as error:
            issues = (GenerationIssue("PROVIDER_FAILURE", "$", f"backend raised {type(error).__name__}"),)
            return self._rejected_result(payload, "PROVIDER", issues, None, rejection_directory)
        backend_issues = backend_candidate_issues(raw_candidate)
        if backend_issues:
            safe_candidate = raw_candidate if isinstance(raw_candidate, dict) and self._safe_hash(raw_candidate) is not None else None
            return self._rejected_result(payload, "PROVIDER", backend_issues, safe_candidate, rejection_directory)
        candidate = self._assemble(payload, raw_candidate)
        post = postgeneration_issues(payload, candidate)
        candidate_hash = self._safe_hash(candidate)
        if post or candidate_hash is None:
            issues = post or (GenerationIssue("BACKEND_RESPONSE_INVALID", "$", "assembled lesson is not finite canonical JSON"),)
            return self._rejected_result(payload, "POSTVALIDATION", issues, candidate if candidate_hash is not None else None, rejection_directory)
        audit = self._audit(payload, accepted=True, stage="COMPLETE", issues=(), output_hash=candidate_hash, publication_attempted=output_directory is not None)
        if output_directory is None:
            return LessonGenerationResult(True, candidate, audit, None, ())
        try:
            paths = publish(output_directory, candidate, audit)
        except (OSError, ValueError, TypeError):
            issues = (GenerationIssue("PUBLICATION_FAILURE", "$", "accepted artifacts could not be published atomically without overwrite"),)
            return self._rejected_result(payload, "PUBLICATION", issues, candidate, rejection_directory)
        return LessonGenerationResult(True, candidate, audit, None, paths)
