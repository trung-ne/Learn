# English Master

English Master is a reproducible, self-study English learning-system pipeline for CEFR A1 through C2. Its primary learners are Vietnamese learners of English.

## M0 scope

This repository bootstrap provides:

- JSON Schema definitions for the six core record types.
- A typed, offline schema validator.
- Tiny artificial fixtures and pytest coverage.
- Data-lifecycle directory scaffolding and Git protections.

M0 does **not** crawl websites, download data, register or approve external sources, generate a curriculum, or generate lessons or exercises. Fixtures are invented solely to verify the schemas.

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

## Layout

- `schemas/` — authoritative Draft 2020-12 JSON Schemas.
- `src/english_master/` — typed local schema validation utility.
- `tests/fixtures/` — small, invented validation examples.
- `sources/` — future source registry metadata; empty during M0.
- `data/raw/` — future downloaded payloads; ignored by Git by default.
- `data/normalized/`, `data/approved/`, `data/quarantine/` — later pipeline stages.
- `curriculum/` — future dependency graph and content artifacts; empty during M0.

See `docs/` for architecture, data policy, curriculum models, QA policy, and milestone definitions.
