# M7 Exercise Generation

## Boundary

M7 consumes only a reverified M6 `DEVELOPMENT_APPROVED` batch and produces lesson-bound exercise sets. It is a development lane: an accepted set and its exercises remain `UNREVIEWED`. Machine validation, recorded AI review, and any future human/release review are distinct evidence; no M7 command can emit `APPROVED`, `HUMAN_REVIEWED`, or `RELEASE_APPROVED`.

M7 does not create AI practice prompts, pronunciation evaluators, web/mobile features, spaced-repetition schedules, assessments, or M8 artifacts.

## Authority and request

`VerifiedM6DevelopmentAuthority` independently revalidates the M5 development snapshot, the M6 batch, every M6 lesson/audit/review hash, and safe bundle paths before a backend is called. The request is rebuilt from this authority and specifies exact lesson scope, objective/target/review references, CEFR, limits, and deterministic settings. Caller-widened, stale, unapproved, or drifted input fails closed.

The backend may return only authored exercise items. Host orchestration assigns IDs, status, lesson and batch bindings, generation metadata, hashes, and audits.

## External-content policy

The initial M7 development sets use only original inline project-authored text and transcript-only listening tasks. They exercise no external text, audio, video, transcript, clipping, transformation, audio extraction, or redistribution right. The audit records that limitation and does not claim an Internet-wide copyright or plagiarism search.

A future external stimulus/media feature must remain opt-in and fail closed: it needs a registered `APPROVED` source, complete record provenance and attribution, and operation-specific permission for every relevant operation (including exercise use, transformation, transcript, clip, extraction, and original/derived redistribution). `REFERENCE_ONLY`, `QUARANTINED`, and unknown-license sources cannot supply an exercise payload.

## Supported contracts

The backend candidate and semantic validator support: multiple choice, fill blank, matching, ordering, error correction, sentence construction, translation, reading, listening, speaking, and writing. Objective tasks carry complete answer/scoring data. Speaking and writing use analytic rubrics and remain reviewable rather than asserting one exact answer. Listening requires an authored inline transcript and `media_required: false`.

The validator checks schema, authority/request reconstruction, scope, CEFR/prerequisite constraints, answer shape, type-specific invariants, duplicate/near-duplicate padding, bounded workload, authored provenance, and M8 exclusion. It records outstanding CEFR, grammar/lexical, language-quality, and pedagogical reviews rather than pretending automated checks replace them.

## Independent AI development review

A distinct AI reviewer process may review only accepted `UNREVIEWED` set-and-audit bundles. Its linguistic and pedagogical records bind the full exercise-set hash, audit hash, verified M6 batch ID, actual prompt/response hashes, role-specific checklist, factual provider/model metadata (or `UNKNOWN`), decision, findings, and limits. Test-only or replay-only evidence cannot promote a development batch.

A ten-set development batch can become `DEVELOPMENT_APPROVED` only after both independent AI roles validate every set in graph order. This is AI-only development evidence: it does not alter any exercise's `UNREVIEWED` content-lifecycle status and never claims human review, public release, certification, or an Internet-wide originality search.

## CLI

Run offline against a retained captured response:

```bash
python -m english_master.exercise_generate \
  --lesson-id A1-U01-L01 \
  --captured-response curriculum/exercises/captures/20260903-development-v1/A1-U01-L01.json \
  --output-dir curriculum/exercises/development-20260903-v1/A1-U01-L01
```

It returns `0` for an accepted immutable set, `1` for deterministic content rejection, and `2` for setup, authority, capture, or persistence failure. It atomically publishes `exercise-set.json` plus `audit.json`; rejections can be retained separately with `--rejection-dir`.

Build a hash-bound AI-only development batch from explicit immutable revision selections:

```bash
python -m english_master.exercise_development_batch \
  --exercise-root curriculum/exercises \
  --bundle-paths curriculum/exercises/development-20260903-v3/batch-selection.json \
  --created-at 2026-09-03T10:15:00Z \
  --output-dir curriculum/exercises/development-batches/20260903-v3
```

The verified batch contains ten five-exercise sets (50 exercises) and covers all eleven supported types. It independently reapplies final set schema, identity, scope, type, duplicate, provenance, and M8-exclusion checks before treating the batch's AI evidence as development approval. It remains neither human review nor release approval.
