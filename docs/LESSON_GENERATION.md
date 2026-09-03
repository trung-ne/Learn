# M6 Lesson Generation

## Status and boundary

M6 generator infrastructure is implemented and tested offline. M6 is **not complete**: no genuine M5 approval snapshot, protected digest, production capture, ten generated lessons, or independent lesson-review evidence exists in this repository.

No production lesson may be generated until a genuine M5 snapshot has been published from distinct, verified linguistic and pedagogical reviews and its digest is protected independently. Synthetic snapshots used by tests are never production authority. Generated lessons remain `UNREVIEWED`.

M6 generates only lesson content sections. It does not generate exercises, answer keys, assessments, AI practice prompts, media, UI, or approval decisions.

## Authority boundary

Every M6 attempt independently reloads and verifies:

- M5 structure, graph, coverage roadmap, and taxonomy;
- the immutable six-member M5 snapshot bundle;
- the authoritative source registry; and
- the separately administered trusted reviewer registry.

A deterministic M6 authorization is then rebuilt from the verified snapshot. It may narrow the approved lesson set but cannot approve taxonomy records itself. The request is independently rebuilt from that authorization, the M5 outline, graph context, exact taxonomy hashes, prerequisite closure, previous knowledge, and bounded configuration. Legacy v1 authorization/request records are rejected.

The only current generation input policy is `REVIEWED_M2_M5_TAXONOMY_ONLY`. M3/M4 records have no production CEFR authority here, and no external source payload is included. Project-authored taxonomy fields are copied into a hash-bound teaching payload; citation wording and external payloads are excluded. Vietnamese learner annotations are hash-bound contextual guidance only, never generation authority.

## Derived lesson scope

The request and generated lesson preserve the M5 projection for grammar, vocabulary, communicative functions, pronunciation, supporting taxonomy concepts, skills, dimensions, review targets, lesson kind, objectives, unit/tier identity, and prerequisites. Embedded references may name only the exact allowed family, supporting, or prerequisite-closure records.

The backend may return only:

```json
{"content_sections": []}
```

The orchestration layer injects all trusted lesson fields, an empty `exercises` list, and `UNREVIEWED` generation metadata. M7-and-later fields are rejected.

## Captured response provenance

A backend response must be a `CapturedLessonResponse` bound to:

- SHA-256 of the exact UTF-8 prompt;
- canonical response hash;
- actual provider/model when known;
- exact parameters and seed;
- observed provider execution time; and
- deterministic and replayability facts.

The provider/model/timestamp are not caller-controlled request fields. The audit records the capture facts and an injectable orchestration-clock timestamp. Byte-identical output is claimed only when the concrete backend supports it.

## Audit and immutable storage

Audits report stage-aware `PASS`, `FAIL`, or `NOT_RUN` checks, complete snapshot binding, hashes, capture provenance, automated reviewer details, issues, and the four still-outstanding independent review categories: CEFR, grammar/lexical, language quality, and pedagogy.

Accepted `lesson.json` and `audit.json`, or rejected `rejection.json` and `audit.json`, are published atomically to a new no-overwrite directory. An automated pass is not human review or content approval.

## Independent review and batch QA contracts

`lesson-independent-review.schema.json` defines a human-submitted, hash-bound overlay. It binds the exact lesson, automated audit, and reverified M5 snapshot; verifies the reviewer against the independently loaded registry; records CEFR, grammar/lexical, language-quality, prerequisite-scope, pedagogical, and copyright spot-check evidence; and explicitly attests that the review does **not** mutate or approve the `UNREVIEWED` lesson.

`lesson-batch-qa-report.schema.json` is a fail-closed report for ten distinct graph-ordered immutable lesson bundles and a declared human-review sample. It records limitations rather than inferring manual outcomes. It does not complete M6 or M9 approval.

Validate supplied evidence offline only after a genuine snapshot exists:

```bash
python -m english_master.lesson_review review \
  --snapshot-dir /trusted/m5snapshot_<digest> \
  --reviewer-registry /trusted/reviewer-registry.json \
  --review /trusted/review.json --lesson /trusted/lesson.json --audit /trusted/audit.json

python -m english_master.lesson_review batch \
  --snapshot-dir /trusted/m5snapshot_<digest> \
  --reviewer-registry /trusted/reviewer-registry.json \
  --report /trusted/batch-report.json --bundle-root /trusted/m6-bundles
```

## Offline CLI

The CLI requires a genuine, independently verified snapshot and a prompt-bound captured response; it deliberately has no arbitrary `--request`, `--authorization`, or `--mock-response` production path:

```bash
python -m english_master.lesson_generate \
  --lesson-id A1-U01-L01 \
  --snapshot-dir /trusted/m5snapshot_<digest> \
  --reviewer-registry /trusted/reviewer-registry.json \
  --captured-response /trusted/captured-response.json \
  --output-dir data/generated/m6/A1-U01-L01 \
  --rejection-dir data/reports/m6/A1-U01-L01-rejection
```

The command independently loads `sources/registry.yaml` and the M5 files by default. Overrides for graph, coverage, or taxonomy are reverified against the snapshot and therefore fail on drift. Exit codes are `0` for accepted publication, `1` for a validated generation rejection, and `2` for setup or persistence failure.

Do not use synthetic fixtures, an unprotected digest, or a test-only backend as production authority.
