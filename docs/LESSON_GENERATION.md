# M6 Lesson Generation

## Boundary

M6 produces one lesson JSON record from an explicit, approved generation snapshot. It does not generate exercises, answer keys, assessments, AI practice prompts, media, UI, or approval decisions. Every accepted lesson has `qa_status: UNREVIEWED` and requires independent QA.

The committed M5 `OUTLINE_ONLY` structure is not an approved generation input. Its DRAFT taxonomy gate has `blocks_content_generation: true`; passing M5 architecture validation does not grant M6 authorization. Tests assert that this bundle fails before the backend is called. The M6 success fixture is a separate, original project-authored snapshot explicitly approved for bounded offline fixture use.

## Contracts

Authoritative Draft 2020-12 schemas are:

- `lesson-generation-authorization.schema.json` — immutable approved taxonomy/vocabulary snapshot, record types, CEFR tiers, authorship or permitted provenance, and review decision.
- `lesson-generation-request.schema.json` — lesson specification, graph context, previous knowledge, exact allowed/forbidden sets, bounds, versions, parameters, and deterministic request identity.
- `lesson-generation-audit.schema.json` — canonical input/output hashes, applied constraints, versions, backend metadata, check outcomes, QA state, and deterministic unresolved issues.
- `lesson-generation-rejection.schema.json` — preflight/provider/postvalidation rejection stage, candidate and hashes when available, deterministic reasons, and `published: false`.
- `lesson.schema.json` — remains compatible with earlier M0 records while optionally representing function and pronunciation introduction/review and internal-tier unit IDs. M6 semantically requires these fields and an empty `exercises` array.

IDs and hashes use UTF-8 canonical JSON with sorted object keys and compact separators. `request_id` and `authorization_id` are SHA-256 identities calculated with their own identity field omitted.

## Fail-closed flow

1. Validate the complete request and authorization schemas.
2. Verify canonical identities, pinned versions, exact target tier, lesson/graph identity, graph ordering and acyclicity, completed prerequisites, review history, reference types, approved status, prerequisite closure, CEFR ceiling, bounds, and disjoint forbidden sets.
3. Call a backend only if preflight has no issue. `LessonBackend` is provider-neutral; M6 includes only a deterministic offline mock implementation.
4. Validate all candidate violations together: lesson schema, exact identity/objectives/reference scope, metadata, CEFR, bounds, forbidden IDs/terms, embedded references, canonical order, and later-milestone leakage.
5. Publish `lesson.json` and `audit.json` together through an atomic, no-overwrite directory rename only after all checks pass.
6. On failure, publish no lesson. An optional rejection path stores a no-overwrite audit record, including the rejected candidate for postvalidation failures.

Provider failures are converted into deterministic rejection issues. Generation never downloads data or silently repairs, broadens, or approves a request.

## Offline CLI

```bash
python -m english_master.lesson_generate \
  --request tests/fixtures/m6/approved-request.json \
  --mock-response tests/fixtures/m6/approved-mock-lesson.json \
  --output-dir data/generated/m6/A1-U01-L01 \
  --rejection data/reports/m6/A1-U01-L01-rejection.json
```

Exit codes are `0` for accepted publication, `1` for a validated rejection, and `2` for file/CLI/setup failures. Output and rejection paths are immutable: existing paths are never overwritten.

Validate individual records offline with:

```bash
python -m english_master.schema_validation --schema lesson-generation-request tests/fixtures/m6/approved-request.json
python -m english_master.schema_validation --schema lesson tests/fixtures/m6/approved-mock-lesson.json
```

## Reproducibility and copyright

The request pins authorization, curriculum/taxonomy/schema/prompt/generator versions, backend provider/model, parameters, and seed when supported. The audit states whether byte-identical output is claimed; only the authored offline mock claims it. External records require complete provenance plus explicit authorization for generation. The committed M6 fixture uses original project-authored definitions and lesson text and contains no downloaded source payload.
