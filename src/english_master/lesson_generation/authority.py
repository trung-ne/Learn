"""Verified M5 release and development snapshot authority for M6."""

from __future__ import annotations

import copy
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping

from english_master.curriculum_review.loading import load_strict_bundle, load_strict_document
from english_master.curriculum_review.workflow import (
    verify_development_snapshot_bundle,
    verify_snapshot_bundle,
)
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
DEVELOPMENT_SNAPSHOT_MEMBERS = (
    ("manifest", "manifest.json"),
    ("source_registry", "source-registry.json"),
    ("snapshot", "snapshot.json"),
)


def _bundle_from_files(
    structure_path: Path,
    source_registry_path: Path,
    *,
    graph_path: Path | None = None,
    coverage_path: Path | None = None,
    taxonomy_path: Path | None = None,
) -> tuple[CurriculumBundle, Mapping[str, Any]]:
    bundle = load_strict_bundle(structure_path, graph_path=graph_path, coverage_path=coverage_path, taxonomy_path=taxonomy_path)
    return bundle, load_strict_document(source_registry_path.resolve())


@dataclass(frozen=True)
class _VerifiedM5Base:
    bundle: CurriculumBundle
    snapshot: Mapping[str, Any]
    source_registry: Mapping[str, Any]
    member_documents: Mapping[str, Mapping[str, Any]]

    def artifact_hashes(self) -> JsonObject:
        return {
            "structure": sha256_json(self.bundle.structure),
            "graph": sha256_json(self.bundle.graph),
            "coverage": sha256_json(self.bundle.coverage),
            "taxonomy": sha256_json(self.bundle.taxonomy),
            "source_registry": sha256_json(self.source_registry),
        }

    def snapshot_binding(self) -> JsonObject:
        members = {key: sha256_json(self.member_documents[key]) for key in self.member_documents}
        return {
            "snapshot_id": self.snapshot["snapshot_id"],
            "snapshot_sha256": sha256_json(self.snapshot),
            "member_hashes": members,
            "bundle_sha256": sha256_json({filename: self.member_documents[key] for key, filename in self.member_filenames()}),
        }

    def snapshot_dict(self) -> JsonObject:
        return copy.deepcopy(dict(self.snapshot))

    @classmethod
    def member_filenames(cls) -> tuple[tuple[str, str], ...]:
        raise NotImplementedError


@dataclass(frozen=True)
class VerifiedM5Authority(_VerifiedM5Base):
    """Human/release M5 authority. It remains strict and reviewer-registry bound."""

    reviewer_registry: Mapping[str, Any]

    @classmethod
    def member_filenames(cls) -> tuple[tuple[str, str], ...]:
        return SNAPSHOT_MEMBERS

    @classmethod
    def from_files(
        cls, structure_path: Path, snapshot_directory: Path, source_registry_path: Path, reviewer_registry_path: Path,
        *, graph_path: Path | None = None, coverage_path: Path | None = None, taxonomy_path: Path | None = None,
        observed_at: str | None = None,
    ) -> "VerifiedM5Authority":
        bundle, source_registry = _bundle_from_files(structure_path, source_registry_path, graph_path=graph_path, coverage_path=coverage_path, taxonomy_path=taxonomy_path)
        reviewer_registry = load_strict_document(reviewer_registry_path.resolve())
        snapshot = verify_snapshot_bundle(snapshot_directory.resolve(), bundle, reviewer_registry, source_registry=source_registry, source_registry_path=source_registry_path.resolve(), observed_at=observed_at)
        documents = {key: load_strict_document(snapshot_directory.resolve() / filename) for key, filename in SNAPSHOT_MEMBERS}
        return cls(bundle=bundle, snapshot=snapshot, source_registry=source_registry, member_documents=documents, reviewer_registry=reviewer_registry)


@dataclass(frozen=True)
class VerifiedM5DevelopmentAuthority(_VerifiedM5Base):
    """Development-only M5 authority; never a human or release approval."""

    @classmethod
    def member_filenames(cls) -> tuple[tuple[str, str], ...]:
        return DEVELOPMENT_SNAPSHOT_MEMBERS

    @classmethod
    def from_files(
        cls, structure_path: Path, snapshot_directory: Path, source_registry_path: Path,
        *, graph_path: Path | None = None, coverage_path: Path | None = None, taxonomy_path: Path | None = None,
        observed_at: str | None = None,
    ) -> "VerifiedM5DevelopmentAuthority":
        bundle, source_registry = _bundle_from_files(structure_path, source_registry_path, graph_path=graph_path, coverage_path=coverage_path, taxonomy_path=taxonomy_path)
        snapshot = verify_development_snapshot_bundle(snapshot_directory.resolve(), bundle, source_registry=source_registry, source_registry_path=source_registry_path.resolve(), observed_at=observed_at)
        documents = {key: load_strict_document(snapshot_directory.resolve() / filename) for key, filename in DEVELOPMENT_SNAPSHOT_MEMBERS}
        return cls(bundle=bundle, snapshot=snapshot, source_registry=source_registry, member_documents=documents)


@dataclass(frozen=True)
class LessonGenerationAuthority:
    """Verified M5 authority plus an independently loaded narrow authorization."""

    m5: _VerifiedM5Base
    authorization: Mapping[str, Any]

    @classmethod
    def from_files(
        cls, structure_path: Path, authorization_path: Path, source_registry_path: Path, snapshot_directory: Path,
        reviewer_registry_path: Path, *, graph_path: Path | None = None, coverage_path: Path | None = None,
        taxonomy_path: Path | None = None, observed_at: str | None = None,
    ) -> "LessonGenerationAuthority":
        m5 = VerifiedM5Authority.from_files(structure_path, snapshot_directory, source_registry_path, reviewer_registry_path, graph_path=graph_path, coverage_path=coverage_path, taxonomy_path=taxonomy_path, observed_at=observed_at)
        return cls(m5=m5, authorization=load_strict_document(authorization_path.resolve()))

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
