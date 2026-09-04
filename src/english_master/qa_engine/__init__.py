"""Immutable, development-only M8 QA Engine."""

from .authority import VerifiedM7QaAuthority
from .orchestrator import QaEngine, QaEngineResult

__all__ = ["QaEngine", "QaEngineResult", "VerifiedM7QaAuthority"]
