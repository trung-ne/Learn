# English Master

English Master is a reproducible, self-study English learning-system pipeline for CEFR A1 through C2. Its primary learners are Vietnamese learners of English.

## Current scope: development tooling through M16

The completed foundation provides:

- JSON Schema definitions for core records, source governance, M2 taxonomy collections, and normalized external text.
- A typed, offline JSON/YAML validator with semantic taxonomy checks and a fail-closed source-permission gate.
- Tiny artificial fixtures, a small original-authored taxonomy prototype, and pytest coverage.
- An official-evidence-backed source registry with separate text, audio, and video rights decisions.
- A representative concept DAG, sense-aware vocabulary model, Vietnamese learner annotation layer, and broad confidence-marked CEFR coverage matrix.
- A typed adapter registry and failure-safe ingestion pipeline with one bounded offline `src_tatoeba_text` adapter.
- A deterministic post-ingestion normalization pipeline with dual hashes, exact groups, bounded character n-gram candidates, and an explicit semantic review queue.
- A compact A1.1-C2.2 curriculum architecture with globally numbered units, outline-only lessons, review nodes, typed dependency edges, and machine-readable dimension coverage.
- An offline curriculum validator that reuses the schema engine and enforces hierarchy, taxonomy-review gates, references, ordering, DAG, review, coverage, and reproducibility rules.
- A provider-neutral M6 generation boundary and separate, hash-bound development approval lane. It independently loads M5 artifacts and source authority; derives scope; injects trusted metadata; emits stage-aware audits; retains factual AI-review evidence; and uses atomic no-overwrite artifact bundles. `DEVELOPMENT_APPROVED`, if earned, never means human review or release approval.
- An M8 QA Engine development gate that records ordered schema, answer, CEFR, prerequisite, duplicate, and candidate-bound AI language QA receipts; failures create immutable rejection and regeneration lineage rather than editing candidates. Successful decisions are `DEVELOPMENT_APPROVED` only and keep content `UNREVIEWED`.
- An M8.2 immutable lesson-specific AI-practice pilot: forty M6-authority-bound listening, speaking, pronunciation, and writing protocols, independently reconstructed and machine-validated while content remains `UNREVIEWED`.
- Active M9 uses the complete pytest suite plus a recorded direct inspection of five representative lesson packets. It requires neither paid/live AI, human review, nor release approval; the previous full-population contracts remain available only for existing immutable records.
- M10 creates a corrected successor rather than changing a predecessor and reruns only the validation relevant to that correction.
- M11 provides direct local-batch export to deterministic JSON, RFC-4180 CSV, static web, and static mobile; print and IMS are optional. It validates paths, hashes, input schemas, source permissions, closed inventories, and preserved `UNREVIEWED` lifecycle, without an M9/M10 or release-authority gate.
- M12 validates a manifest for 10–30 explicitly listed, licensed local media files. M13 provides a caller-controlled local-ASR interface for 10–20 selected records, and M14 computes only basic offline transcript metrics. No real media or ASR model is processed until licensed local inputs and a local ASR backend/model path are supplied.
- M15/M16 validate graph and blueprint IDs, references, prerequisite integrity, and population binding without requiring an exact regenerated-object match.
- Data-lifecycle directory scaffolding and Git protections.

M3 is ingestion infrastructure, not a corpus project. M4 adds deterministic normalization and review-oriented deduplication only. M5 adds architecture and dependency planning only. M6 adds constrained lesson generation and an independent development lane; it does not automatically approve lessons, exercises, assessments, or AI prompts. These stages do not crawl websites or bulk-download data or media. The committed ingestion fixture sentences are invented and explicitly used only to test the documented Tatoeba-shaped input path. The strict human/release lane still rejects the DRAFT M5 source bundle without genuine independent human evidence. The separate M5 development snapshot may authorize bounded M6 development only, preserving those source states and never creating human/release claims.

A separately implemented **Post-M3 Authorized Real-Record Ingestion Pilot** can process a local, pinned official `src_tatoeba_text` payload only after a hash-bound authorization and receipt validate. It is not M11 (which remains Export & Packaging), never makes network requests, accepts 1,000–5,000 English text records, and leaves all raw, normalized, and deduplication artifacts gitignored and `UNREVIEWED`. It cannot publish to `data/approved/` or create learning material. See [the pilot operator contract](prompts/M11_REAL_DATA_INGESTION.md).

## Requirements

- Python 3.12 or newer

## Setup

```bash
python --version
python -m venv .venv
```

Activate the environment:

```powershell
.\.venv\Scripts\Activate.ps1
```

```bash
python -m pip install --upgrade pip
python -m pip install -e ".[dev]"
```

## Run tests

```bash
python -m pytest
```

## Validate a record

A valid fixture exits with status `0`:

```bash
python -m english_master.schema_validation --schema lesson tests/fixtures/valid/lesson.json
```

An invalid fixture prints a path-aware validation error and exits nonzero. That nonzero status is expected:

```bash
python -m english_master.schema_validation --schema lesson tests/fixtures/invalid/lesson.json
```

The installed command is equivalent:

```bash
english-master-validate --schema lesson tests/fixtures/valid/lesson.json
```

## Validate source governance

Validate the committed YAML registry:

```bash
python -m english_master.schema_validation --schema source-registry sources/registry.yaml
```

Check a proposed future operation. The command exits `0` only when the named source is exactly `APPROVED` and grants the particular operation; all other cases fail closed:

```bash
python -m english_master.schema_validation --schema source-registry \
  --require-source-permission src_tatoeba_text ingest_text sources/registry.yaml
```

See [sources/license_summary.md](sources/license_summary.md) for decisions and [sources/approved_sources.md](sources/approved_sources.md) for operation-specific restrictions. These commands validate governance only; they do not download data.

## Validate the M2 taxonomy

Validate the complete taxonomy with schema, ID, reference, vocabulary-integrity, and cycle checks:

```bash
python -m english_master.schema_validation --schema taxonomy curriculum/taxonomy/taxonomy.json
```

Validate broad CEFR-band coverage and matrix completeness:

```bash
python -m english_master.schema_validation --schema coverage-matrix curriculum/taxonomy/coverage-matrix.json
```

Both commands are offline and read-only.

## Run bounded M3 ingestion

The M3 adapter accepts only a small local fixture and has no network mode:

```bash
python -m english_master.ingest \
  --source src_tatoeba_text \
  --input tests/fixtures/ingestion/tatoeba_text_valid.tsv \
  --max-records 2 \
  --retrieved-at 2026-08-31T12:00:00Z \
  --offline-fixture
```

The command retains exact raw bytes, validates every normalized record, atomically publishes the run, and prints its report location. It exits nonzero for denied permissions, invalid or over-limit input, any rejected record, schema failure, or write failure. See [docs/INGESTION.md](docs/INGESTION.md) for the adapter contract, canonical field origins, storage layout, and failure semantics.

## Run M4 normalization and deduplication

Process a bounded M3 run without network access:

```bash
python -m english_master.normalize \
  --input data/normalized/src_tatoeba_text/runs/<m3-run-id> \
  --output-root data/deduplicated \
  --processed-at 2026-08-31T12:00:00Z \
  --max-records 10000 \
  --ngram-size 3 \
  --near-threshold 0.85
```

M4 preserves source text and provenance, emits separate raw and normalized SHA-256 hashes, creates exact duplicate groups, and sends bounded same-language n-gram candidates to review. See [docs/NORMALIZATION.md](docs/NORMALIZATION.md) for policies, safeguards, output layout, and the M3 source-hash verification limitation.

## Validate the M5 curriculum architecture

Validate the structure, explicit graph, coverage roadmap, and referenced taxonomy together without network access:

```bash
python -m english_master.curriculum_validate curriculum/structure.json
```

To regenerate the committed deterministic report:

```bash
python -m english_master.curriculum_validate curriculum/structure.json \
  --report curriculum/validation-report.json
```

M5 contains a compact outline-only architecture: 12 globally numbered representative units, 24 lesson outlines, and 12 review nodes across all internal tiers. The 1,000-1,200 hour scale range is an expansion estimate, not completed content. The strict human/release M6 lane requires a genuine human approval snapshot. A separate deterministic M5 development snapshot may authorize bounded development while leaving the taxonomy `DRAFT` and outlines `OUTLINE_ONLY`. See [docs/CURRICULUM_ARCHITECTURE.md](docs/CURRICULUM_ARCHITECTURE.md).

Prepare a hash-bound packet for independent human review, with the current strict source registry independently loaded and all taxonomy citations checked for reference eligibility. Publish or verify an immutable snapshot only after real linguistic and pedagogical submissions exist:

```bash
python -m english_master.curriculum_review prepare curriculum/structure.json --source-registry sources/registry.yaml --output <new-manifest-directory>
python -m english_master.curriculum_review publish curriculum/structure.json --source-registry sources/registry.yaml --manifest <manifest.json> --linguistic-review <review.json> --pedagogical-review <review.json> --reviewer-registry <trusted-reviewer-registry.json> --approved-at <ISO-8601> --published-by <publisher-id> --output <new-snapshot-directory>
python -m english_master.curriculum_review verify curriculum/structure.json --source-registry sources/registry.yaml --snapshot <snapshot-directory> --reviewer-registry <trusted-reviewer-registry.json>
```

The repository includes blank forms for the separate strict human/release lane. The deterministic development snapshot is not a human review or approval. See [docs/M5_REVIEW_WORKFLOW.md](docs/M5_REVIEW_WORKFLOW.md).

## Run constrained M6 lesson generation

M6 accepts either a reverified strict human/release snapshot (with independently loaded reviewer and source registries) or an explicitly selected reverified M5 development snapshot. Both require a prompt-hash-bound captured response and reject arbitrary caller-authored request, authorization, or mock-response files. The development lane is never release authority:

```bash
python -m english_master.lesson_generate --development \
  --lesson-id A1-U01-L01 \
  --snapshot-dir data/reviews/m5/development \
  --captured-response <session-captured-response.json> \
  --output-dir <new-immutable-bundle-directory>
```

Use the existing strict human/release invocation, including `--reviewer-registry`, only when a genuine verified human snapshot exists.

The command reconstructs the exact M6 authorization and request from the verified snapshot and current M5 bundle before a backend is called. It injects only trusted lesson metadata, validates the assembled candidate, and atomically publishes `lesson.json` and `audit.json` on success. Add `--rejection-dir <directory>` to retain an immutable rejection-plus-audit bundle.

No human/release snapshot or human/release approval exists yet. The development lane has a verified M5 snapshot, ten session-captured M6 lesson bundles, twenty AI review records, and one hash-bound `DEVELOPMENT_APPROVED` batch. M7 has a separate hash-bound AI-only `DEVELOPMENT_APPROVED` batch of ten `UNREVIEWED` five-exercise sets; it remains distinct from human/release evidence. See [docs/EXERCISE_GENERATION.md](docs/EXERCISE_GENERATION.md).

## Run constrained M7 exercise generation

M7 rebuilds a lesson request from the verified M6 batch, accepts only a prompt-bound captured response, injects trusted IDs and metadata, and atomically publishes a complete `exercise-set.json` plus `audit.json`. Initial M7 development artifacts use only original inline project-authored stimuli and transcript-only listening tasks; no external text/media operation is exercised.

```bash
python -m english_master.exercise_generate \
  --lesson-id A1-U01-L01 \
  --captured-response curriculum/exercises/captures/20260903-development-v1/A1-U01-L01.json \
  --output-dir curriculum/exercises/development-20260903-v1/A1-U01-L01
```

The command exits `0` when a complete unreviewed set is published, `1` for content rejection, and `2` for authority/setup/persistence failure. See [docs/EXERCISE_GENERATION.md](docs/EXERCISE_GENERATION.md) for type-specific contracts, QA limits, and future external-media requirements.

## Run M8 QA Engine

M8 independently revalidates the exact M5-M7 development authority, executes six fixed QA stages, and atomically publishes a complete `DEVELOPMENT_APPROVED`, `REJECTED`, or `OPERATIONAL_FAILURE` run. Content remains `UNREVIEWED`; M8 does not assert human review, release approval, provider authentication, or an Internet-wide originality search.

```bash
python -m english_master.qa_engine run \
  --lesson-id A1-U01-L01 \
  --created-at 2026-09-04T10:00:00Z \
  --output-dir <new-immutable-run-directory>

python -m english_master.qa_engine verify \
  --run-dir <immutable-run-directory>
```

Static response documents supplied through `--regeneration-captures` or `--review-captures` are replay-only evidence and cannot promote a changed candidate. See [docs/QA_ENGINE.md](docs/QA_ENGINE.md) for evidence, retry, and verification constraints.

## Build and verify the M8.2 AI-practice pilot

M8.2 builds exactly forty immutable lesson-specific prompt artifacts from the verified ten-lesson M6 development batch. It uses only original project-authored inline text; prompts remain `UNREVIEWED` and a successful pilot is only `MACHINE_VALIDATED`.

```bash
python -m english_master.ai_practice build-pilot \
  --output-dir <new-immutable-pilot-directory>

python -m english_master.ai_practice verify-pilot \
  --pilot-dir curriculum/ai-practice/pilot-batches/20260905-v13
```

See [docs/AI_PRACTICE_PILOT.md](docs/AI_PRACTICE_PILOT.md) for the modality contracts, evidence limits, and tamper-resistant verification.

## Active M9 development check

Run the complete deterministic suite, then record a direct inspection of five representative lesson packets as described in [M9 Lightweight Development QA](docs/M9_INDEPENDENT_REVIEW.md):

```bash
python -m pytest
python -m english_master.project_audit
git diff --check
```

The audit checks active documentation, local implementation paths, and declared repository facts for drift. It is a consistency check, not an approval, release, human-review, or runtime-quality gate.

## M11 local-batch and historical commands

Build and verify a local batch without an M9/M10 or release-authority gate:

```bash
python -m english_master.export_packaging build-batch \
  --batch-input <m11-export-batch-input.json> \
  --repository-root . \
  --output-root data/exports \
  --exported-at <ISO-8601>
python -m english_master.export_packaging verify-batch \
  data/exports/<export-id> --repository-root .
```

The historical authority commands remain solely for existing immutable records:

```bash
python -m english_master.export_packaging inspect-authority --authorization <m11-authorization.json> --repository-root .
python -m english_master.export_packaging verify data/exports/<export-id> --repository-root .
```

See [Export & Packaging](docs/EXPORT_PACKAGING.md) for format and verification details.

## Layout

- `schemas/` — authoritative Draft 2020-12 JSON Schemas.
- `src/english_master/` — typed pipeline, generation, review, revision, and export utilities.
- `tests/fixtures/` — small, invented validation, ingestion, and M6 offline test examples; taxonomy tests use the authored prototype.
- `sources/` — M1 registry metadata, official evidence summary, and source-operation policy; no source payloads.
- `data/raw/`, `data/normalized/`, `data/quarantine/` — local M3 run payloads and audit records, ignored by Git except scaffolding.
- `data/deduplicated/`, `data/reports/` — local M4 derived runs and reports, ignored by Git.
- `data/approved/` — reserved for genuinely approved/classified data; current development artifacts do not populate it.
- `data/exports/` — immutable local M11 export bundles, ignored by Git; a successful local export does not create public-distribution authority.
- `curriculum/taxonomy/` — M2 representative taxonomy and broad coverage matrix.
- `curriculum/structure.json`, `curriculum/prerequisite_graph.json`, `curriculum/coverage-roadmap.json` — M5 outline-only architecture, graph, and coverage artifacts.
- `curriculum/curriculum-graph.dot` — deterministic compact graph view; JSON remains authoritative.

See `docs/` for architecture, data policy, curriculum models, QA policy, and milestone definitions.
