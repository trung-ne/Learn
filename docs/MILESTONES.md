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

**Estimated Duration**: ~3 weeks

**Owner**: AI Agent (Claude/Codex)

### Scope

Generate exercises for lessons:

1. For each lesson, generate exercises
2. Vary exercise types (MC, fill-blank, matching, etc.)
3. Create answer keys
4. Run QA
5. Manual review challenging exercises

### Exercise Types

- Multiple choice
- Fill-in-the-blank
- Matching
- Listening comprehension
- Reading comprehension
- Free response (writing/speaking)

### Deliverables

1. curriculum/exercises/ folder with JSON exercise objects
2. Exercise generator script (type-specific)
3. Answer key validation
4. QA report: answer validation, ambiguity detection, CEFR validity
5. Manual review process output
6. Tests for exercise structure

### Acceptance Criteria

- [ ] At least 50 exercises generated (5 per lesson)
- [ ] Mix of exercise types
- [ ] Answer keys are correct
- [ ] Clarity QA passed
- [ ] CEFR levels appropriate
- [ ] Exercises test correct vocabulary/grammar

### Next: M8

---

## M8 — AI Practice Prompt Generation

**Estimated Duration**: ~1-2 weeks

**Owner**: AI Agent (Claude/Codex)

### Scope

Create AI-driven practice prompts for:

- Listening practice (AI reads, learner listens)
- Speaking practice (AI prompts, learner speaks)
- Pronunciation practice (AI checks pronunciation)
- Writing tutoring (AI gives feedback)

### Deliverables

1. prompts/ folder with JSON prompt templates
2. Prompt generator (system role + template)
3. Evaluation criteria per prompt
4. Tests for prompt structure
5. Sample prompt executions

### Acceptance Criteria

- [ ] At least 20 prompts created
- [ ] Each prompt has clear communicative goal
- [ ] Prompts reference correct vocabulary/grammar
- [ ] Evaluation criteria are reasonable
- [ ] Prompts can be used with Claude API

### Next: M9

---

## M9 — Independent QA

**Estimated Duration**: ~2-4 weeks

**Owner**: Human QA Team

### Scope

Comprehensive QA review:

1. Schema validation (automated)
2. CEFR validation (sampled manual)
3. Grammar/lexical validation (expert review)
4. Pedagogical review (educator review)
5. Copyright/provenance validation (automated)
6. Language quality review (native speaker)

### Deliverables

1. QA report for each content type
2. Identified issues and recommendations
3. Revision requests
4. Revision tickets logged

### Acceptance Criteria

- [ ] All content paths reviewed
- [ ] Critical issues identified
- [ ] >95% content passes automated checks
- [ ] >90% of sample manual review passes
- [ ] Revision queue is prioritized

### Next: M10

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

- [ ] All formats valid
- [ ] Data integrity preserved
- [ ] Export commands are reproducible

### Next: M12

---

## M12 — Web Platform (Optional, Future)

**Estimated Duration**: ~4-6 weeks

**Owner**: Frontend Team

### Scope

Build web UI for learners:

- Next.js frontend
- TypeScript
- Lesson viewer
- Exercise taker
- Progress tracking
- Spaced repetition scheduler

### Note

This is future work. Core curriculum is production-ready before web platform.

### Next: M13

---

## M13 — Production Deployment

**Estimated Duration**: ~1-2 weeks

**Owner**: DevOps + Product

### Scope

Deploy to production:

1. Infrastructure setup
2. Security hardening
3. Load testing
4. Public launch preparation
5. Documentation for users

### Acceptance Criteria

- [ ] Platform is scalable
- [ ] Security is validated
- [ ] User documentation is complete
- [ ] Support process is in place

---

## Summary

**Total Estimated Timeline**: ~4-5 months

**Core Milestones**: M0 - M11 (most important)

**Future**: M12 - M13 (web platform and deployment)

Each milestone is a deliberate, auditable step toward a complete A1-C2 English learning system.

No milestone is skipped.

No milestone is started until the previous one is complete.

Quality over speed.
