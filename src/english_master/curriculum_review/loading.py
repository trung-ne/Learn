"""Strict JSON/YAML loading for hash-bound M5 review inputs."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from english_master.curriculum_validation.validator import CurriculumBundle
from english_master.schema_validation import DuplicateMappingKeyError, load_document


def load_strict_document(path: Path) -> dict[str, Any]:
    """Load one JSON/YAML object and reject duplicate mapping keys."""

    return load_document(path)


def load_strict_bundle(
    structure_path: Path,
    *,
    graph_path: Path | None = None,
    coverage_path: Path | None = None,
    taxonomy_path: Path | None = None,
) -> CurriculumBundle:
    """Load all four M5 artifacts with duplicate-key rejection."""

    structure_path = structure_path.resolve()
    structure = load_strict_document(structure_path)
    base = structure_path.parent
    artifacts = structure.get("artifacts", {})
    taxonomy_dependency = structure.get("taxonomy_dependency", {})
    if not isinstance(artifacts, dict):
        artifacts = {}
    if not isinstance(taxonomy_dependency, dict):
        taxonomy_dependency = {}
    resolved_graph = (graph_path or base / str(artifacts.get("graph", "prerequisite_graph.json"))).resolve()
    resolved_coverage = (coverage_path or base / str(artifacts.get("coverage", "coverage-roadmap.json"))).resolve()
    resolved_taxonomy = (taxonomy_path or base / str(taxonomy_dependency.get("path", "taxonomy/taxonomy.json"))).resolve()
    return CurriculumBundle(
        structure=structure,
        graph=load_strict_document(resolved_graph),
        coverage=load_strict_document(resolved_coverage),
        taxonomy=load_strict_document(resolved_taxonomy),
        paths=(structure_path, resolved_graph, resolved_coverage, resolved_taxonomy),
    )
