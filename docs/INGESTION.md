# M3 Ingestion Engine

## Scope

M3 provides a small adapter-based engine for authorized external records. It does not classify CEFR levels, compute frequency, generate curriculum, or produce learning content. The only implemented source path is a bounded, local, offline TSV adapter for `src_tatoeba_text`; there is no network fetch mode.

## Flow and contract

The source-independent pipeline loads and validates `sources/registry.yaml`, resolves an adapter by stable `source_id`, and requires every operation declared by that adapter before reading input. It then executes:

```text
fetch -> retain raw bytes -> parse -> provenance -> normalize -> schema validate -> atomic run publish
```

`SourceAdapter` in `src/english_master/ingestion/base.py` separates these responsibilities:

- `fetch` accepts an explicit local path, record cap, and retrieval timestamp. The Tatoeba adapter rejects inputs over 100 records or 1,000,000 bytes and rejects a file rather than silently truncating it.
- `parse` preserves each original TSV row, keeps sentence identity, and returns structured errors for every malformed or duplicate row.
- `provenance` builds all Data Policy fields and hashes the original UTF-8 TSV row bytes with SHA-256.
- `normalize` creates the canonical text shape and does not assign CEFR.

The adapter registry rejects unknown IDs, duplicate registrations, and mismatches between the registry key and an adapter's declared source ID. Adding another source requires another adapter module and an explicit registration; the core pipeline contains no source switch.

## Offline Tatoeba fixture format

The adapter accepts a UTF-8, tab-separated file with this exact header:

```text
sentence_id language text author license license_url
```

(The displayed spaces represent tabs.) M3's approved adapter lane accepts the record-level `CC-BY-2.0-FR` name and URL registered for `src_tatoeba_text`. Test fixture sentences are plainly invented project fixtures; they are not represented as downloaded Tatoeba records.

## Canonical normalized text fields

`schemas/normalized-text.schema.json` is the authoritative shape.

| Field | Origin |
| --- | --- |
| `text`, `language` | Source-derived; language tags are lowercased during normalization. |
| `provenance.source_record_id`, record license, license URL | Source-derived. |
| `provenance.source_id`, source name, source URL, attribution | Combined from the validated registry and source record. |
| `provenance.content_hash` | Generated SHA-256 of the exact original TSV record bytes. |
| `id` | Generated deterministically from source ID and source record ID. |
| `schema_version`, `record_type`, `ingestion_version`, retrieval metadata | Generated or supplied explicitly by the ingestion run. |

No CEFR field exists in this schema.

## Run the CLI

Install the project as described in the README, then run a bounded offline fixture:

```bash
python -m english_master.ingest \
  --source src_tatoeba_text \
  --input tests/fixtures/ingestion/tatoeba_text_valid.tsv \
  --max-records 2 \
  --retrieved-at 2026-08-31T12:00:00Z \
  --offline-fixture
```

`--retrieved-at` is mandatory so provenance and run identity are explicit and testable. The command has no network path. It exits nonzero for an unknown or unauthorized source, a denied operation, an invalid registry, an over-limit or malformed input, rejected/schema-invalid records, or a write failure.

## Storage and repeatability

A deterministic hash of the adapter, ingestion version, input description, and retrieval timestamp determines `run_id`.

```text
data/raw/<source_id>/<run_id>/payload.tsv
data/normalized/<source_id>/runs/<run_id>/records/*.json
data/normalized/<source_id>/runs/<run_id>/report.json
data/quarantine/ingestion_record_error/<source_id>/<run_id>/errors.json
```

Raw payloads are retained before parsing. A normalized run is staged and renamed into place only after all record and report files are written. Existing output is never silently replaced: identical reruns reuse the report, while differing content at an existing path fails. Invalid records are never written to `records/`; structured errors preserve their audit context under quarantine. A mixed run may publish its valid records, but its outcome is `COMPLETED_WITH_ERRORS` and the CLI exits nonzero.

Runtime raw, normalized, and quarantine payloads are ignored by Git by default. The tiny committed fixtures are the only source-shaped payloads used by ordinary tests.
