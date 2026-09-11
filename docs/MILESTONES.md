# Milestones — English Master

## Overview

This document outlines the major development milestones for the English Master project.

Each milestone has explicit scope, deliverables, and acceptance criteria.

Milestones are executed sequentially. Do not begin the next milestone until the current one is complete.

---

## M0 — Repository Bootstrap

**Status**: Complete (verified 2026-08-28)

**Duration**: ~2-3 days

**Owner**: AI Agent

### Scope

Create the architectural and specification foundation.

Do NOT crawl, download datasets, or generate curriculum.

### Deliverables

1. Repository structure (docs/, src/, tests/, data/, schemas/, etc.)
2. Specification documents:
   - docs/PROJECT_SPEC.md
   - docs/DATA_POLICY.md
   - docs/CURRICULUM_SCHEMA.md
   - docs/QA_SPEC.md
   - docs/MILESTONES.md
3. JSON Schema files for core models
4. Python 3.12+ project with pytest setup
5. Sample validation fixtures
6. .gitignore with data and secrets protection
7. README.md with build/test commands

### Acceptance Criteria

- [x] All specification documents exist and are complete
- [x] Schemas can be loaded and validated
- [x] Sample schema validation passes
- [x] Invalid sample validation fails correctly
- [x] pytest runs successfully
- [x] No external data has been downloaded
- [x] No curriculum has been generated
- [x] Tests document how to use schemas
- [x] README includes step-by-step setup

### Next: M1

---

## M1 — Source Registry & Data Policy

**Estimated Duration**: ~1 week

**Owner**: AI Agent + Human Research

### Scope

Identify, research, and register authoritative data sources for:

- Public domain texts
- Creative Commons datasets
- Official vocabulary lists
- Academic research data
- Official language resources

Do NOT download large quantities yet.

Do register sources and verify licensing.

### Deliverables

1. sources/registry.json: complete list of approved sources
2. sources/license_summary.md: summary of licensing terms
3. Source documentation for each approved source
4. Research notes on rejected sources (why rejected)
5. Policy for quarantine review

### Acceptance Criteria

- [ ] At least 5 approved sources registered
- [ ] All licensing verified
- [ ] Source registry is machine-readable
- [ ] License summary is accurate
- [ ] Rationale for any rejections documented

### Next: M2

---

## M2 — CEFR Taxonomy & Linguistic Knowledge Model

**Status**: Complete (verified 2026-08-31)

**Owner**: AI Agent + Human Review

### Scope

Build the machine-readable knowledge skeleton that will govern later classification and curriculum work. Model the supported internal CEFR subdivisions, language skills, linguistic and communicative dimensions, vocabulary senses, concept dependencies, Vietnamese learner annotations, and broad CEFR-band coverage.

Do NOT download or ingest source payloads. Do NOT classify a corpus. Do NOT generate curriculum, lessons, exercises, or assessments.

### Deliverables

1. Strict schemas for taxonomy concepts, vocabulary senses, Vietnamese learner annotations, the taxonomy collection, and the coverage matrix
2. A small original-authored representative taxonomy proving every required dimension
3. An explicit notice that `.1` and `.2` tiers are internal subdivisions, not official CEFR levels
4. A broad, confidence-marked coverage matrix without false precision
5. Semantic validators for unique IDs, references, vocabulary-sense identity, and an acyclic prerequisite graph
6. CLI support using the existing offline schema-validation command
7. Tests for schemas, graph semantics, vocabulary integrity, annotations, matrix completeness, and CLI behavior

### Acceptance Criteria

- [x] Taxonomy schemas exist and resolve offline
- [x] All 12 internal CEFR subdivisions are supported and accurately labeled as internal
- [x] Required skills and linguistic dimensions have representative records
- [x] Concept IDs and vocabulary-sense IDs are unique
- [x] Prerequisites and relationships resolve
- [x] The prerequisite graph is acyclic
- [x] Vocabulary senses retain separate identities and CEFR assignments
- [x] Vietnamese learner research claims and pedagogical observations are structurally distinguishable
- [x] Broad CEFR coverage includes confidence and evidence metadata
- [x] Prototype wording and examples are original; references are citations only
- [x] No data was downloaded and no curriculum content was generated
- [x] Tests pass

### Next: M3

---

## M3 — Data Ingestion Pipeline

**Status**: Complete (verified 2026-08-31)

**Estimated Duration**: ~1-2 weeks

**Owner**: AI Agent

### Scope

Build the data ingestion pipeline:

1. Download/export data from approved sources
2. Parse data into normalized form
3. Validate schema
4. Check provenance
5. Deduplicate
6. Store in data/normalized/

Do NOT classify by CEFR yet.

Do NOT generate curriculum yet.

### Deliverables

1. Python CLI: `ingest.py --source <source_id>`
2. Ingestion scripts for each approved source
3. Normalization for vocabulary, concepts, phrases
4. Deduplicate logic
5. data/normalized/ folder structure
6. Ingestion report: how many records, any errors
7. Tests for ingestion pipeline

### Acceptance Criteria

- [x] At least one source fully ingested
- [x] Normalized data is valid
- [x] Duplicate records are detected
- [x] Provenance is preserved
- [x] Ingestion can be reproduced
- [x] Errors are logged
- [x] Tests pass

### Next: M4

### Post-M3 Authorized Real-Record Ingestion Pilot Addendum

**Status**: Implemented contract; blocked pending a genuine authorization and a pinned local official payload

This bounded operational addendum may process 1,000–5,000 English text records from `src_tatoeba_text` only after a hash-bound authorization, local official-download receipt, and record-level attribution/license evidence validate. It uses M3 normalization and M4 duplicate analysis without reopening either milestone.

It is **not M11**. It does not authorize CEFR classification, curriculum generation, lesson/exercise use, `data/approved/` publication, human/release approval, or a network crawler. M11 remains Export & Packaging.

---

## M4 — Normalization and Deduplication

**Status**: Complete (verified 2026-08-31)

**Owner**: AI Agent

### Scope

Build a deterministic post-ingestion stage for strict M3 normalized records:

1. Preserve source text and provenance
2. Create conservative display and lossy comparison representations
3. Calculate separate canonical raw and normalized SHA-256 hashes
4. Detect exact raw and normalized-text duplicate groups
5. Generate bounded, explainable character n-gram candidates
6. Route candidates to explicit human semantic review

Do NOT classify CEFR content, add embeddings or a vector database, or generate curriculum.

### Deliverables

1. Typed `english_master.normalization` package with separated models, text, hash, exact, near, semantic, storage, and pipeline responsibilities
2. Strict schemas for derived records, groups, candidates, review queues/decisions, and reports
3. Offline `python -m english_master.normalize` CLI
4. Atomic, idempotent run storage with no-overwrite behavior
5. Documented normalization, hash, candidate, review, and M3 provenance-verification policies
6. Offline success and failure tests

### Acceptance Criteria

- [x] Normalization is deterministic, Unicode-safe, and idempotent
- [x] Original text, complete provenance, attribution, raw hash, and normalized hash are retained
- [x] Exact raw and normalized-text groups are deterministic
- [x] Inconsistent source identity metadata fails closed
- [x] Near matching uses bounded, same-language character n-gram candidates with evidence
- [x] Short texts and translations have explicit safeguards
- [x] Semantic decisions require a human reviewer and supported disposition
- [x] Derived schemas and cross-record references are validated before publication
- [x] Reruns are idempotent and conflicting/incomplete outputs are rejected
- [x] CLI and tests run offline
- [x] No embeddings, vector database, CEFR classification, or M5 work was added

### Next: M5

---

## M5 — Curriculum Architecture & Dependency Graph

**Status**: Complete (verified 2026-09-02)

**Owner**: AI Agent + Curriculum Designer

### Scope

Design the curriculum structure:

1. Define curriculum units and sequence
2. Group content by CEFR level
3. Build prerequisites and dependencies
4. Verify DAG (no circular dependencies)
5. Design lesson structure and scope
6. Create detailed curriculum roadmap

Do NOT generate lesson content yet.

Do validate curriculum structure.

### Deliverables

1. `curriculum/structure.json`: compact six-band/twelve-tier hierarchy with globally numbered units, lesson outlines, and review nodes
2. `curriculum/prerequisite_graph.json`: explicit typed dependencies and deterministic topological order
3. `curriculum/coverage-roadmap.json`: machine-readable introduction, development, and review coverage
4. Strict M5 schemas and an offline `english_master.curriculum_validate` CLI
5. Tests for schema, hierarchy, references, review gates, graph semantics, coverage, and reproducibility
6. `curriculum/curriculum-graph.dot`: deterministic compact curriculum visualization
7. `docs/CURRICULUM_ARCHITECTURE.md`: design and governance decisions

### Acceptance Criteria

- [x] Curriculum architecture covers A1.1 through C2.2
- [x] Dependency graph is acyclic
- [x] All prerequisites are introduced before dependent use
- [x] Compact lesson outlines and units are balanced and machine-readable
- [x] Scale plan supports an estimated 1,000-1,200 hour expansion without claiming completed content
- [x] Global unit numbering prevents lesson-ID collisions across internal half-tiers
- [x] DRAFT taxonomy dependencies are behind an explicit review gate that blocks M6
- [x] Coverage roadmap represents all required dimensions
- [x] Offline CLI and applicable tests pass
- [x] No M6 lesson content or later-milestone material was generated

### Post-completion M5 review governance

The offline independent-review implementation now provides strict manifest, human-review, reviewer-authority, source-registry, and approval-snapshot contracts; canonical hash binding; taxonomy citation-eligibility and semantic review gates; prepare/publish/verify commands; atomic immutable storage; and blank human checklists. This implementation does not constitute an actual linguistic or pedagogical review, does not change the `DRAFT`/`OUTLINE_ONLY` source bundle, and does not by itself complete M6's outstanding independent-review acceptance criteria.

### Next: M6

---

## M6 — Lesson Generation

**Status**: Complete for development — `DEVELOPMENT_APPROVED` batch and read-only M7 eligibility verified; human/release approval remains a separate, unclaimed gate (2026-09-03)

**Estimated Duration**: ~2-3 weeks

**Owner**: AI Agent (Claude/Codex)

### Scope

Generate lesson content:

1. Use curriculum structure from M5
2. Extract vocabulary and grammar from M4
3. Generate lesson explanations
4. Create lesson structure (sections, media references)
5. Preserve provenance
6. Run QA

Do NOT generate exercises yet.

Do validate lesson content.

### Deliverables

1. curriculum/lessons/ folder with JSON lesson objects
2. Lesson generator script (prompt-based)
3. QA reports: deterministic validation plus independent AI linguistic and pedagogical review evidence
4. Separate strict human/release review workflow (not required for development approval)
5. Rejected/revised lessons
6. Tests for lesson structure

### Acceptance Criteria

Generator repair verification:

- [x] M5 structure, graph, coverage, taxonomy, authorization, registry, versions, and hashes are independently loaded and bound
- [x] Strict M5 validation and a separate independent authorization gate run before backend invocation
- [x] Lesson identity, prerequisite closure, introduction/review edges, and previous knowledge are derived and cross-checked
- [x] External provenance is authorized through the registered source status, identity, license, and permissions
- [x] Shared typed ID contracts and cross-field lesson/unit/tier/sequence checks are enforced
- [x] The backend returns content only; trusted fields and `UNREVIEWED` metadata are injected by orchestration
- [x] Malformed/provider/postvalidation/publication failures produce truthful stage-aware results
- [x] Accepted and rejected artifact bundles use atomic no-overwrite publication
- [x] QA audits identify the automated reviewer and retain outstanding independent-review categories
- [x] Focused offline M6 tests pass
- [x] No M7 or later-milestone implementation was added by the repair

Development M6 content acceptance verified:

- [x] Development M6 authorization is bound to a verified genuine M5 development snapshot; synthetic fixtures cannot satisfy this gate
- [x] At least 10 complete lessons generated in the required graph order
- [x] All lessons pass schema and deterministic machine validation
- [x] All lessons have correct prerequisites and reference scope
- [x] Each lesson has independent AI linguistic and pedagogical review with no major or critical finding
- [x] Available internal originality/copyright checks and their limits are recorded; no Internet-wide search is implied
- [x] Lessons include authorized vocabulary/grammar references
- [x] Immutable development batch QA and the read-only M7 eligibility check pass

`DEVELOPMENT_APPROVED` does not constitute `HUMAN_REVIEWED` or `RELEASE_APPROVED`. Human/release acceptance remains a separate future gate. M6 is complete only for the development lane; M7 is eligible to begin but has not been started.

### Next: M7 is eligible to start; do not start it automatically

---

## M7 — Exercise Generation

**Status**: Complete for the AI-only development lane (verified 2026-09-03); human/release approval remains separate

**Estimated Duration**: ~3 weeks

**Owner**: AI Agent (Claude/Codex)

### Scope

Generate exercise sets only from a verified M6 development-approved lesson batch. Derive exact scope and constraints from the lesson and graph; validate type-specific answer/rubric contracts; preserve provenance; and keep all generated content `UNREVIEWED`. Do not start M8.

### Deliverables

1. Strict M7 authorization/request/candidate/set/audit/rejection schemas and offline package/CLI
2. Immutable lesson-bound exercise sets under `curriculum/exercises/`
3. Type-specific answer, ambiguity, CEFR, prerequisite, duplicate, provenance, copyright, and later-milestone scope-exclusion checks
4. Original authored offline captures and transcript-only listening fixtures; no external media payloads
5. Tests, audit reports, and documented independent-review limits

### Acceptance Criteria

- [x] Exercises consume validated M6 lesson constraints rather than inventing scope
- [x] All supported types have strict type-specific contracts
- [x] Count is a bounded quality target, not a reason to pad or relax QA
- [x] Answer correctness and ambiguity checks reject unsafe publication
- [x] CEFR, prerequisite, reference, duplicate, provenance, and copyright checks are auditable
- [x] Subjective tasks have usable rubrics and remain reviewable
- [x] Invalid output is rejected atomically with no partial accepted set
- [x] Every generated exercise remains `UNREVIEWED` pending independent QA
- [x] Offline CLI and full applicable tests pass
- [x] No M8 or later-milestone implementation is added

The 50-exercise / five-per-lesson figure is a development coverage target for the ten verified M6 lessons, not an approval criterion that overrides correctness, clarity, provenance, or pedagogical value.

### Next: M8 — QA Engine; do not start it automatically

---

## M8 — QA Engine

**Status**: Complete for M8.1 QA Engine and M8.2 lesson-specific AI-practice pilot — development-only evidence verified 2026-09-04; no human or release approval is claimed

**Owner**: AI Agent (Claude/Codex)

### Scope

Validate immutable M7 exercise candidates through the fixed order: schema, answer, CEFR, prerequisite, duplicate, and candidate-bound AI language QA. A content failure publishes immutable rejection evidence and may regenerate a new candidate under a strict attempt limit. A candidate is never edited in place and a failed gate is never manually waived.

M8 independently reloads M5-M7 authority, retains prompts and raw responses for M8 invocations, enforces exact chronology and retry lineage, and publishes one atomic terminal run as `DEVELOPMENT_APPROVED`, `REJECTED`, or `OPERATIONAL_FAILURE`. A pass is development evidence only: exercise content remains `UNREVIEWED`.

### Deliverables

1. Strict request, candidate-attempt, stage-receipt, invocation, AI-review, rejection, operational-failure, decision, and run-manifest schemas
2. Ordered offline QA orchestration with immutable bounded regeneration
3. Learner-facing exact and normalized near-duplicate policy
4. Atomic complete-run publication and independent run-directory verification
5. Offline CLI, adversarial tests, and `prompts/M8_QA_ENGINE.md`

### Acceptance Criteria

- [x] Exact M5, M6, and M7 authority is independently revalidated
- [x] All six stages enforce fixed sequence, reviewer type, and fail-fast `NOT_RUN` behavior
- [x] Attempt 1 is the exact M7 set and retries bind the complete parent rejection and repair constraints
- [x] Fresh regenerated candidates receive candidate-bound AI review after five passing machine stages
- [x] Replay, test, mock, unsupported, or parameter-mismatched evidence cannot promote content
- [x] Duplicate checks exclude volatile metadata while retaining learner-facing semantics
- [x] Approved, rejected, and operational terminal bundles publish atomically and verify independently
- [x] Exact timestamps, prompts, raw responses, identities, hashes, and record chronology fail closed
- [x] Content remains `UNREVIEWED`; `human_reviewed` and `release_approved` remain false
- [x] Focused and full applicable tests pass
- [x] No M5, M6, or M7 immutable artifact is changed

## M8.2 — Lesson-Specific AI Practice Prompt Pilot

**Status**: Complete — forty project-authored, M6-authority-bound prompt artifacts are machine-validated as development evidence only (verified 2026-09-04)

M8.2 is an extension of M8, not M9. It creates four immutable lesson-specific protocols (listening, speaking roleplay, pronunciation, and writing) for each of the exact ten lessons in the verified M6 development batch. Every artifact remains `UNREVIEWED`; the batch can state only `MACHINE_VALIDATED` and never human review, release approval, provider authentication, live-provider behavior, external-media use, or an Internet-wide search.

The pilot independently derives lesson scope, protects listening transcripts, enforces one-question interaction rules, makes pronunciation assessment audio-only with `NOT_ASSESSED` fallback, makes writing draft-first and bounded, and independently verifies a closed 10×4 inventory before atomic publication. See [AI_PRACTICE_PILOT.md](AI_PRACTICE_PILOT.md).

### Next: M9 only after an explicit request

---

## M9 — Independent Review Layer

**Status**: Development lane implemented for a bounded representative sample; human/release lane is available only with genuine verified human evidence

**Owner**: AI Agent (development lane) + optional Human QA Team (human/release lane)

### Scope

M9 has two distinct lanes:

1. **Development lane:** independently reload M5–M8.2 authority, run fresh static machine QA, then retain separate AI linguistic and pedagogical reviews before a hash-bound `DEVELOPMENT_APPROVED` overlay can be published.
2. **Optional human/release lane:** after a verified development overlay, separately validate real registry-bound human linguistic and pedagogical review for `HUMAN_REVIEWED`; a distinct authorized release decision is required for `RELEASE_APPROVED`.

The development lane never waits for a real person, never alters underlying content status, and never claims human review, release approval, provider authentication, live-provider behavior, or an Internet-wide originality search. It reviews lessons, exercise sets, listening prompts, speaking prompts, pronunciation prompts, and writing prompts. M8.2 prompt review is static-protocol review, not observed runtime behavior.

### Deliverables

1. Hash-bound scope manifest and per-content-type machine QA reports
2. Independent AI linguistic and pedagogical review evidence
3. Immutable development batch and read-only verifier
4. Optional human/release contracts and blank workflow documentation
5. Lane-qualified QA reports and M10-consumable findings

### Development acceptance criteria

- [ ] All required artifact types are represented by real immutable artifacts
- [ ] Sample scope and its unreviewed population boundary are explicit
- [ ] Fresh static checks, two AI roles, provenance, and closed inventory are hash-bound
- [ ] Development evidence cannot manufacture human or release approval
- [ ] Human absence does not block development approval
- [ ] Tests and read-only verification pass

A representative development pass is not comprehensive review of unselected content and cannot authorize a release. See [M9_INDEPENDENT_REVIEW.md](M9_INDEPENDENT_REVIEW.md).

### Next: M10 only after an explicit request

---

## M10 — Revision Cycle

**Estimated Duration**: ~2-3 weeks

**Owner**: AI Agent + Subject Matter Experts

### Scope

Fix issues identified in M9:

1. Revise failed content
2. Address QA feedback
3. Re-run QA
4. Approve or escalate

### Deliverables

1. Revised content
2. QA report (second pass)
3. Unresolved issues escalation
4. Final approval list

### Acceptance Criteria

- [ ] >98% of content approved
- [ ] Only critical unresolved issues remain
- [ ] Revisions are auditable

### Next: M11

---

## M11 — Export & Packaging

**Status**: AI-only development export framework implemented but blocked pending a complete version-2 full-population M9 development batch and closed M10 lineage.

**Estimated Duration**: ~1 week

**Owner**: AI Agent

### Scope

Package content for different modalities:

1. Export to a selected LMS package format
2. Export to JSON/CSV for data scientists
3. Create mobile-friendly format
4. Create web-friendly format
5. Create printable materials

### Deliverables

1. Standardized export formats
2. Export scripts
3. Format validation
4. Documentation for using exported materials

### Acceptance Criteria

- [x] All format renderers and strict metadata contracts are implemented and testable offline
- [x] Data integrity is hash-inventoried and independently verifiable
- [x] Export commands are deterministic, atomic, no-overwrite, and require an explicit timestamp
- [x] Current development, representative, escalated, unreviewed, ingestion, and Tatoeba-pilot authority fails closed
- [ ] A complete version-2 full-population `DEVELOPMENT_APPROVED` M9 batch and closed M10 lineage have authorized an M11 package that passes independent verification.

M11 framework completion does not claim that current content is public or export-ready; its only future authority path is the active AI-only development evidence model. See [M11.md](M11.md) and [EXPORT_PACKAGING.md](EXPORT_PACKAGING.md).

### Next: M12 only after an explicit request and a complete, independently verified `DEVELOPMENT_APPROVED` M11 export; do not start operationally or automatically

---

## M12 — Real Audio / Video Corpus Ingestion

**Status**: Preparation only — implementation blocked until M11 has a complete, independently verified `DEVELOPMENT_APPROVED` export

**Estimated Duration**: To be determined before operational work begins

**Owner**: AI Agent

### Gate

M12 must not begin operationally until the M11 authorization, export manifest, and independent verification receipt all validate as `DEVELOPMENT_APPROVED`. This is a development gate, not human review, endorsement, release approval, redistribution authority, or public-release authority.

### Scope

Build a reproducible, permission-aware pipeline for legitimately supplied audio/video records:

1. Source and record-level media permission verification
2. Locally supplied or explicitly authorized acquisition inputs
3. Immutable payload checksums and provenance
4. Media metadata and safe controlled storage
5. Permission-gated derivative lineage
6. Quarantine, closed inventories, and independent verification

Generic crawling, access-control bypass, YouTube URL ingestion, and redistribution without explicit permission are prohibited.

See [M12_MEDIA_INGESTION.md](../prompts/M12_MEDIA_INGESTION.md) for the complete design contract and deferred implementation requirements.

### Acceptance Criteria

- [ ] M11 prerequisite evidence passes independent verification
- [ ] Strict M12 schemas and offline-first commands are implemented
- [ ] Every accepted operation has source- and record-specific permission evidence
- [ ] Original and derivative bytes have immutable checksum-bound lineage
- [ ] Unauthorized, malformed, drifted, or unsafe records fail closed
- [ ] Complete run inventories pass independent verification
- [ ] No output claims curriculum, human-review, redistribution, or release authority without a separate applicable gate

### Next: M13 only after an explicit request and verified operational M12 media authority

---

## M13 — ASR, Transcript, and Timestamp

**Status**: Fixture-only preparation framework complete; operational transcription is blocked pending verified M11 and M12 authority

### Scope

Produce immutable, permission-bound transcript derivatives from authorized controlled-media assets:

1. Verify the parent M12 asset, registry, authorization, and operation-specific permission evidence
2. Run an explicitly configured ASR tool or local deterministic fixture backend
3. Retain transcript text, sentence segmentation, duration-bounded timestamps, and factual tool/model provenance
4. Add optional anonymous within-record speaker segments when separately permitted and evidenced
5. Publish an atomic derivative run with independent verification

Transcript and timestamp generation are separate operations. No speaker identity, voice profile, cross-record linkage, or runtime-provider behavior may be inferred. See [M13_TRANSCRIPTION.md](M13_TRANSCRIPTION.md).

### Acceptance Criteria

- [x] Fixture-only M12 v2 parent media and current operation authority independently verify
- [x] Transcript and timestamp permissions are explicit at source and record scope in fixture contracts
- [x] Sentence segments are deterministic, ordered, duration-bounded, and hash-bound to the parent asset
- [x] Optional speaker labels are anonymous and local to the single artifact
- [x] Fixture-only runs remain clearly non-operational and independently verifiable
- [x] No real ASR, provider call, model download, or source-media processing occurs until predecessor gates pass

The completed fixture framework does not establish an operational M13 transcript, source/media authority, ASR accuracy, or permission to begin M15.

### Next: M14 only after an explicit request and verified M13 output

---

## M14 — Listening Difficulty Analyzer

**Status**: Fixture-only preparation framework complete; operational analysis is blocked pending verified operational M13 output

### Scope

Create auditable, multidimensional listening-difficulty evidence from verified M13 transcripts and measured media evidence. The analyzer must consider lexical difficulty, grammar difficulty, speech rate, utterance length, reductions, connected speech, accent/variety complexity, number of speakers, speaker overlap, noise, and discourse complexity.

It must not assign an overall listening level from vocabulary alone. Each feature records evidence, method/version, score or `NOT_ASSESSED`, confidence, limitations, and contribution to the cautious composite result. See [M14_LISTENING_DIFFICULTY.md](M14_LISTENING_DIFFICULTY.md).

### Acceptance Criteria

- [x] Fixture-only M13 lineage and evidence verify independently before publication
- [x] Every required listening dimension is measured or explicitly `NOT_ASSESSED`
- [x] Vocabulary-only or insufficiently evidenced composites fail closed as `INSUFFICIENT_EVIDENCE`
- [x] Text-only inputs do not invent acoustic or interaction properties
- [x] Profiles, manifests, and verifier receipts are immutable and independently verifiable

The completed fixture framework does not establish measured real-media evidence or operational listening analysis. The curriculum population and A1 blueprint tracks below are separate planning workstreams and do not authorize the existing M15 platform milestone.

### Next: M15-KG-FULL and M16-A1-BLUEPRINT only after an explicit request

---

## M15-KG-FULL — Populate Full Curriculum Knowledge Graph

**Status**: Implemented as a bounded, original-authored development population

M15-KG-FULL creates a separate 120-node, twelve-tier knowledge-graph population covering grammar, vocabulary senses, functions, pronunciation, discourse, pragmatics, collocations, lexical chunks, topics, and skills. It includes deterministic typed prerequisite edges and no lesson prose, exercises, media, or release authority. The M2 prototype and M5 hash-bound architecture remain unchanged. See [M15 prompt](../prompts/M15_CURRICULUM_POPULATION.md).

The bounded population is not exhaustive English coverage, official CEFR endorsement, human/release approval, or M6 generation authority.

### Next: M16-A1-BLUEPRINT

---

## M16-A1-BLUEPRINT — Build Full A1 Curriculum Outline

**Status**: Implemented as an outline-only development blueprint

M16-A1-BLUEPRINT consumes the versioned M15 population and maps A1.1 and A1.2 into units, deterministic lesson IDs, objectives, grammar/vocabulary/pronunciation/function targets, prerequisites, review placements, and assessment blueprints. It contains no lesson prose, exercises, answer keys, media, or M6 authorization. See [M16 documentation](M16_A1_BLUEPRINT.md) and [M16 prompt](../prompts/M16_A1_CURRICULUM.md).

The blueprint is a planning artifact only and does not replace the historical M5 structure or authorize lesson generation.

### Next: existing M15 platform milestone remains separately gated

---

## M15 — Authorized Listening Assembly and Web Platform (Optional, Future)

**Estimated Duration**: ~4-6 weeks

**Owner**: Frontend Team

### Scope

First build authorized listening-exercise assembly from M13/M14 evidence, then build a learner web UI:

- permission-bound media/transcript exercise assembly
- Next.js frontend and TypeScript
- lesson and exercise delivery
- progress tracking and spaced-repetition scheduling

The platform must not expose assets, transcripts, or derivatives beyond their exact permission scope.

### Next: M16

---

## M16 — Production Deployment

**Estimated Duration**: ~1-2 weeks

**Owner**: DevOps + Product

### Scope

Deploy the authorized platform using deterministic security and operational evidence, with recorded AI evidence where applicable. Development evidence is not itself public-release authority.

### Acceptance Criteria

- [ ] Platform is scalable
- [ ] Security is validated
- [ ] User documentation is complete
- [ ] Support process is in place

---

## Summary

**Total Estimated Timeline**: To be revised after M12 duration and downstream schedule are approved

**Core Milestones**: M0 - M11 (most important)

**Future**: M12 - M16 (media ingestion, transcription, listening analysis, web platform, and production deployment)

Each milestone is a deliberate, auditable step toward a complete A1-C2 English learning system.

No milestone is skipped.

No milestone begins operationally until its predecessor’s stated acceptance gate is satisfied; preparation-only design documents do not constitute operational work.

Quality over speed.
