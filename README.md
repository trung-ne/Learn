# English Master

English Master is a reproducible, self-study English learning-system pipeline for CEFR A1 through C2. Its primary learners are Vietnamese learners of English.

## Current scope: M0 and M1

The completed foundation provides:

- JSON Schema definitions for the core records and source-governance registry.
- A typed, offline JSON/YAML schema validator and fail-closed source-permission gate.
- Tiny artificial fixtures and pytest coverage.
- An official-evidence-backed source registry with separate text, audio, and video rights decisions.
- Data-lifecycle directory scaffolding and Git protections.

M1 registers governance metadata only. It does **not** crawl websites, bulk-download data or media, generate transcripts, run speech recognition, ingest a corpus, generate a curriculum, or generate lessons or exercises. Test fixtures are invented solely to verify schemas.

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

## Layout

- `schemas/` — authoritative Draft 2020-12 JSON Schemas.
- `src/english_master/` — typed local schema validation utility.
- `tests/fixtures/` — small, invented validation examples.
- `sources/` — M1 registry metadata, official evidence summary, and source-operation policy; no source payloads.
- `data/raw/` — future downloaded payloads; ignored by Git by default.
- `data/normalized/`, `data/approved/`, `data/quarantine/` — later pipeline stages.
- `curriculum/` — future dependency graph and content artifacts; empty during M0.

See `docs/` for architecture, data policy, curriculum models, QA policy, and milestone definitions.
