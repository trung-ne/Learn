# Grammar Mastery — Local Practice Progress

## Scope

The Grammar Mastery module is an English-only, browser-local practice tracker for the committed Full A1–C2 learner corpus. It exposes only grammar targets that have an explicit, deterministic binding to a currently supplied objectively scored exercise.

It does not provide a German grammar route. The current German A1 pilot has no equivalent granular grammar-target-to-exercise mapping, so the app deliberately does not infer one.

## Authoritative input boundary

`apps/web/scripts/build-grammar-snapshot.mjs` reads the six committed English allocation records and the matching immutable English packet manifests declared in `apps/web/scripts/lib/sources.mjs`.

For each allocation target whose dimension is exactly `grammar`, the builder:

1. requires exactly one `INTRODUCE` allocation lesson;
2. verifies every current packet byte hash against its manifest;
3. accepts only current objective exercise types that explicitly retain that target in `target_ids`;
4. requires at least one such binding; and
5. derives only grammar-to-grammar prerequisite edges.

The committed learner snapshot contains application-owned opaque target IDs, supplied introduction-lesson title/topic, band/tier, grammar-only prerequisite IDs, and `{ lessonId, exerciseId }` bindings. It strips source target IDs, broad concept IDs, packet hashes, source paths, provenance, target dimensions, and unrelated targets.

The module never reads the M15 knowledge graph. M15 remains `DRAFT` planning material and is not a grammar mapping source or learner-facing instruction source.

Build only after an intentional upstream source change:

```bash
cd apps/web
npm run build:grammar-snapshot
```

For ordinary verification:

```bash
npm run check:grammar-snapshot
```

## Local state and schedule

Grammar state is stored only in the current browser:

```text
english-master.grammar.v1.<learnerId>.en
```

A target receives a local record only after its explicitly bound objective exercise produces a deterministic correct or incorrect result. The record contains aggregate correct/incorrect counts, a local score, interval state, and timestamps. It never stores learner answers, prompts, free text, raw assessment data, source IDs, hashes, provenance, provider data, or knowledge-graph IDs.

The fixed local ladder is:

```text
1 day → 3 days → 7 days → 14 days → 30 days → 60 days
```

A correct result advances one stage; an incorrect result resets to the first stage. `locally_consolidated` means only that the target reached the final browser-local schedule stage. It is not verified grammar mastery, a competency judgement, CEFR attainment, placement, or proficiency evidence.

Malformed, scope-mismatched, stale-version, or internally inconsistent browser data fails closed. Removed targets are ignored in current summaries and queues.

## Multiple target bindings

One supplied exercise can have several explicit grammar target bindings. Each deterministic outcome is recorded identically for each bound target. This is a transparent bookkeeping policy: the app does not weight, split, or determine which target caused an incorrect result.

Lesson completion, writing/speaking/self-practice, AI protocols, drafts, stale activities, generic review history, lesson prose, titles, objectives, and unbound exercises cannot create grammar records.

## Limits

All source and derived content remains `UNREVIEWED`. The module creates no grammar explanations, corrected learner sentences, error categories, root-cause analysis, recommendations, human-review claim, release claim, provider claim, or public-distribution authority.
