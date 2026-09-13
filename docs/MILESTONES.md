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

## M9 — Lightweight QA

**Status**: Active free QA workflow.

Run `python -m pytest` for the existing schema, CEFR/reference, prerequisite, answer/ambiguity, and duplicate checks. Directly inspect five representative lesson packets. A factual `M9 DEVELOPMENT: PASS` allows the next explicitly requested development step; paid runners, 120 AI reviews, full-population live review, human review, and release authority are not required.

### Next: M10 only when a checked artifact needs revision

---

## M10 — Revision

**Status**: Active lightweight revision workflow; historical governance records are retained separately.

For a failed artifact, preserve the predecessor, publish a corrected revision at a new path, retain a short predecessor-hash/finding note, and run the relevant validator/tests. No supersession system, M9 import, broad dependency rebuild, or fresh whole-population review is required.

### Next: M11 when a local batch export is requested

---

## M11 — Export & Packaging

**Status**: Local-batch export implemented alongside legacy authority verification.

### Scope

Package one locally declared batch into JSON, CSV, static web, and static mobile output. Print and IMS Common Cartridge are optional. The batch validates schema-valid inputs, hashes, source permissions, closed inventory, deterministic rendering, and no-overwrite publication.

### Routine development boundary

The local-batch command does not require M9 full-population review, M10 closure, `DEVELOPMENT_APPROVED`, human review, or release authority. Output remains `UNREVIEWED` and does not authorize public distribution.

### Next: M12 local pilot can validate explicitly listed licensed local files

---

## M12 — Real Audio / Video Corpus Ingestion

**Status**: Local-pilot manifest validator implemented; no real payload has been processed.

### Scope

Validate a supplied pilot of 10–30 local audio/video files. Each record retains source, URL/local locator, license, attribution, SHA-256, and explicit storage/transcript/timestamp permissions. The validator does not fetch URLs, discover unlisted files, download models, or process media.

### Acceptance Criteria

- [x] A local manifest validates count, unique IDs, safe paths, license/source fields, permissions, and exact hashes.
- [ ] A licensed local 10–30 file pilot is supplied and validated.
- [ ] A real-media run is explicitly requested.

### Next: M13 can process an explicit 10–20-record local selection with a supplied local ASR backend

---

## M13 — Transcript and Timestamp

**Status**: Local-pilot transcript tooling implemented; no real ASR run has occurred.

A caller-controlled local ASR backend can process an explicit 10–20-record selection from a validated M12 local manifest. It retains factual tool/model provenance, rejects reported network use, enforces transcript/timestamp permission and duration-bounded ordered segments, and uses anonymous speaker labels. It does not bundle or download a model.

### Next: M14 can compute simple local-pilot metrics from a supplied transcript artifact

---

## M14 — Listening Metrics

**Status**: Local-pilot metrics tooling implemented; no real transcript artifact has been analyzed.

The local metric module computes only speech rate, vocabulary proxies, grammar-complexity proxies, length measures, and anonymous speaker count. It does not produce CEFR levels, a composite score, diarization-quality claims, or model judgments.

### Next: M15-KG-FULL and M16-A1-BLUEPRINT use focused reference/prerequisite validation

---

## M15-KG-FULL — Populate Full Curriculum Knowledge Graph

**Status**: Implemented as a bounded, original-authored development population

M15-KG-FULL creates a separate 120-node, twelve-tier knowledge-graph population covering grammar, vocabulary senses, functions, pronunciation, discourse, pragmatics, collocations, lexical chunks, topics, and skills. Its active validation checks that IDs and dependency endpoints resolve and that prerequisites are acyclic. It includes no lesson prose, exercises, media, or release authority. See [M15 prompt](../prompts/M15_CURRICULUM_POPULATION.md).

The bounded population is not exhaustive English coverage, official CEFR endorsement, human/release approval, or M6 generation authority.

### Next: M16-A1-BLUEPRINT

---

## M16-A1-BLUEPRINT — Build Full A1 Curriculum Outline

**Status**: Implemented as an outline-only development blueprint

M16-A1-BLUEPRINT consumes the versioned M15 population and maps A1.1 and A1.2 into units, deterministic lesson IDs, objectives, grammar/vocabulary/pronunciation/function targets, prerequisites, review placements, and assessment blueprints. Its active validation resolves all references, rejects broken/non-forward prerequisites, and requires existing concept IDs. It contains no lesson prose, exercises, answer keys, media, or M6 authorization. See [M16 documentation](M16_A1_BLUEPRINT.md) and [M16 prompt](../prompts/M16_A1_CURRICULUM.md).

The blueprint is a planning artifact only and does not replace the historical M5 structure or authorize lesson generation.

### A1 pilot follow-up

**Status**: Implemented as a bounded development pilot

The A1 pilot derives the first ten A1.1 M16 outline lessons into ten original-authored learner packets. Every packet contains lesson content, exercises, and listening, speaking, pronunciation, and writing practice protocols. The pilot validates source hashes, ordered prerequisites, exact four-modality inventory, answer/rubric completeness, duration bounds, duplicate learner-facing text, and closed immutable inventory. A direct user-plus-AI review template covers clarity, grammar, vocabulary difficulty, exercise quality, prompt usability, duration, and duplication; systemic findings identify a generator rule to repair. The pilot remains `UNREVIEWED` and makes no human/release/provider or real-media claim. See [A1 Pilot](A1_PILOT.md).

### Full A1 implementation follow-up

**Status**: Implemented as a complete fifty-lesson development corpus

The isolated Full A1 v2 path preserves the pilot and adds an original-authored granular allocation across the exact ten M16 units and fifty A1.1/A1.2 lessons. Ten hash-bound content files build fifty immutable learner packets with structured exercises and all four practice protocols. Read-only verification reconstructs every packet from M15, M16, allocation, and content inputs. A lightweight full-population audit reports deterministic reference, prerequisite, tier/scope, exercise, media-boundary, claim-boundary, and exact-duplicate checks; a passing report can feed a reproducible 10–15 lesson SHA-256-ranked unit-stratified sample. Everything remains `UNREVIEWED`, uses no network/live AI/external media, and creates no human, release, or provider claim. See [Full A1](A1_FULL.md).

### Next: direct use of the deterministic twelve-lesson Full A1 sample

---

## M16-A2-BLUEPRINT — Build Full A2 Curriculum Outline

**Status**: Implemented as an outline-only development blueprint

M16-A2-BLUEPRINT maps the existing M15 A2.1/A2.2 nodes into ten units, fifty deterministic lesson outlines, explicit review lessons, and unit-test blueprints. It uses only hash-bound M15 node references and their direct A1.2 entry prerequisites; it does not add an A1 authority bridge. Local validation resolves node IDs, checks target tier/dimension and introduction/review coverage, rejects broken or forward prerequisites, and detects cycles. It contains no lesson prose, exercises, answer keys, media, or M6 authorization. See [A2 documentation](A2_BLUEPRINT.md) and [A2 prompt](../prompts/A2_BLUEPRINT.md).

The blueprint is a planning artifact only. It does not replace historical curriculum structures, authorize lesson generation, claim CEFR endorsement, or establish human/release/provider authority.

### A2 pilot follow-up

**Status**: Implemented as a bounded ten-lesson development pilot

The pilot builds the first two A2.1 units into immutable packets with exercises and four AI-practice protocols. Deterministic verification, audit, and a five-lesson unit-stratified sample pass; content remains `UNREVIEWED` and no live-provider, human, release, or public-distribution claim is made. See [A2 Pilot](A2_PILOT.md).

### Full A2 implementation follow-up

**Status**: Implemented as a complete fifty-lesson development corpus

Full A2 adds ten original-authored unit files and fifty immutable A2.1/A2.2 packets derived from the M16 A2 blueprint. Source hashes, references, prerequisites, exercise answer contracts, modality boundaries, duplicates, verification, and a 12-lesson ten-unit sample pass in the lightweight development workflow. Content remains `UNREVIEWED`; no live AI, human/release/provider, CEFR-endorsement, public-distribution, or real-media claim is made. See [Full A2](A2_FULL.md).

### Next: direct use of the deterministic A2 sample

---

## M16-B1-BLUEPRINT — Build Full B1 Curriculum Outline

**Status**: Implemented as an outline-only development blueprint

M16-B1-BLUEPRINT maps the existing M15 B1.1/B1.2 nodes into ten units, fifty deterministic lesson outlines, explicit review lessons, and unit-test blueprints. It hash-binds the M15 population and uses only direct A2.2 entry prerequisites; it does not add an A2 authority bridge. Local validation resolves node IDs, checks target tier/dimension and introduction/review coverage, rejects broken or forward prerequisites, and detects cycles. It contains no lesson prose, exercises, answer keys, media, practice protocols, or generation authority. See [B1 documentation](B1_BLUEPRINT.md) and [B1 prompt](../prompts/B1_BLUEPRINT.md).

The blueprint is planning material only and does not replace historical curriculum structures or establish generation authority.

### Full B1 implementation follow-up

**Status**: Implemented as a complete fifty-lesson development corpus

Full B1 adds ten original-authored unit files and fifty immutable B1.1/B1.2 packets derived from the M16 B1 blueprint. Source hashes, references, prerequisites, exercise answer contracts, modality boundaries, duplicates, verification, and a 12-lesson ten-unit sample pass in the lightweight development workflow. Content remains `UNREVIEWED`; no live AI, human/release/provider, CEFR-endorsement, public-distribution, or real-media claim is made. See [Full B1](B1_FULL.md).

### Next: direct use of the deterministic B1 sample

---

## M16-B2-BLUEPRINT — Build Full B2 Curriculum Outline

**Status**: Implemented as an outline-only development blueprint

M16-B2-BLUEPRINT maps the M15 B2.1/B2.2 nodes into ten units, fifty deterministic lesson outlines, explicit review lessons, and unit-test blueprints. It hash-binds the M15 population and uses direct B1.2 entry prerequisites without loading a B1 blueprint or creating an authority bridge. Validation checks references, exact target coverage, links, prerequisite order, and cycles. See [B2 documentation](B2_BLUEPRINT.md) and [B2 prompt](../prompts/B2_BLUEPRINT.md).

### Full B2 implementation follow-up

**Status**: Implemented as a complete fifty-lesson development corpus

Full B2 adds ten original-authored unit files and fifty immutable B2.1/B2.2 packets derived from the M16 B2 blueprint. Source hashes, references, prerequisites, exercise answer contracts, modality boundaries, duplicates, verification, and a 12-lesson ten-unit sample pass in the lightweight development workflow. Content remains `UNREVIEWED`; no live AI, human/release/provider, CEFR-endorsement, public-distribution, or real-media claim is made. See [Full B2](B2_FULL.md).

### Next: direct use of the deterministic B2 sample

## M16-C1-BLUEPRINT — Build Full C1 Curriculum Outline

**Status**: Implemented as an outline-only development blueprint

M16-C1-BLUEPRINT maps the M15 C1.1/C1.2 nodes into ten units, fifty deterministic lesson outlines, explicit review lessons, and unit-test blueprints. It hash-binds the M15 population and uses direct B2.2 entry prerequisites without loading a B2 blueprint or creating an authority bridge. Validation checks references, exact target coverage, links, prerequisite order, and cycles. See [C1 documentation](C1_BLUEPRINT.md) and [C1 prompt](../prompts/C1_BLUEPRINT.md).

### Full C1 implementation follow-up

**Status**: Implemented as a complete fifty-lesson development corpus

Full C1 adds ten original-authored unit files and fifty immutable C1.1/C1.2 packets derived from the M16 C1 blueprint. Source hashes, references, prerequisites, exercise answer contracts, modality boundaries, duplicates, verification, and a 12-lesson ten-unit sample pass in the lightweight development workflow. Content remains `UNREVIEWED`; no live AI, human/release/provider, CEFR-endorsement, public-distribution, or real-media claim is made. See [Full C1](C1_FULL.md).

### Next: direct use of the deterministic C1 sample

## M16-C2-BLUEPRINT — Build Full C2 Curriculum Outline

**Status**: Implemented as an outline-only development blueprint

M16-C2-BLUEPRINT maps the M15 C2.1/C2.2 nodes into ten units, fifty deterministic lesson outlines, explicit review lessons, and unit-test blueprints. It hash-binds the M15 population and uses direct C1.2 entry prerequisites without loading a C1 blueprint or creating an authority bridge. Validation checks references, exact target coverage, links, prerequisite order, and cycles. See [C2 documentation](C2_BLUEPRINT.md) and [C2 prompt](../prompts/C2_BLUEPRINT.md).

### Full C2 implementation follow-up

**Status**: Implemented as a complete fifty-lesson development corpus

Full C2 adds ten original-authored unit files and fifty immutable C2.1/C2.2 packets derived from the M16 C2 blueprint. Source hashes, references, prerequisites, exercise answer contracts, modality boundaries, duplicates, verification, and a 12-lesson ten-unit sample pass in the lightweight development workflow. Content remains `UNREVIEWED`; no live AI, human/release/provider, CEFR-endorsement, public-distribution, or real-media claim is made. See [Full C2](C2_FULL.md).

### Next: direct use of the deterministic C2 sample

---

## Cross-level A1-C2 QA

**Status**: Implemented as an offline deterministic development consistency check.

The cross-level QA package independently reuses the six Full A1–C2 verifiers, requires the exact ordered 300-packet inventory and a common M15 population hash, and reports target linkage, global prerequisite/M15 ordering, learner-text duplicate candidates, topic candidates, modality boundaries, and structural difficulty-jump diagnostics. Its request, report, and deterministic flagged-region manifest are hash-bound and no-overwrite. The manifest makes no API call; all source and derived records remain `UNREVIEWED`. See [Cross-level QA](CROSS_LEVEL_QA.md).

---

## Assessment + Mastery

**Status**: Implemented as an offline deterministic development layer.

The assessment package reverifies the six Full A1–C2 corpora and common M15 binding, then projects existing objective no-media exercises without rewriting source content. Its immutable inventory contains exactly 300 lesson quizzes, 60 unit tests, six band tests, and one 24-item placement package. Objective scoring updates only caller-owned local JSON concept state with the seven fields documented in [Assessment and Mastery](ASSESSMENT_MASTERY.md).

All packages and source content remain `UNREVIEWED`. The placement `suggested_start_tier` is a fixed offline heuristic, not a validated diagnostic, learner-proficiency claim, official CEFR endorsement, human/release decision, or provider/live-AI evidence. No external media or data is used.

Adaptive Review follow-up is implemented as a separate local planner. It references existing lesson-quiz items, persists recent mistakes and interval stages in caller-owned state, and uses the fixed 1/3/7/14/30/60-day ladder. It does not change the 367-package inventory or complete the future platform milestone.

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
