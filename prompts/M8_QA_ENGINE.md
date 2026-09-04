# GIAI ĐOẠN 16 — M8: QA ENGINE

## Objective

Complete the development-only QA Engine for immutable M7 exercise candidates. M8 must independently reload trusted M5, M6, and M7 authority, execute the fixed QA sequence, retain complete evidence, reject unsafe content, and regenerate only as a new candidate revision.

M8 does not create learner-facing AI practice prompts, perform independent human QA, revise approved curriculum in place, or authorize public release. Those activities remain outside this milestone.

## Required flow

Execute these stages exactly once and in this order for each candidate attempt:

```text
Generator
↓
Candidate
↓
Schema QA
↓
Answer QA
↓
CEFR QA
↓
Prerequisite QA
↓
Duplicate QA
↓
Language QA
↓
DEVELOPMENT_APPROVED
```

The authoritative stage mapping is:

1. `SCHEMA` — deterministic machine review;
2. `ANSWER` — deterministic machine review;
3. `CEFR` — deterministic machine review;
4. `PREREQUISITE` — deterministic machine review;
5. `DUPLICATE` — deterministic machine review;
6. `LANGUAGE` — separate candidate-bound AI review after all five machine stages pass.

A failed or errored stage stops later checks. Every remaining stage must be recorded as `NOT_RUN`; no later reviewer may override, waive, or bypass an earlier failure.

## Authority boundary

Before QA begins:

- independently reload and validate the exact M5 development snapshot, source registry, M6 development batch, M6 lesson artifacts, M7 development batch, M7 exercise set, generation audit, and both M7 AI reviews;
- derive the QA request from verified authority rather than caller assertions;
- import attempt 1 as the exact immutable M7 exercise set;
- bind every request, attempt, receipt, review, rejection, invocation, decision, and manifest with canonical IDs and SHA-256 hashes;
- reject stale, incomplete, mismatched, synthetic-authority, or path-unsafe inputs.

M8 must not mutate any M5, M6, or M7 artifact.

## Candidate and retry rules

A candidate is immutable after capture. If content QA fails:

```text
Rejected
↓
regenerate
```

- Publish all six receipts and a hash-bound rejection before retrying.
- Derive exact structured repair constraints only from blocking findings.
- Bind the next regeneration prompt to the trusted request, prior candidate, parent rejection, and repair constraints.
- Retain the exact prompt, raw structured response, factual capture metadata, and hashes.
- Host orchestration—not model output—must assign IDs, trusted bindings, status, provenance decisions, and generation metadata.
- Create a new deterministic exercise-set identity; never edit the rejected candidate in place.
- Use a strict maximum-attempt limit and never weaken a QA rule to obtain a pass.
- Treat backend, parsing, validation, review, or publication failures as operational failures, not content repair instructions.

Replay, test, mock, unsupported, parameter-mismatched, or caller-completed evidence cannot promote a regenerated candidate.

## QA requirements

### Schema QA

Validate strict schemas, canonical identity, exact M7/M6/lesson bindings, exercise IDs and sequence, `UNREVIEWED` status, generation evidence, provenance policy, and later-scope exclusions.

### Answer QA

Enforce the M7 type-specific contracts. Objective tasks require complete and unambiguous answers; distractors must be wrong but plausible. Subjective speaking and writing tasks require usable analytic rubrics and must not claim one fictional exact answer.

### CEFR QA

Verify the candidate and each exercise against the trusted lesson tier. A generator's self-declared CEFR label is not independent evidence of alignment.

### Prerequisite QA

Allow only lesson-authorized target and review references. Verify objective links and prerequisite/previous-knowledge scope against the independently reloaded graph and lesson.

### Duplicate QA

Compare a deterministic learner-facing projection that excludes volatile IDs, hashes, and generation metadata while retaining authored content, answer/rubric data, difficulty, scoring, and scope. Check exact duplicates and bounded normalized character-ngram near duplicates within the set and across prior attempts. Record the projection and comparison policy versions.

### Language QA

After stages 1–5 pass, run one separate candidate-bound comprehensive AI review covering, in order:

1. `ANSWER_ACCURACY_AND_AMBIGUITY`;
2. `CEFR_SEMANTIC_ALIGNMENT`;
3. `PREREQUISITE_OBJECTIVE_ALIGNMENT`;
4. `LANGUAGE_QUALITY`.

Bind the review to the request, candidate attempt, candidate hash, M7 batch, and hashes of the five machine receipts. A regenerated candidate requires a fresh review. Verified M7 linguistic and pedagogical reviews may support only the exact unchanged M7 candidate and must retain their limitations.

## Evidence and status limits

For every provider/model/run fact, retain the observed value or `UNKNOWN`; never invent metadata. Record explicitly that local hashes do not cryptographically authenticate a provider or model. Never claim an Internet-wide plagiarism or copyright search unless one actually occurred and is recorded.

A passing M8 run may establish only:

- `terminal_result: DEVELOPMENT_APPROVED`;
- `content_lifecycle_status: UNREVIEWED`;
- machine and AI-only development evidence.

It must always retain:

- `human_reviewed: false`;
- `release_approved: false`;
- `provider_authenticated: false` unless a future independent authentication contract is implemented.

M8 must never emit or imply `APPROVED`, `HUMAN_REVIEWED`, `RELEASE_APPROVED`, human identity, human qualifications, publisher endorsement, certification, or release authority.

## Publication and independent verification

Publish exactly one complete terminal run atomically and without overwrite:

- `DEVELOPMENT_APPROVED` with a decision;
- `REJECTED` after non-repairable failure or retry exhaustion; or
- `OPERATIONAL_FAILURE` with truthful failure evidence.

Every terminal directory must contain a canonical manifest inventorying every JSON record and hash. Verification must independently reload M7 authority and reject:

- duplicate JSON keys;
- symlinks, path escapes, unexpected files, orphan records, or missing records;
- noncanonical identities or hashes;
- attempt-count, stage-order, reviewer, short-circuit, or receipt drift;
- invalid exact timestamp chronology;
- incomplete rejection, repair, or retry lineage;
- prompts, responses, candidates, reviews, or decisions that cannot be reconstructed;
- replay, test, mock, unsupported, or fabricated promotion evidence;
- any human/release/provider-authentication claim.

Verification success means only that the retained development evidence is internally consistent with independently reloaded project authority.

## Tests

Use only authored offline fixtures and synthetic test backends. Test at minimum:

- exact M7 attempt import and six-stage success;
- every deterministic stage failure and legal `NOT_RUN` behavior;
- fresh review pass, failure, malformed response, and backend error;
- immutable failed-review to changed-candidate retry lineage;
- retry exhaustion and missing/failed regeneration;
- prompt, response, invocation, candidate, review, receipt, rejection, decision, and manifest tampering;
- exact RFC 3339 chronology, equal instants, invalid offsets, leap seconds, and future evidence;
- metadata-only duplicate and normalized near-duplicate detection;
- replay/test/mock and parameter-mismatched evidence non-promotion;
- approved, rejected, and operational run-directory verification;
- extra, orphan, missing, duplicate-key, symlink, and no-overwrite failures;
- invariant `UNREVIEWED`, `human_reviewed: false`, and `release_approved: false`.

No live network request, bulk download, external corpus, or media payload is permitted in tests. Synthetic test evidence must never be published or described as genuine provider evidence.

## Acceptance criteria

1. The fixed six-stage order is enforced independently by schemas, execution, and verification.
2. Attempt 1 is the exact verified M7 candidate; every retry is a new immutable, reconstructable revision.
3. Failures cannot be waived, edited in place, or converted into approval.
4. Machine stages and candidate-bound language review are complete and auditable.
5. Duplicate comparison ignores volatile metadata but preserves learner-facing semantics.
6. Exact chronology and complete capture/retry evidence fail closed.
7. All three terminal states publish atomically with a complete manifest and verify independently.
8. No M5, M6, or M7 immutable artifact is changed.
9. All applicable focused and full tests pass.
10. M8 makes only a development-approval claim while content remains `UNREVIEWED`.

Run focused QA/schema/CLI tests, then the complete test suite, compile the source, inspect the diff and published test bundles, report all failures and unresolved issues truthfully, and resolve applicable failures before declaring M8 complete.

Report created files, modified files, commands, tests, pass/fail status, unresolved issues, and the next recommended milestone. Then STOP. Do not start M9 or any deferred learner-facing AI practice-prompt work automatically.
