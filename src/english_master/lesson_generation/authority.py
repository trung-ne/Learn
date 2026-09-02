"""Authoritative M5, approval, and source-registry inputs for M6."""

from __future__ import annotations

import copy
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping

from english_master.curriculum_validation.validator import CurriculumBundle, load_bundle
from english_master.schema_validation import load_document, load_source_registry

from .canonical import sha256_json
from .models import JsonObject


@dataclass(frozen=True)
class LessonGenerationAuthority:
    """Inputs loaded independently from the caller's generation request."""

    bundle: CurriculumBundle
    authorization: Mapping[str, Any]
    source_registry: Mapping[str, Any]

    @classmethod
    def from_files(
        cls,
        structure_path: Path,
        authorization_path: Path,
        source_registry_path: Path,
        *,
        graph_path: Path | None = None,
        coverage_path: Path | None = None,
        taxonomy_path: Path | None = None,
    ) -> "LessonGenerationAuthority":
        return cls(
            bundle=load_bundle(
                structure_path,
                graph_path=graph_path,
                coverage_path=coverage_path,
                taxonomy_path=taxonomy_path,
            ),
            authorization=load_document(authorization_path),
            source_registry=load_source_registry(source_registry_path),
        )

    def artifact_hashes(self) -> JsonObject:
        return {
            "structure": sha256_json(self.bundle.structure),
            "graph": sha256_json(self.bundle.graph),
            "coverage": sha256_json(self.bundle.coverage),
            "taxonomy": sha256_json(self.bundle.taxonomy),
            "source_registry": sha256_json(self.source_registry),
        }

    def authorization_dict(self) -> JsonObject:
        return copy.deepcopy(dict(self.authorization))

    def registry_dict(self) -> JsonObject:
        return copy.deepcopy(dict(self.source_registry))
