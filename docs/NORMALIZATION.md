# M4 Normalization and Deduplication

M4 is an offline, deterministic post-ingestion stage. It consumes strict M3 `normalized_text` JSON records and does not download data, assign CEFR levels, generate curriculum, use embeddings, or require a vector database.

## Command

```bash
python -m english_master.normalize \
  --input data/normalized/src_tatoeba_text/runs/<m3-run-id> \
  --output-root data/deduplicated \
  --processed-at 2026-08-31T12:00:00Z \
  --max-records 10000 \
  --ngram-size 3 \
  --near-threshold 0.85 \
  --minimum-characters 12 \
  --max-candidates-per-record 50
```

`--input` may be one M3 record, an M3 run containing `records/`, or a flat directory of record JSON files. The explicit record bound and timestamp are required. Inputs are validated against `normalized-text.schema.json`, and every source must still be `APPROVED` with `store_text` and `transform_text` permission.

The installed equivalent is `english-master-normalize`.

## Text policy `text-nfc-casefold-v1`

Every output retains three values:

- `original_text`: unchanged M3 text;
- `display_text`: NFC Unicode, normalized line endings, collapsed whitespace, and trimming;
- `comparison_text`: display normalization plus Unicode case folding; punctuation becomes a token boundary, while word-internal straight/curly apostrophes are retained and canonicalized.

Display normalization is intentionally conservative. Case folding and punctuation replacement are comparison-only and lossy. No language-specific stemming, transliteration, or model-generated rewriting occurs. The functions are idempotent.

## Hash policy

Canonical JSON uses UTF-8, sorted keys, compact `,`/`:` separators, non-ASCII characters preserved, and exactly one final LF. SHA-256 output is lowercase hexadecimal.

- `raw_hash` hashes the complete canonical M3 normalized record. It is never derived from normalized text.
- `normalized_hash` hashes `{language, comparison_text}` so identical strings in different languages are not exact duplicates.
- `source_content_hash` preserves M3 provenance unchanged (canonicalized to lowercase in the convenience field; the full provenance object is retained).

M3's source `content_hash` covers source-row bytes, but those bytes are not embedded in an M3 normalized JSON record. Therefore M4 reports `NOT_VERIFIABLE_FROM_M3_RECORD` rather than falsely claiming verification. Verification can become `VERIFIED` only when a future input contract supplies the retained row representation.

## Exact and near duplicates

`hash-exact-v1` creates deterministic groups for:

1. equal `raw_hash` values;
2. different raw records with equal language-scoped `normalized_hash` values.

All records, provenance, attribution, source identities, hashes, and locations remain present. The lexicographically first processed record ID is the canonical member; other members are marked `DUPLICATE`. Reusing one source/source-record identity for changed raw content fails the run.

`char-ngram-jaccard-v1` uses character trigrams by default after removing comparison-token spaces. It builds an inverted n-gram index, considers only the configured maximum candidates per record, compares within the same language, and skips texts shorter than 12 compact characters. Candidates at or above the threshold receive scores, intersection/union counts, and a matched n-gram sample. They are always `REVIEW_REQUIRED`, never automatic semantic duplicates.

Human semantic decisions are limited to `DUPLICATE`, `NOT_DUPLICATE`, and `RELATED_NOT_DUPLICATE`, with a distinct `PARAPHRASE`, `TRANSLATION`, or `OTHER` relationship and required reviewer, timestamp, reason, and evidence.

## Output and safety

One complete run is staged and atomically published under:

```text
<output-root>/runs/<run-id>/
├── records/
├── groups/
├── candidates/
├── review/queue.json
└── report.json
```

Run identity includes sorted input identities/hashes, all policy settings, and the explicit processing timestamp. An identical rerun returns the existing report. An incomplete or conflicting existing run is rejected; partial staged output is removed. Derived data is schema-validated and references are checked before publication.

Generated outputs under `data/deduplicated/` and `data/reports/` are ignored by Git. They are not approved/classified data and must not be moved to `data/approved/` without later QA.
