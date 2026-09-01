GIAI ĐOẠN 12 — M4: NORMALIZATION + DEDUPLICATION

Sau khi ingestion engine hoạt động mới làm:

```text
raw
 ↓
normalization
 ↓
exact deduplication
 ↓
near-duplicate detection
 ↓
semantic-duplicate review
```

Tạo:

prompts/M4_NORMALIZATION_DEDUPLICATION.md

# M4 — Normalization and Deduplication

## Objective

Build a deterministic post-ingestion normalization and deduplication stage for records already produced by M3.

M4 consumes retained raw records and/or M3 normalized records. It must not replace the M3 ingestion engine or bypass source governance.

The first implementation must be simple, explainable, reproducible, and offline.

Do NOT add a vector database.

Do NOT add embeddings yet.

Do NOT classify content by CEFR.

Do NOT generate curriculum, lessons, exercises, or AI prompts.

---

# Pipeline

Implement the following explicit stages:

```text
M3 raw record
    ↓
canonical normalization
    ↓
raw_hash + normalized_hash
    ↓
exact duplicate detection
    ↓
near-duplicate detection
    ↓
semantic-duplicate review queue
    ↓
accepted / duplicate / review-needed output
```

Each stage must have a clear input/output contract. Do not hide normalization and deduplication in an unrelated ingestion adapter.

A later stage must not mutate the original raw record.

---

# Architecture

Create a focused package, for example:

```text
src/english_master/normalization/
├── __init__.py
├── models.py
├── text.py
├── hashes.py
├── exact.py
├── near.py
├── semantic.py
├── pipeline.py
└── storage.py
```

The exact layout may differ, but keep responsibilities separated:

- text normalization
- hash calculation
- exact duplicate indexing
- near-duplicate scoring
- semantic duplicate review decisions
- orchestration and persistence

Reuse the existing schema-validation, provenance, and M3 storage conventions. Do not create a second source registry or a competing provenance model.

---

# Normalization

Define a deterministic, documented text-normalization policy.

At minimum, consider:

- Unicode normalization;
- line-ending normalization;
- whitespace collapsing;
- trimming leading/trailing whitespace;
- consistent case-folding policy for comparison;
- preservation of the original display text;
- safe handling of punctuation, apostrophes, and non-ASCII text;
- language-aware limitations.

Do not destroy meaningful linguistic information in the canonical stored text merely to improve duplicate matching. Store both:

- original/source text;
- normalized comparison text.

Normalization must be deterministic and idempotent:

```text
normalize(normalize(text)) == normalize(text)
```

Document which transformations are reversible and which are comparison-only.

Do not use an uncontrolled language model or external network service in normalization.

---

# Hashes

Every processed record must retain both hashes:

- `raw_hash`: SHA-256 of the canonical original raw record representation;
- `normalized_hash`: SHA-256 of the canonical normalized comparison representation.

Hash requirements:

- use explicit UTF-8 serialization;
- define JSON key ordering and separators;
- define newline behavior;
- use SHA-256;
- produce lowercase hexadecimal output;
- never calculate `raw_hash` from normalized text;
- never overwrite a source-provided hash without recording the verification result;
- verify M3 provenance `content_hash` against the retained raw representation where applicable.

A record with the same `raw_hash` is an exact duplicate of the same raw record.

A record with a different `raw_hash` but the same `normalized_hash` is a normalized-text duplicate and must retain both source identities for auditability.

---

# Exact deduplication

Implement deterministic exact duplicate detection using hashes, not ad hoc string comparisons.

At minimum detect:

1. identical raw records (`raw_hash` match);
2. distinct raw records producing identical normalized text (`normalized_hash` match);
3. collisions or inconsistent metadata for an existing hash.

Do not silently discard duplicate provenance. Maintain a duplicate group or index containing:

- canonical record/group ID;
- all contributing source IDs;
- all source record IDs;
- raw hashes;
- normalized hashes;
- first-seen and subsequent locations;
- deduplication reason;
- disposition.

Repeated runs must be deterministic and idempotent. Existing outputs must not be silently overwritten.

---

# Near-duplicate detection

Initially implement explainable n-gram similarity. A suitable baseline is token or character n-grams with a documented Jaccard or equivalent similarity score.

Requirements:

- use a deterministic tokenizer and n-gram policy;
- document n-gram size, tokenization, punctuation treatment, and thresholds;
- produce a score and evidence for every flagged pair/group;
- compare only bounded candidate sets so the implementation does not accidentally become an unbounded O(n²) job;
- use deterministic ordering and tie-breaking;
- make thresholds configurable and record the configuration in the run report;
- do not call near duplicates exact duplicates automatically unless the policy explicitly says so.

Near-duplicate output must preserve both records and identify the pair/group requiring review or the approved merge decision.

Examples to test include:

- whitespace and punctuation variants;
- case variants;
- minor spelling or wording changes;
- translations, which must not be treated as English exact duplicates merely because they are related;
- short texts where similarity scores are unreliable.

---

# Semantic duplicates

M4 must define a semantic-duplicate review boundary without pretending to solve semantic similarity fully.

Before embeddings are introduced:

- do not claim that n-gram similarity proves semantic equivalence;
- route ambiguous or high-risk pairs to `REVIEW_REQUIRED`;
- allow an explicit human-reviewed disposition such as `DUPLICATE`, `NOT_DUPLICATE`, or `RELATED_NOT_DUPLICATE`;
- retain reviewer, timestamp, reason, and evidence;
- never automatically merge records solely on a weak similarity score;
- keep translation and paraphrase decisions distinguishable from exact duplication.

A future embeddings stage may add signals, but it must not invalidate existing raw provenance or hashes.

---

# Data model and storage

Define schemas for normalized comparison records, duplicate groups/indexes, similarity candidates, review decisions, and run reports as needed.

Every derived record must retain:

- stable deterministic ID;
- source and source-record identity;
- original raw location;
- original/raw hash;
- normalized text or comparison representation;
- normalized hash;
- normalization policy/version;
- deduplication policy/version;
- processing timestamp or explicit run metadata;
- disposition/status.

Use a documented layout, for example:

```text
data/normalized/<source_id>/...
data/deduplicated/records/...
data/deduplicated/groups/...
data/deduplicated/review/
data/reports/normalization/<run_id>.json
```

Keep source provenance permanently attached. Deduplication is not permission to remove attribution, licensing, or source record IDs.

Generated data must be ignored by Git unless it is a small, explicitly authored fixture or schema example with clear licensing.

Use atomic writes and fail-safe behavior. Invalid or incomplete derived data must not be published as accepted output.

---

# CLI

Provide a reproducible offline CLI, for example:

```bash
python -m english_master.normalize \
  --input <m3-normalized-input> \
  --output-root <output-root> \
  --ngram-size 3 \
  --near-threshold 0.85
```

The CLI must:

- accept bounded, explicit inputs;
- expose normalization and similarity policy versions/configuration;
- support deterministic run metadata;
- print counts and report location;
- return nonzero for malformed input, schema failure, hash mismatch, invalid configuration, or write failure;
- never require network access;
- never require a vector database or embeddings service.

Document all defaults and thresholds. Do not silently change a deduplication policy between runs.

---

# Validation and provenance

Reuse M3 and project validation utilities where applicable.

Validate:

- input normalized-record schema;
- output schema;
- required `raw_hash` and `normalized_hash`;
- hash format and recomputation;
- source/provenance consistency;
- deterministic IDs;
- duplicate-group references;
- review decisions and allowed dispositions;
- no accepted output references an invalid or missing record;
- no source permission is broadened by normalization.

Normalization and deduplication must never be used to ingest a source that M1/M3 did not authorize.

---

# Tests

Add offline tests for actual success and failure paths:

- normalization correctness and idempotency;
- Unicode, whitespace, punctuation, case, and multilingual edge cases;
- deterministic raw and normalized hashes;
- raw hash differs when raw content differs;
- normalized hash matches intended comparison-equivalent text;
- exact raw duplicates;
- normalized-text duplicates with distinct provenance;
- hash collision/inconsistent metadata handling;
- deterministic n-gram scores and threshold behavior;
- near-duplicate review candidates;
- short-text and translation safeguards;
- semantic review dispositions and rejection of unsupported automatic merges;
- missing provenance, invalid hashes, malformed records, and schema failures;
- duplicate-group reference integrity;
- idempotent reruns and no-overwrite conflicts;
- atomic-write failure behavior;
- CLI success and nonzero failure cases;
- bounded input and no network/vector-database dependency.

Tests must verify that deduplication preserves all source provenance and attribution.

---

# Explicit exclusions

M4 does not:

- download new source data;
- bypass M1/M3 source permissions;
- classify CEFR levels;
- build a frequency model;
- generate curriculum, lessons, exercises, assessments, or AI prompts;
- add embeddings;
- add a vector database;
- claim that n-gram similarity is semantic proof;
- implement M5 or later milestones.

---

# Acceptance

1. deterministic normalization exists and is documented;
2. original text/raw records remain preserved;
3. every derived record retains `raw_hash` and `normalized_hash`;
4. exact raw and normalized-text duplicates are detected;
5. duplicate provenance and attribution are preserved;
6. explainable n-gram near-duplicate scoring works;
7. thresholds and similarity evidence are recorded;
8. semantic duplicates are routed to explicit review rather than guessed automatically;
9. output schemas and hash integrity are validated;
10. reruns are deterministic and do not silently overwrite data;
11. CLI and reports work offline;
12. tests cover success and failure cases;
13. no vector database or embeddings were introduced;
14. no M5 or later milestone was started.

Run the full applicable test suite, inspect generated reports and output, inspect the diff, and report PASS/FAIL with unresolved issues.

Then STOP.
