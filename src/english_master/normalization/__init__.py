"""Deterministic post-ingestion normalization and deduplication."""

from english_master.normalization.models import (
    NearDuplicatePolicy,
    NormalizationPolicy,
    ReviewDisposition,
)
from english_master.normalization.pipeline import (
    NormalizationError,
    NormalizationPipeline,
    PipelineConfig,
)

__all__ = [
    "NearDuplicatePolicy",
    "NormalizationError",
    "NormalizationPipeline",
    "NormalizationPolicy",
    "PipelineConfig",
    "ReviewDisposition",
]
