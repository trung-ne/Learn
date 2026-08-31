# English Master

English Master is a reproducible, self-study English learning-system pipeline for CEFR A1 through C2. Its primary learners are Vietnamese learners of English.

## Current scope: M0 through M3

The completed foundation provides:

- JSON Schema definitions for core records, source governance, M2 taxonomy collections, and normalized external text.
- A typed, offline JSON/YAML validator with semantic taxonomy checks and a fail-closed source-permission gate.
- Tiny artificial fixtures, a small original-authored taxonomy prototype, and pytest coverage.
- An official-evidence-backed source registry with separate text, audio, and video rights decisions.
- A representative concept DAG, sense-aware vocabulary model, Vietnamese learner annotation layer, and broad confidence-marked CEFR coverage matrix.
- A typed adapter registry and failure-safe ingestion pipeline with one bounded offline `src_tatoeba_text` adapter.
- Data-lifecycle directory scaffolding and Git protections.

M3 is ingestion infrastructure, not a corpus project. It does **not** crawl websites, bulk-download data or media, classify records by CEFR, compute frequency, generate a curriculum, or generate lessons or exercises. The committed ingestion fixture sentences are invented and explicitly used only to test the documented Tatoeba-shaped input path.

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

## Layout

- `schemas/` — authoritative Draft 2020-12 JSON Schemas.
- `src/english_master/` — typed validation and adapter-based ingestion utilities.
- `tests/fixtures/` — small, invented validation and offline ingestion examples; taxonomy tests use the authored prototype.
- `sources/` — M1 registry metadata, official evidence summary, and source-operation policy; no source payloads.
- `data/raw/`, `data/normalized/`, `data/quarantine/` — local M3 run payloads and audit records, ignored by Git except scaffolding.
- `data/approved/` — reserved for later approved/classified data; M3 does not populate it.
- `curriculum/taxonomy/` — M2 representative taxonomy and broad coverage matrix; not a generated curriculum.

See `docs/` for architecture, data policy, curriculum models, QA policy, and milestone definitions.
