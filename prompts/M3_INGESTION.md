GIAI ĐOẠN 11 — M3: INGESTION ENGINE

Đến đây mới bắt đầu xây máy lấy dữ liệu.

M3 chưa cần download hết Internet.

Tạo:

prompts/M3_INGESTION.md

# M3 — Data Ingestion and Normalization Engine

## Objective

Build a small, reproducible ingestion engine that moves authorized source data through:

```text
registered source
    ↓
source adapter
    ↓
raw record
    ↓
provenance
    ↓
normalized record
    ↓
schema and policy validation
    ↓
data/normalized/
```

The engine is infrastructure for later milestones. It is not a corpus project.

Do NOT download the whole Internet.

Do NOT bulk-download corpora or media.

Do NOT classify records by CEFR yet.

Do NOT generate curriculum, lessons, exercises, or prompts.

Only use sources registered in the M1 source registry. Respect each source's status, license, terms, rate limits, and operation-specific permissions. Unknown or unauthorized sources must fail closed or be quarantined.

---

# Architecture

Create an adapter-based architecture similar to:

```text
src/english_master/ingestion/
├── __init__.py
├── base.py
├── registry.py
├── pipeline.py
└── adapters/
    ├── __init__.py
    └── <source_adapter>.py
```

Define a typed interface such as:

```python
class SourceAdapter:
    def fetch(...): ...
    def parse(...): ...
    def normalize(...): ...
    def provenance(...): ...
```

The exact method signatures may be improved if they preserve the same separation of responsibilities.

Every source gets its own adapter module. Register adapters through a registry or factory keyed by the source registry's stable `source_id`.

Do NOT create one giant conditional file such as:

```python
if source == "voa":
    ...
elif source == "tatoeba":
    ...
```

Do NOT create a 5,000-line source switchboard.

The core pipeline must depend on the adapter interface, not on source-specific implementation details. Adding a source should require a new adapter and registration, not edits throughout the pipeline.

---

# Scope of the first implementation

Implement one small end-to-end adapter using a permitted, registered source or a deterministic local fixture representing that source's documented export/API response.

The first adapter must:

1. verify that the source exists in the registry;
2. verify that its status and operation permissions allow the requested fetch;
3. fetch a bounded input, never an unbounded crawl;
4. retain the original raw record before transformation;
5. parse the source format into records;
6. attach complete provenance to every external record;
7. normalize records into a documented canonical shape;
8. validate the normalized output;
9. write only approved normalized output to `data/normalized/<source_id>/`;
10. write errors and rejected records to an auditable quarantine/error location without silently dropping them.

A local fixture may be used in tests so tests remain offline, deterministic, and free of unnecessary network access. Do not disguise invented data as downloaded source content; label fixtures clearly.

Do not add a source merely to avoid implementing an adapter. Do not download large payloads.

---

# SourceAdapter contract

Document and test the contract for:

## fetch

- accepts bounded, explicit input options;
- never bypasses authentication, paywalls, robots restrictions, rate limits, or technical controls;
- uses the source's permitted operation only;
- returns raw source payloads or raw records without silently rewriting them;
- supports deterministic test injection or a local fixture;
- records enough information to reproduce the request.

## parse

- converts raw payloads into discrete raw records;
- preserves source record identity;
- reports malformed records as structured errors;
- does not discard records silently;
- does not perform CEFR classification.

## provenance

Every external record must include the fields required by the data policy:

- `source_id`
- `source_name`
- `source_url`
- `source_record_id`
- `retrieved_at`
- `retrieved_by`
- `license`
- `attribution`
- `content_hash`
- `ingestion_version`

The hash must be a deterministic SHA-256 hash of the original record or payload used by the documented policy. Timestamps and tool versions must be explicit and testable; avoid hidden nondeterminism.

## normalize

- maps permitted source fields to a canonical normalized representation;
- preserves provenance;
- preserves source identifiers and traceability;
- does not copy restricted fields into an approved output unless the source license permits that use;
- produces stable ordering and deterministic IDs where the canonical schema requires them;
- does not assign CEFR levels or pretend that frequency equals CEFR classification.

---

# Registry and pipeline

Implement:

## Adapter registry

- map registered `source_id` values to adapter implementations;
- reject unknown source IDs;
- reject duplicate adapter registrations;
- reject an adapter whose declared source ID does not match the selected registry record;
- expose a clear way to list available adapters.

## Ingestion pipeline

Provide a typed orchestration layer that:

1. loads and validates the source registry;
2. selects an adapter by `source_id`;
3. checks operation-specific permissions before fetching;
4. executes fetch → parse → provenance → normalize → validate;
5. records counts for fetched, parsed, normalized, rejected, and quarantined records;
6. writes a reproducible ingestion report;
7. uses atomic or otherwise failure-safe output writes;
8. returns nonzero/raises a clear error for fatal failures;
9. never publishes invalid records as normalized data.

Do not couple the pipeline to a particular source format.

---

# Canonical normalized records

Define the smallest useful normalized schema for the selected record type, reusing existing M0 schemas and common provenance definitions where appropriate.

At minimum, normalized records must have:

- a deterministic record ID;
- the normalized content fields;
- complete provenance;
- schema version;
- ingestion version.

Document which fields are source-derived, which are normalized, and which are generated by the ingestion system.

Do not add CEFR classification fields merely as placeholders. Classification belongs to M4.

---

# Storage and safety

Use the documented layout:

```text
data/raw/<source_id>/<run_id>/
data/normalized/<source_id>/
data/quarantine/<reason>/
```

Raw payloads must remain excluded from Git by default and must not be committed accidentally. Small deterministic fixtures and reports may be committed only when their licensing and purpose are clear.

Each run must have an auditable report containing at least:

- source ID and adapter ID;
- ingestion version;
- input description or request parameters;
- start/completion outcome;
- record counts;
- error and quarantine counts;
- output paths;
- content or run hashes where applicable.

Do not overwrite an existing normalized run silently. Use deterministic content identity and explicit run/output handling.

---

# Copyright and licensing

Before fetching, check the registered source's status and operation-specific permissions.

Distinguish at least:

- fetch/download;
- storage;
- transformation/normalization;
- text extraction;
- audio/video handling;
- redistribution.

A source that is `REFERENCE_ONLY`, `QUARANTINED`, or `REJECTED` must not contribute records to approved normalized data. A missing permission must fail closed. Taxonomy citation permission is not ingestion permission.

Retain attribution and provenance. Never bypass access controls. Do not ingest source content whose license or redistribution rights are unclear.

---

# CLI

Add a documented, reproducible CLI, for example:

```bash
python -m english_master.ingest --source <source_id> --input <bounded-input>
```

The CLI must:

- expose bounded input options;
- support an offline fixture/test mode where appropriate;
- print a concise summary and report location;
- return nonzero on invalid source, denied permission, parse failure, schema failure, or write failure;
- never require network access for the test suite.

Document setup, examples, output locations, and failure behavior in README or M3 documentation.

---

# Tests

Add tests for actual success and failure behavior:

- adapter contract compliance;
- adapter registry lookup and duplicate/unknown adapter rejection;
- bounded fetch behavior;
- parse success and malformed input errors;
- complete provenance fields;
- deterministic content hashes and normalized IDs;
- schema validation of normalized records;
- missing or unauthorized source rejection;
- `REFERENCE_ONLY`, `QUARANTINED`, and `REJECTED` source rejection;
- denied operation-specific permissions;
- duplicate detection/idempotent reruns;
- quarantine and error reporting;
- atomic/failure-safe output behavior;
- CLI success and nonzero failure cases;
- no network dependency in ordinary tests.

Tests must test failure paths, not only happy paths.

---

# Explicit exclusions

M3 does not:

- classify content by CEFR;
- build a frequency model;
- generate a curriculum or dependency roadmap;
- generate lessons, exercises, assessments, or AI prompts;
- ingest every registered source;
- download large corpora or media collections;
- implement M4 linguistic analysis.

---

# Acceptance

1. adapter interface exists and is documented;
2. each implemented source is isolated in its own adapter;
3. adapter registry replaces giant source conditionals;
4. one bounded source path works end to end;
5. raw records are retained appropriately;
6. complete provenance is attached;
7. normalized output is schema-valid;
8. unauthorized and malformed records fail closed or are quarantined;
9. ingestion reports are reproducible and auditable;
10. CLI is documented and returns correct exit status;
11. tests cover success and failure cases;
12. no bulk corpus/media download occurred;
13. M4 and later milestones were not started.

Run the full test suite and inspect the generated output.

Report PASS/FAIL, created files, changed files, commands, tests, test results, unresolved issues, and confirmation that no later milestone was started.

Then STOP.
