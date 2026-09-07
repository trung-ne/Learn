# Post-M3 Authorized Real English Data Ingestion Pilot

> Despite this filename, this is a **Post-M3 addendum**, not M11. M11 remains Export & Packaging.

## Purpose

Prepare and process one bounded batch of **1,000–5,000 real English text records** from the registered `APPROVED` source `src_tatoeba_text`. The pilot makes source evidence, real usage examples, provenance, normalized records, and duplicate-review evidence visible without treating them as curriculum material.

## Strict boundary

- Use only a locally supplied, pinned official Tatoeba download and a genuine completed authorization/receipt pair.
- Do not crawl sentence pages, use an API, follow mirrors, or make network requests from repository commands.
- Preserve the original local payload under gitignored `data/raw/` storage.
- Require record-level sentence ID, author, license, license URL, attribution, and English language value.
- Do not write to `data/approved/`, curriculum directories, lesson/exercise output, or export output.
- Do not claim CEFR classification, human review, release approval, provider authentication, Internet-wide coverage, or permission beyond the registered source operations.
- `TEST_ONLY`, invented fixtures, and replay evidence validate code only; they are not real ingestion.

## Required local bundle

An authorized operator supplies, below `data/raw/src_tatoeba_text/acquisitions/<id>/`:

1. The unmodified official payload using the supported six-column TSV shape.
2. `authorization.json`: hash-bound to the source registry, exact official URL, filename, payload bytes, target count, English/language scope, license lane, and genuine authorizer facts.
3. `receipt.json`: hash-bound to the authorization and actual local payload facts.

Unknown factual metadata must be recorded as `UNKNOWN` only where the schema permits it; never invent an identity, release, checksum, or approval.

## Commands

All commands are offline and accept paths, not URLs:

```bash
python -m english_master.ingestion_pilot prepare \
  --authorization data/raw/src_tatoeba_text/acquisitions/<id>/authorization.json \
  --receipt data/raw/src_tatoeba_text/acquisitions/<id>/receipt.json \
  --payload data/raw/src_tatoeba_text/acquisitions/<id>/official/<filename> \
  --output-directory data/raw/src_tatoeba_text/acquisitions/<id>

python -m english_master.ingestion_pilot run \
  --authorization ... --receipt ... \
  --preparation-report data/raw/src_tatoeba_text/acquisitions/<id>/preparation-report.json \
  --prepared-tsv data/raw/src_tatoeba_text/acquisitions/<id>/prepared/english-authorized-records.tsv \
  --retrieved-at 2026-09-07T00:00:00Z \
  --processed-at 2026-09-07T00:00:00Z

python -m english_master.ingestion_pilot verify \
  --authorization ... --receipt ... --preparation-report ... --prepared-tsv ...
```

`prepare` verifies the pinned local payload and deterministically selects authorized `eng` records. `run` performs all-or-nothing M3 ingestion, then existing M4 normalization/deduplication. `verify` is read-only.

## Output and interpretation

The pilot retains raw payloads, prepared TSVs, M3 normalized records, quarantine/error evidence, M4 exact duplicate groups, and near-duplicate review queues. It never auto-deletes records or promotes them to an approved corpus. Near matches remain `REVIEW_REQUIRED` until a separate authorized human semantic-review workflow occurs.
