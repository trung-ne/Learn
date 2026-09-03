"""Public M6 lesson-generation API."""

from .authority import LessonGenerationAuthority, VerifiedM5Authority, VerifiedM5DevelopmentAuthority
from .backend import CapturedResponseLessonBackend, FileMockLessonBackend, MockLessonBackend
from .builders import GenerationConfig, build_authorization, build_request
from .canonical import authorization_id, request_id, sha256_json, sha256_text
from .development import build_development_batch, publish_development_batch
from .generator import LessonGenerator
from .models import CapturedLessonResponse, GenerationIssue, LessonBackend, LessonGenerationRequest, LessonGenerationResult
from .review import (
    build_ai_review_prompt,
    m7_eligibility_issues,
    validate_ai_lesson_review,
    validate_batch_report,
    validate_development_batch,
    validate_lesson_review,
)
from .validator import backend_candidate_issues, postgeneration_issues, preflight_issues

__all__ = [
    "CapturedLessonResponse", "CapturedResponseLessonBackend", "FileMockLessonBackend",
    "GenerationConfig", "GenerationIssue", "LessonBackend", "LessonGenerationAuthority",
    "LessonGenerationRequest", "LessonGenerationResult", "LessonGenerator", "MockLessonBackend",
    "VerifiedM5Authority", "VerifiedM5DevelopmentAuthority", "authorization_id", "backend_candidate_issues", "build_ai_review_prompt", "build_authorization",
    "build_development_batch", "build_request", "m7_eligibility_issues", "postgeneration_issues", "preflight_issues", "request_id", "sha256_json", "sha256_text",
    "validate_ai_lesson_review", "validate_batch_report", "validate_development_batch", "validate_lesson_review", "publish_development_batch",
]
