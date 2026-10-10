# Web Assessment

## Scope

The static web app is a separate browser-local consumer of the existing English Assessment + Mastery run:

```text
assessment_38118701d2db5edb1013b6584591b78bd3d697cd3d47367af8c05eebc261c1d3
```

Its committed projection is built only from the immutable, hash-bound run packages. It does not generate questions, alter source packages, call a provider, make a network request, or replace the Python Assessment + Mastery scorer.

All projected content remains `UNREVIEWED`.

## Availability and hierarchy

The web projection is English-only and contains exactly 300 lesson quizzes, 60 unit checkpoints, six level tests, and one placement package. It displays the requested hierarchy in this order:

1. Placement — available as a supplied 24-item package.
2. Lesson quiz — available from matching English lesson pages.
3. Unit checkpoint — available from matching English level catalogs.
4. Skill checkpoint — unavailable; no immutable package validly assesses every requested skill.
5. CEFR level test — available as a supplied band-level package, not CEFR certification.
6. Comprehensive assessment — unavailable; the inventory cannot assess speaking, writing, pronunciation, or audio listening.

German has no language-scoped assessment package and receives no placement, score, or inferred availability result.

## Local attempts and scoring

Assessment state is scoped to the browser-local learner identifier, `en`, and the pinned run ID. It is separate from lesson progress, vocabulary, grammar, review, and the Python seven-field concept-state format.

A package can be not started, have a locally persisted draft, or retain submitted attempts. A submission requires a complete response for every supplied item and the matching package hash. Retakes preserve earlier local attempts and append a new one. Submitted attempts retain only factual item correctness, applicable target bindings, score totals, submission time, and required package/run identities; raw answers are not retained after submission.

The browser deterministically scores only no-media objective contracts: multiple choice, fill blank, matching, ordering, reading questions, and transcript-only listening questions. String matching uses the existing normalized answer behavior; ordering is sequence-sensitive and matching requires every supplied pair. Placement reproduces the source package’s fixed suggested-start-tier heuristic only.

## Evidence dashboard

The dashboard shows direct browser-local results only:

- Vocabulary and grammar count only items with explicit target-dimension bindings.
- Reading counts only submitted reading items.
- Listening counts only submitted transcript-only listening items; it is not audio-listening assessment.
- Writing, speaking, and pronunciation are `NOT_ASSESSED`.
- Retention has no score. Existing review scheduling is scheduling evidence only, not a retention measurement.

It first identifies missing submitted checkpoint types. Once those stages have local evidence, it can state the lowest directly measured local row as a factual result. It does not identify a learner as weak, infer a cause, diagnose ability, or infer proficiency.

## Non-claims

Browser-local results do not unlock content, determine level completion, certify CEFR attainment, diagnose placement, establish mastery or proficiency, establish learner outcomes, or create human/release/provider authority. Existing course content stays navigable. A future actual progression policy would need valid evidence for every required skill before it could impose an access gate.

## Snapshot maintenance

From `apps/web`:

```bash
npm run build:assessment-snapshot
npm run check:assessment-snapshot
```

Run the build command only after an explicit upstream assessment update. Ordinary verification and `npm run build` use the check command, which fails if the committed web projection drifts from the pinned immutable run.
