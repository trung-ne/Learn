"""Public M6 lesson-generation API."""

from .authority import LessonGenerationAuthority
from .backend import FileMockLessonBackend, MockLessonBackend
from .canonical import authorization_id, request_id, sha256_json
from .generator import LessonGenerator
from .models import GenerationIssue, LessonBackend, LessonGenerationRequest, LessonGenerationResult
from .validator import backend_candidate_issues, postgeneration_issues, preflight_issues

__all__ = [
    "FileMockLessonBackend",
    "GenerationIssue",
    "LessonBackend",
    "LessonGenerationAuthority",
    "LessonGenerationRequest",
    "LessonGenerationResult",
    "LessonGenerator",
    "MockLessonBackend",
    "authorization_id",
    "backend_candidate_issues",
    "postgeneration_issues",
    "preflight_issues",
    "request_id",
    "sha256_json",
]
