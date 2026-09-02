"""Public M6 lesson-generation API."""

from .backend import FileMockLessonBackend, MockLessonBackend
from .canonical import authorization_id, request_id, sha256_json
from .generator import LessonGenerator
from .models import GenerationIssue, LessonBackend, LessonGenerationRequest, LessonGenerationResult
from .validator import postgeneration_issues, preflight_issues

__all__ = [
    "FileMockLessonBackend", "GenerationIssue", "LessonBackend", "LessonGenerationRequest",
    "LessonGenerationResult", "LessonGenerator", "MockLessonBackend", "authorization_id",
    "postgeneration_issues", "preflight_issues", "request_id", "sha256_json",
]
