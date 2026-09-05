"""Trusted M6 authority reconstruction for M8.2 practice prompts."""
from __future__ import annotations

import copy
from dataclasses import dataclass
from pathlib import Path
from types import MappingProxyType
from typing import Any, Mapping

from english_master.exercise_generation.authority import VerifiedM6DevelopmentAuthority
from english_master.lesson_generation.canonical import identity, sha256_json
from english_master.schema_validation import validate_instance

JsonObject = dict[str, Any]
MODALITIES = ("LISTENING", "SPEAKING", "PRONUNCIATION", "WRITING")
EXPECTED_LESSON_COUNT = 10
SUPPORTED_PROMPT_VERSIONS = ("M8_2_AI_PRACTICE_v9",)


@dataclass(frozen=True)
class VerifiedM6PracticeAuthority:
    """Read-only M5/M6 authority narrowed to the complete development batch."""

    m6: VerifiedM6DevelopmentAuthority
    lesson_ids: tuple[str, ...]
    structure_path: Path
    snapshot_directory: Path
    source_registry_path: Path
    m6_batch_path: Path
    m6_root: Path
    m6_batch_sha256: str
    m6_lesson_sha256: Mapping[str, str]
    m6_audit_sha256: Mapping[str, str]
    m6_binding_sha256: Mapping[str, str]
    m5_snapshot_binding_sha256: str
    m5_bundle_sha256: Mapping[str, str]

    def _assert_unchanged(self) -> None:
        """Reject mutation of the reused M6/M5 authority object.

        The upstream authority exposes mappings for read compatibility. M8.2 must
        never publish a batch that only verifies while those mutable mappings are
        still in memory.
        """
        if sha256_json(self.m6.batch) != self.m6_batch_sha256:
            raise ValueError("M8.2 trusted M6 batch mutated after verification")
        if sha256_json(self.m6.m5.snapshot_binding()) != self.m5_snapshot_binding_sha256:
            raise ValueError("M8.2 trusted M5 snapshot binding mutated after verification")
        for lesson_id in self.lesson_ids:
            if sha256_json(self.m6.lesson(lesson_id)) != self.m6_lesson_sha256[lesson_id]:
                raise ValueError(f"M8.2 trusted M6 lesson mutated after verification: {lesson_id}")
            if sha256_json(self.m6.audits[lesson_id]) != self.m6_audit_sha256[lesson_id]:
                raise ValueError(f"M8.2 trusted M6 audit mutated after verification: {lesson_id}")
            if sha256_json(self.m6.binding(lesson_id)) != self.m6_binding_sha256[lesson_id]:
                raise ValueError(f"M8.2 trusted M6 binding mutated after verification: {lesson_id}")
        for name, expected_hash in self.m5_bundle_sha256.items():
            if sha256_json(getattr(self.m6.m5.bundle, name)) != expected_hash:
                raise ValueError(f"M8.2 trusted M5 {name} mutated after verification")

    def reload(self) -> "VerifiedM6PracticeAuthority":
        """Reload every authority member from its independently supplied paths."""
        return type(self).from_files(
            structure_path=self.structure_path,
            snapshot_directory=self.snapshot_directory,
            source_registry_path=self.source_registry_path,
            m6_batch_path=self.m6_batch_path,
            m6_root=self.m6_root,
        )

    @classmethod
    def from_files(
        cls,
        *,
        structure_path: Path,
        snapshot_directory: Path,
        source_registry_path: Path,
        m6_batch_path: Path,
        m6_root: Path,
    ) -> "VerifiedM6PracticeAuthority":
        m6 = VerifiedM6DevelopmentAuthority.from_files(
            structure_path,
            snapshot_directory,
            source_registry_path,
            m6_batch_path,
            m6_root,
        )
        lesson_ids = tuple(entry["lesson_id"] for entry in m6.batch["lessons"])
        if len(lesson_ids) != EXPECTED_LESSON_COUNT or len(set(lesson_ids)) != EXPECTED_LESSON_COUNT:
            raise ValueError("M8.2 requires exactly ten unique M6 development lessons")
        for lesson_id in lesson_ids:
            binding = m6.binding(lesson_id)
            lesson = m6.lesson(lesson_id)
            audit = copy.deepcopy(dict(m6.audits[lesson_id]))
            if sha256_json(lesson) != binding["lesson_sha256"]:
                raise ValueError(f"M6 lesson hash drift: {lesson_id}")
            if sha256_json(audit) != binding["audit_sha256"]:
                raise ValueError(f"M6 audit hash drift: {lesson_id}")
            if audit.get("output_hash") != binding["lesson_sha256"]:
                raise ValueError(f"M6 audit does not bind its lesson output: {lesson_id}")
            if lesson.get("generation_metadata", {}).get("qa_status") != "UNREVIEWED":
                raise ValueError(f"M6 lesson lifecycle status is not UNREVIEWED: {lesson_id}")
        return cls(
            m6=m6,
            lesson_ids=lesson_ids,
            structure_path=structure_path.resolve(),
            snapshot_directory=snapshot_directory.resolve(),
            source_registry_path=source_registry_path.resolve(),
            m6_batch_path=m6_batch_path.resolve(),
            m6_root=m6_root.resolve(),
            m6_batch_sha256=sha256_json(m6.batch),
            m6_lesson_sha256=MappingProxyType({lesson_id: sha256_json(m6.lesson(lesson_id)) for lesson_id in lesson_ids}),
            m6_audit_sha256=MappingProxyType({lesson_id: sha256_json(m6.audits[lesson_id]) for lesson_id in lesson_ids}),
            m6_binding_sha256=MappingProxyType({lesson_id: sha256_json(m6.binding(lesson_id)) for lesson_id in lesson_ids}),
            m5_snapshot_binding_sha256=sha256_json(m6.m5.snapshot_binding()),
            m5_bundle_sha256=MappingProxyType({
                name: sha256_json(getattr(m6.m5.bundle, name))
                for name in ("structure", "graph", "coverage", "taxonomy")
            }),
        )

    def authorization(self, *, created_at: str, prompt_version: str) -> JsonObject:
        self._assert_unchanged()
        if prompt_version not in SUPPORTED_PROMPT_VERSIONS:
            raise ValueError(f"unsupported M8.2 prompt version: {prompt_version}")
        value: JsonObject = {
            "schema_version": "1.0",
            "record_type": "ai_practice_authorization",
            "authorization_id": "PENDING",
            "m6_batch_id": self.m6.batch["batch_id"],
            "m6_batch_sha256": sha256_json(self.m6.batch),
            "snapshot_binding": self.m6.m5.snapshot_binding(),
            "lesson_bindings": [
                {
                    "lesson_id": lesson_id,
                    "lesson_sha256": self.m6.binding(lesson_id)["lesson_sha256"],
                    "audit_sha256": self.m6.binding(lesson_id)["audit_sha256"],
                }
                for lesson_id in self.lesson_ids
            ],
            "policy": {
                "authored_inline_text": "REQUIRED",
                "external_text": "FORBIDDEN",
                "external_media": "FORBIDDEN",
                "provider_authenticated": False,
                "human_reviewed": False,
                "release_approved": False,
            },
            "prompt_version": prompt_version,
            "created_at": created_at,
        }
        value["authorization_id"] = identity("aipauth", value, "authorization_id")
        validate_instance(value, "ai-practice-authorization")
        return value

    def request(
        self,
        lesson_id: str,
        modality: str,
        authorization: Mapping[str, Any],
    ) -> JsonObject:
        self._assert_unchanged()
        if lesson_id not in self.lesson_ids:
            raise ValueError(f"lesson is outside the selected M6 batch: {lesson_id}")
        if modality not in MODALITIES:
            raise ValueError(f"unsupported practice modality: {modality}")
        expected_authorization = self.authorization(
            created_at=authorization.get("created_at"),
            prompt_version=authorization.get("prompt_version"),
        )
        if dict(authorization) != expected_authorization:
            raise ValueError("M8.2 request requires a reconstructable trusted authorization")
        lesson = self.m6.lesson(lesson_id)
        taxonomy = self.m6.m5.bundle.taxonomy
        concepts = {item["id"]: item for item in taxonomy["concepts"]}
        binding = self.m6.binding(lesson_id)

        def typed(ids: list[str], expected: str) -> list[str]:
            values: list[str] = []
            for identifier in ids:
                record = concepts.get(identifier)
                if record is None:
                    raise ValueError(f"unresolved lesson taxonomy reference: {identifier}")
                if record.get("type") == expected:
                    values.append(identifier)
            return values

        # Previous knowledge is derived from the graph-ordered selected M6 batch, not
        # merely the references reviewed in the current lesson.
        position = self.lesson_ids.index(lesson_id)
        previous_lessons = [self.m6.lesson(identifier) for identifier in self.lesson_ids[:position]]

        def prior(field: str) -> list[str]:
            values: list[str] = []
            for previous in previous_lessons:
                values.extend(previous[field])
            values.extend(lesson[field.replace("introduced", "reviewed")])
            return list(dict.fromkeys(values))

        introduced = list(lesson["grammar_introduced"])
        reviewed = prior("grammar_introduced")
        function_targets = list(lesson["functions_introduced"])
        function_known = prior("functions_introduced")
        pronunciation_targets = list(lesson["pronunciation_introduced"])
        pronunciation_known = prior("pronunciation_introduced")
        value: JsonObject = {
            "schema_version": "1.0",
            "record_type": "ai_practice_request",
            "request_id": "PENDING",
            "authorization_id": authorization["authorization_id"],
            "authorization_sha256": sha256_json(authorization),
            "lesson_id": lesson_id,
            "lesson_sha256": binding["lesson_sha256"],
            "lesson_audit_sha256": binding["audit_sha256"],
            "cefr_level": lesson["cefr_level"],
            "modality": modality,
            "objectives": list(lesson["objectives"]),
            "known_vocabulary": prior("vocabulary_introduced"),
            "target_vocabulary": list(lesson["vocabulary_introduced"]),
            "review_vocabulary": list(lesson["vocabulary_reviewed"]),
            "known_grammar": reviewed,
            "target_grammar": introduced,
            "review_grammar": list(lesson["grammar_reviewed"]),
            "known_functions": function_known,
            "target_functions": function_targets,
            "review_functions": list(lesson["functions_reviewed"]),
            "known_pronunciation": pronunciation_known,
            "target_pronunciation": pronunciation_targets,
            "review_pronunciation": list(lesson["pronunciation_reviewed"]),
            "prerequisite_context": list(dict.fromkeys(list(lesson["prerequisites"]) + list(lesson["review_of"]))),
            "taxonomy_context": sorted(set(lesson["taxonomy_concepts"])),
            "source_section_ids": [section["id"] for section in lesson["content_sections"]],
            "scope_types": {
                "target_grammar": typed(introduced, "grammar"),
                "target_functions": typed(function_targets, "communicative_function"),
                "target_pronunciation": typed(pronunciation_targets, "pronunciation"),
            },
            "prompt_version": authorization["prompt_version"],
        }
        if value["scope_types"]["target_grammar"] != introduced:
            raise ValueError(f"lesson grammar target type drift: {lesson_id}")
        if value["scope_types"]["target_functions"] != function_targets:
            raise ValueError(f"lesson function target type drift: {lesson_id}")
        if value["scope_types"]["target_pronunciation"] != pronunciation_targets:
            raise ValueError(f"lesson pronunciation target type drift: {lesson_id}")
        value["request_id"] = identity("aipreq", value, "request_id")
        validate_instance(value, "ai-practice-request")
        return value
