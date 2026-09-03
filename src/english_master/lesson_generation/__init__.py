"""Public M6 lesson-generation API."""

from .authority import LessonGenerationAuthority, VerifiedM5Authority
from .backend import CapturedResponseLessonBackend, FileMockLessonBackend, MockLessonBackend
from .builders import GenerationConfig, build_authorization, build_request
from .canonical import authorization_id, request_id, sha256_json, sha256_text
from .generator import LessonGenerator
from .models import CapturedLessonResponse, GenerationIssue, LessonBackend, LessonGenerationRequest, LessonGenerationResult
from .review import validate_batch_report, validate_lesson_review
from .validator import backend_candidate_issues, postgeneration_issues, preflight_issues

__all__ = [
    "CapturedLessonResponse", "CapturedResponseLessonBackend", "FileMockLessonBackend",
    "GenerationConfig", "GenerationIssue", "LessonBackend", "LessonGenerationAuthority",
    "LessonGenerationRequest", "LessonGenerationResult", "LessonGenerator", "MockLessonBackend",
    "VerifiedM5Authority", "authorization_id", "backend_candidate_issues", "build_authorization",
    "build_request", "postgeneration_issues", "preflight_issues", "request_id", "sha256_json", "sha256_text",
    "validate_batch_report", "validate_lesson_review",
]
