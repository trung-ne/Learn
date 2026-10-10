# Assessment and Mastery

## Scope

`english_master.assessment_mastery` is an offline deterministic layer over the six existing Full A1–C2 development corpora. It reverifies every source run and the common M15 population binding before projecting existing objective exercises. It does not generate or rewrite questions, use external data or media, call a model/provider, or change source packets or taxonomy schemas.

Every assessment package and source packet remains `UNREVIEWED`. A build or score is not human review, release approval, provider evidence, official CEFR endorsement, certification, a validated placement diagnosis, or a learner-proficiency claim.

## Immutable inventory

One run contains exactly:

- 300 lesson quizzes, one per verified packet, with all eligible objective items;
- 60 ten-item unit tests, one for every M16 unit-test scope;
- 6 twenty-item official-band tests, one each for A1, A2, B1, B2, C1, and C2;
- 1 twenty-four-item placement package, with two items from distinct lessons in each internal tier.

Published files are hash-bound and no-overwrite:

```text
curriculum/assessments/v1/runs/<deterministic-run-id>/
  manifest.json
  packages/<assessment-id>.json
```

Verification reruns all six Full-corpus verifiers and reconstructs every expected package. It rejects source, scope, item, hash, or closed-inventory drift.

## Item projection and selection

Eligible items are project-authored, `media_required: false`, and deterministically scoreable: multiple choice, fill blank, matching, ordering, and individual questions in reading or transcript-only listening exercises. Existing prompts, stimuli, options, and answer contracts are preserved. Speaking, writing, rubric-scored tasks, pronunciation assessment, and audio-dependent evaluation are excluded.

Each item binds its packet/exercise/question identity, packet hash, granular allocation target IDs, target dimensions, and mapped broad M15 concept IDs. Reading/listening questions use their stable one-based source index because those source questions have no ID.

Selection policy `ASSESSMENT_MASTERY_V1` uses SHA-256 ranking. A unit test first covers all five assessed lessons, then favors unused exercise types and target dimensions. A band test first covers all ten units and uses the same diversity-aware fill. Placement takes two ranked items per internal tier and requires distinct source lessons.

## Scoring and placement

A submission must bind the package hash and include exactly one response for every item. String answers compare after Unicode NFKC, case folding, and whitespace normalization. Ordering remains order-sensitive; matching accepts the complete canonical pair set in any pair order. Validation and scoring finish before state changes.

Placement scores each internal tier independently. `suggested_start_tier` is the first tier scoring below 2/2, or `C2.2` when all tiers meet 2/2. This fixed offline heuristic is not a validated diagnostic or CEFR certification.

## Local concept state

The caller separates learners by selecting a local file path, such as `data/learner-state/local-01/concept-state.json`. The document is a JSON array sorted by `concept_id`. Every record has exactly seven keys:

```text
concept_id, attempts, correct, incorrect, mastery, last_seen, next_review
```

There is no learner profile, account, database, attempt history, hidden metadata, idempotency token, or cross-learner aggregation. Each selected item's result updates each mapped broad M15 concept once:

- `attempts = correct + incorrect`;
- `mastery = round(correct / attempts, 4)`;
- `last_seen` is the caller-supplied UTC `seen_at`;
- any incorrect result schedules review immediately;
- a correct result below 0.80 mastery schedules +1 day;
- a correct result at or above 0.80 with fewer than 3 attempts schedules +3 days;
- 3–5 attempts schedules +7 days;
- 6+ attempts schedules +30 days.

State is local single-writer data. A complete new state is schema-validated and written to a same-directory temporary file before atomic `os.replace`. Replaying a valid submission intentionally records another attempt because no event history or idempotency field exists.

## Multilingual core boundary

The original assessment and array-state contracts remain the backward-compatible English v1 lane. Future language-scoped packages use an explicit language-bound package/submission wrapper and a `learner-concept-state-v2` envelope at `data/learner-state/<language_code>/...`. The scorer rejects a package, submission, state, or `kg_<language_code>_...` concept identifier from another declared language. This v2 boundary establishes state isolation only; it does not migrate existing state, create German assessments, or change the fixed English inventory.

## CLI

Run from the repository root:

```bash
python -m english_master.assessment_mastery create-request \
  --a1-run-dir ... --a1-population ... --a1-blueprint ... --a1-allocation ... --a1-content-manifest ... \
  --a2-run-dir ... --a2-population ... --a2-blueprint ... --a2-allocation ... --a2-content-manifest ... \
  --b1-run-dir ... --b1-population ... --b1-blueprint ... --b1-allocation ... --b1-content-manifest ... \
  --b2-run-dir ... --b2-population ... --b2-blueprint ... --b2-allocation ... --b2-content-manifest ... \
  --c1-run-dir ... --c1-population ... --c1-blueprint ... --c1-allocation ... --c1-content-manifest ... \
  --c2-run-dir ... --c2-population ... --c2-blueprint ... --c2-allocation ... --c2-content-manifest ... \
  --output curriculum/assessments/v1/request.json

python -m english_master.assessment_mastery build \
  --request curriculum/assessments/v1/request.json \
  --output-root curriculum/assessments/v1/runs

python -m english_master.assessment_mastery verify \
  --request curriculum/assessments/v1/request.json \
  --run-dir curriculum/assessments/v1/runs/<deterministic-run-id>

python -m english_master.assessment_mastery score \
  --package <package.json> --submission <submission.json> \
  --state data/learner-state/local-01/concept-state.json
```

All commands are local and make no network or provider call.

Adaptive review planning and observation are documented in [ADAPTIVE_REVIEW.md](ADAPTIVE_REVIEW.md). They use a separate caller-owned schedule state and the fixed 1/3/7/14/30/60-day ladder without changing this assessment inventory or its seven-field aggregate learner state.

## Static web projection

The separate, English-only static web consumer is documented in [WEB_ASSESSMENT.md](WEB_ASSESSMENT.md). It verifies and projects the pinned immutable inventory into browser-local attempts; it neither replaces this Python scorer nor changes its file-backed learner-state contract.
