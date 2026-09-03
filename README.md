# English Master

English Master is a reproducible, self-study English learning-system pipeline for CEFR A1 through C2. Its primary learners are Vietnamese learners of English.

## Current scope: M0 through M5 complete; M6 infrastructure repaired

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
- A repaired provider-neutral M6 generation boundary that loads and hash-binds M5 artifacts, an independent authorization, and the source registry; derives graph context; injects trusted lesson metadata; emits stage-aware QA audits; and uses atomic no-overwrite artifact bundles. This is generator infrastructure, not completed or independently approved lesson content.
- Data-lifecycle directory scaffolding and Git protections.

M3 is ingestion infrastructure, not a corpus project. M4 adds deterministic normalization and review-oriented deduplication only. M5 adds architecture and dependency planning only. M6 adds constrained lesson-generation infrastructure and one project-authored offline test fixture; it does not approve generated lessons. These stages do not crawl websites, bulk-download data or media, generate exercises, assessments, or AI prompts. The committed ingestion fixture sentences are invented and explicitly used only to test the documented Tatoeba-shaped input path. The committed M5 bundle still references the DRAFT M2 taxonomy under an explicit outline-only gate and therefore fails M6 preflight before the backend is called. M6 success tests use a separate, explicitly synthetic authorization fixture; they do not constitute human review, reinterpret the M5 bundle, or upgrade its status.

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

M5 contains a compact outline-only architecture: 12 globally numbered representative units, 24 lesson outlines, and 12 review nodes across all internal tiers. The 1,000-1,200 hour scale range is an expansion estimate, not completed content. DRAFT taxonomy dependencies are allowed only for outline planning and explicitly fail the M6 generation gate until independent review. See [docs/CURRICULUM_ARCHITECTURE.md](docs/CURRICULUM_ARCHITECTURE.md).

Prepare a hash-bound packet for independent human review, with the current strict source registry independently loaded and all taxonomy citations checked for reference eligibility. Publish or verify an immutable snapshot only after real linguistic and pedagogical submissions exist:

```bash
python -m english_master.curriculum_review prepare curriculum/structure.json --source-registry sources/registry.yaml --output <new-manifest-directory>
python -m english_master.curriculum_review publish curriculum/structure.json --source-registry sources/registry.yaml --manifest <manifest.json> --linguistic-review <review.json> --pedagogical-review <review.json> --reviewer-registry <trusted-reviewer-registry.json> --approved-at <ISO-8601> --published-by <publisher-id> --output <new-snapshot-directory>
python -m english_master.curriculum_review verify curriculum/structure.json --source-registry sources/registry.yaml --snapshot <snapshot-directory> --reviewer-registry <trusted-reviewer-registry.json>
```

The repository intentionally includes blank review forms, not a real review or approval. See [docs/M5_REVIEW_WORKFLOW.md](docs/M5_REVIEW_WORKFLOW.md).

## Run constrained M6 lesson generation

M6 accepts only a reverified genuine M5 approval snapshot, independently loaded reviewer/source registries, and a prompt-hash-bound captured response. It deliberately does not accept arbitrary caller-authored request, authorization, or mock-response files:

```bash
python -m english_master.lesson_generate \
  --lesson-id A1-U01-L01 \
  --snapshot-dir <trusted-snapshot-directory> \
  --reviewer-registry <trusted-reviewer-registry.json> \
  --captured-response <trusted-captured-response.json> \
  --output-dir data/generated/m6/A1-U01-L01
```

The command reconstructs the exact M6 authorization and request from the verified snapshot and current M5 bundle before a backend is called. It injects only trusted lesson metadata, validates the assembled candidate, and atomically publishes `lesson.json` and `audit.json` on success. Add `--rejection-dir <directory>` to retain an immutable rejection-plus-audit bundle.

No genuine snapshot, protected digest, production capture, or ten-lesson M6 batch exists yet. Test-only synthetic snapshots and mock backends exercise the fail-closed implementation but cannot authorize production generation. All generated output remains `UNREVIEWED`. See [docs/LESSON_GENERATION.md](docs/LESSON_GENERATION.md).

## Layout

- `schemas/` — authoritative Draft 2020-12 JSON Schemas.
- `src/english_master/` — typed validation, ingestion, normalization, deduplication, M5 curriculum-graph, and M6 lesson-generation utilities.
- `tests/fixtures/` — small, invented validation, ingestion, and M6 offline test examples; taxonomy tests use the authored prototype.
- `sources/` — M1 registry metadata, official evidence summary, and source-operation policy; no source payloads.
- `data/raw/`, `data/normalized/`, `data/quarantine/` — local M3 run payloads and audit records, ignored by Git except scaffolding.
- `data/deduplicated/`, `data/reports/` — local M4 derived runs and reports, ignored by Git.
- `data/approved/` — reserved for later approved/classified data; M3 does not populate it.
- `curriculum/taxonomy/` — M2 representative taxonomy and broad coverage matrix.
- `curriculum/structure.json`, `curriculum/prerequisite_graph.json`, `curriculum/coverage-roadmap.json` — M5 outline-only architecture, graph, and coverage artifacts.
- `curriculum/curriculum-graph.dot` — deterministic compact graph view; JSON remains authoritative.

See `docs/` for architecture, data policy, curriculum models, QA policy, and milestone definitions.
