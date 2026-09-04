# M8 QA Engine Development Gate

## Boundary

M8 is the development gate after M7. It does not implement the deferred learner-facing AI practice prompts, replace M9 independent human QA, or perform M10 revision governance.

The engine processes only an independently reverified M7 `DEVELOPMENT_APPROVED` batch and keeps every candidate exercise set `UNREVIEWED`. Its strongest successful terminal evidence is `DEVELOPMENT_APPROVED`; it never emits content-lifecycle `APPROVED`, `HUMAN_REVIEWED`, or `RELEASE_APPROVED`.

## Required state machine

```text
Generator → Candidate → Schema QA → Answer QA → CEFR QA → Prerequisite QA
          → Duplicate QA → Language QA → DEVELOPMENT_APPROVED

Any content failure → immutable rejection → regeneration request → new candidate revision
```

The orchestrator, not a generator or reviewer, controls transitions. Each stage receives the unchanged candidate and publishes a hash-bound receipt. A failed or errored stage prevents all later stages from running; those stages are recorded as `NOT_RUN`.

## Authority and gates

Before candidate materialization, the engine independently reloads M5 structure and development authority, M6 lessons and development batch, M7 exercises, audits, both role-specific AI reviews, and the M7 development batch. An M8 request must be timestamped no earlier than the bound M7 batch-level development evidence. Attempt 1 is the exact verified M7 exercise set, not caller-supplied content.

- **Schema QA** validates the exercise-set schema, canonical ID/hash, exact verified lesson and M6/M7 bindings, generation evidence, later-milestone scope exclusions, and `UNREVIEWED` lifecycle state.
- **Answer QA** reapplies M7 type-specific answer, ambiguity, rubric, media, and size checks.
- **CEFR QA** derives the expected level from the verified lesson rather than trusting the candidate.
- **Prerequisite QA** rebuilds allowed target/review references and objective scope from verified M6 authority.
- **Duplicate QA** compares a versioned learner-facing projection. It excludes IDs, hashes, and volatile generation metadata while retaining authored content, answers/rubrics, scoring, difficulty, and scope. Exact and bounded normalized character-ngram near duplicates are checked within the candidate and against prior attempts.
- **Language QA** is a separate comprehensive AI pass covering answer accuracy and ambiguity, CEFR semantics, prerequisite/objective alignment, and language quality. It runs only after five machine passes and binds the candidate plus all five receipt hashes.

Verified M7 linguistic and pedagogical reviews can support only the exact unchanged M7 set. Every regenerated candidate requires a fresh candidate-bound review. To assert independence for a regenerated candidate, the retained generation and review invocations must have distinct, non-`UNKNOWN` factual execution IDs; otherwise the review is retained as failed development evidence. AI review is development evidence, never human/native-speaker review.

## Rejection, regeneration, and operational failures

The engine never edits a failed candidate. It retains the complete attempt and six receipts, then creates a rejection containing exact receipt hashes and structured repair constraints derived from blocking findings. The next generation prompt binds the trusted request, prior candidate, parent rejection, M7 generation authority, and repair constraints. Host code injects deterministic IDs, hashes, status, and provenance into a new candidate.

The default hard limit is three attempts. Checks may not be relaxed. Exhaustion creates `RETRY_LIMIT_EXHAUSTED` evidence, never partial approval. Replay, test, mock, unsupported, parameter-mismatched, or provider-authentication-asserting capture evidence cannot promote a regenerated candidate.

Backend, parsing, candidate assembly, QA-stage, semantic-review capture, semantic-review processing, and record-construction failures are operational failures. A capture failure before any response is retained separately from a post-capture review failure; neither is converted into content repair instructions. If the clock cannot provide an orderable observation timestamp while a failure record is being constructed, the record explicitly identifies its retained last-known-safe or request-time boundary rather than inventing an execution time.

## Capture evidence

M8 host code constructs every invocation record. It retains:

- exact prompt and raw structured response;
- recomputed prompt and response hashes;
- requested and independently captured effective parameters and seed, plus their equality results;
- observed capture mode;
- provider, model, and provider run ID, using `UNKNOWN` when unavailable;
- exact request, attempt, rejection, and repair bindings;
- host observation timestamp.

`provider_authenticated` remains false. A backend's authentication assertion is retained separately but is not trusted. Local content hashes prove internal consistency, not provider identity or model execution.

Static CLI capture files are replay-only and cannot promote a retry or fresh language review. The CLI can still approve an unchanged M7 candidate through its already verified dual-role legacy reviews. A session callback retains its response but does not establish provider-applied parameters or seed, so it cannot promote a run. A promotable integration must return independently captured effective parameters and seed through the typed backend interface; even then no provider authentication is claimed.

## CLI

Run M8 for the unchanged verified M7 candidate:

```bash
python -m english_master.qa_engine run \
  --lesson-id A1-U01-L01 \
  --created-at 2026-09-04T06:00:00Z \
  --output-dir <new-immutable-directory>
```

Optional retained response documents have the form:

```json
{ "captures": [ ... ] }
```

They may be supplied with `--regeneration-captures` and `--review-captures` to exercise replay/rejection paths. `--candidate-captures` remains a compatibility alias for `--regeneration-captures`; it never replaces attempt 1.

Independently verify any approved, rejected, or operational terminal run against current M7 authority:

```bash
python -m english_master.qa_engine verify --run-dir <immutable-run-directory>
```

For `run`, exit code `0` means development approval, `1` means content rejection, and `2` means operational/setup failure. A valid `verify` returns `0` for any internally consistent terminal state; invalid evidence returns `2`.

## Publication and verification

Publication builds a complete manifest, writes a temporary immutable bundle, independently verifies it against M7 authority, and only then performs an atomic no-overwrite rename. A run contains:

- one request;
- every candidate attempt and exactly six receipts per attempt;
- all model invocations and AI reviews;
- every content rejection;
- at most one operational failure;
- a development decision only for `DEVELOPMENT_APPROVED`;
- one exact file/hash inventory manifest.

Run verification rejects duplicate JSON keys, symlinks, unsafe or extra paths, missing/orphan records, noncanonical IDs or hashes, stage or reviewer drift, illegal `NOT_RUN`, invalid chronology, timestamps after the verifier's trusted current-time boundary, incomplete rejection/repair lineage, unreconstructable prompts/responses/candidates/reviews, attempt-limit violations, and false human/release/provider-authentication claims.

Verification success means only that development evidence is internally consistent with independently reloaded project authority.

## Evidence limitations

No Internet-wide plagiarism/copyright search, human language review, provider authentication, or public-release approval is implied unless a future separate workflow actually performs and records it. M8 completion is development-infrastructure completion only.
