"""Verified M5 snapshot and independently loaded M6 authorization inputs."""

from __future__ import annotations

import copy
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping

from english_master.curriculum_review.loading import (
    load_strict_bundle,
    load_strict_document,
)
from english_master.curriculum_review.workflow import verify_snapshot_bundle
from english_master.curriculum_validation.validator import CurriculumBundle

from .canonical import sha256_json
from .models import JsonObject

SNAPSHOT_MEMBERS = (
    ("manifest", "manifest.json"),
    ("review_linguistic", "review-linguistic.json"),
    ("review_pedagogical", "review-pedagogical.json"),
    ("reviewer_registry", "reviewer-registry.json"),
    ("source_registry", "source-registry.json"),
    ("snapshot", "snapshot.json"),
)


@dataclass(frozen=True)
class VerifiedM5Authority:
    """M5 state accepted only after full snapshot-bundle reverification."""

    bundle: CurriculumBundle
    snapshot: Mapping[str, Any]
    source_registry: Mapping[str, Any]
    reviewer_registry: Mapping[str, Any]
    member_documents: Mapping[str, Mapping[str, Any]]

    @classmethod
    def from_files(
        cls,
        structure_path: Path,
        snapshot_directory: Path,
        source_registry_path: Path,
        reviewer_registry_path: Path,
        *,
        graph_path: Path | None = None,
        coverage_path: Path | None = None,
        taxonomy_path: Path | None = None,
        observed_at: str | None = None,
    ) -> "VerifiedM5Authority":
        """Independently reload and verify all M5 authority boundaries."""

        bundle = load_strict_bundle(
            structure_path,
            graph_path=graph_path,
            coverage_path=coverage_path,
            taxonomy_path=taxonomy_path,
        )
        resolved_source_path = source_registry_path.resolve()
        source_registry = load_strict_document(resolved_source_path)
        reviewer_registry = load_strict_document(reviewer_registry_path.resolve())
        snapshot = verify_snapshot_bundle(
            snapshot_directory.resolve(),
            bundle,
            reviewer_registry,
            source_registry=source_registry,
            source_registry_path=resolved_source_path,
            observed_at=observed_at,
        )
        documents = {
            key: load_strict_document(snapshot_directory.resolve() / filename)
            for key, filename in SNAPSHOT_MEMBERS
        }
        return cls(
            bundle=bundle,
            snapshot=snapshot,
            source_registry=source_registry,
            reviewer_registry=reviewer_registry,
            member_documents=documents,
        )

    def artifact_hashes(self) -> JsonObject:
        """Return hashes recomputed from independently loaded current inputs."""

        return {
            "structure": sha256_json(self.bundle.structure),
            "graph": sha256_json(self.bundle.graph),
            "coverage": sha256_json(self.bundle.coverage),
            "taxonomy": sha256_json(self.bundle.taxonomy),
            "source_registry": sha256_json(self.source_registry),
        }

    def snapshot_binding(self) -> JsonObject:
        """Bind every retained member and the canonical six-document bundle."""

        members = {
            key: sha256_json(self.member_documents[key])
            for key, _ in SNAPSHOT_MEMBERS
        }
        return {
            "snapshot_id": self.snapshot["snapshot_id"],
            "snapshot_sha256": sha256_json(self.snapshot),
            "member_hashes": members,
            "bundle_sha256": sha256_json(
                {
                    filename: self.member_documents[key]
                    for key, filename in SNAPSHOT_MEMBERS
                }
            ),
        }

    def snapshot_dict(self) -> JsonObject:
        return copy.deepcopy(dict(self.snapshot))


@dataclass(frozen=True)
class LessonGenerationAuthority:
    """Verified M5 authority plus an independently loaded narrow authorization."""

    m5: VerifiedM5Authority
    authorization: Mapping[str, Any]

    @classmethod
    def from_files(
        cls,
        structure_path: Path,
        authorization_path: Path,
        source_registry_path: Path,
        snapshot_directory: Path,
        reviewer_registry_path: Path,
        *,
        graph_path: Path | None = None,
        coverage_path: Path | None = None,
        taxonomy_path: Path | None = None,
        observed_at: str | None = None,
    ) -> "LessonGenerationAuthority":
        m5 = VerifiedM5Authority.from_files(
            structure_path,
            snapshot_directory,
            source_registry_path,
            reviewer_registry_path,
            graph_path=graph_path,
            coverage_path=coverage_path,
            taxonomy_path=taxonomy_path,
            observed_at=observed_at,
        )
        return cls(
            m5=m5,
            authorization=load_strict_document(authorization_path.resolve()),
        )

    @property
    def bundle(self) -> CurriculumBundle:
        return self.m5.bundle

    @property
    def source_registry(self) -> Mapping[str, Any]:
        return self.m5.source_registry

    @property
    def snapshot(self) -> Mapping[str, Any]:
        return self.m5.snapshot

    def artifact_hashes(self) -> JsonObject:
        return self.m5.artifact_hashes()

    def snapshot_binding(self) -> JsonObject:
        return self.m5.snapshot_binding()

    def authorization_dict(self) -> JsonObject:
        return copy.deepcopy(dict(self.authorization))

    def registry_dict(self) -> JsonObject:
        return copy.deepcopy(dict(self.source_registry))
