# Unified Review Foundation

## Purpose and scope

The unified review foundation is a local-first scheduling layer for the learner web app. It combines independent review sources into one course-scoped session without merging their records or claiming that a schedule measures proficiency.

This Step 13.2 implementation supports only:

- factual `correct` and `incorrect` outcomes from deterministically checked lesson exercises; and
- existing WordSense review candidates owned by the vocabulary module.

All supplied learning content remains `UNREVIEWED`. A local outcome or schedule does not establish grammar knowledge, vocabulary mastery, CEFR placement, learner proficiency, certification, human review, release approval, provider behavior, or public-distribution authority.

## Source ownership and storage

Generic objective-exercise review state is stored independently by learner, target language, and course:

```text
english-master.review.v1.<learnerId>.<language>.<course>
```

Each record retains only its lesson/exercise identity, first/last review timestamps, review/correct/incorrect counts, deterministic ease and mastery values, interval stage, next-review timestamp, and last factual result. It never stores learner answers, prompts, free text, transcripts, packet hashes, source target IDs, provenance, provider data, or knowledge-graph IDs.

Vocabulary retains its separate language-scoped `english-master.vocabulary.v1...` store and its existing lifecycle. The unified queue reads vocabulary candidates but does not rewrite or reinterpret vocabulary records. Course progress, generic review progress, and vocabulary progress are separate best-effort browser writes; no cross-key transaction is claimed.

Invalid, malformed, scope-mismatched, unknown, or stale local records fail closed. Existing lesson completion/runner state is not migrated into a synthetic review history.

## Scheduling

For a newly observed objective exercise, the deterministic review ladder is:

```text
10 minutes → 1 day → 3 days → 7 days → 14 days → 30 days → 60 days
```

A correct result advances one stage. An incorrect result resets the item to the 10-minute stage. `ease` is an aggregate local signal adjusted by result and retained for future scheduling-policy revisions; this version intentionally preserves the predictable stated ladder. Timestamps are calculated in UTC.

The normal session contains at most ten items. It prioritizes recent incorrect outcomes, then due items, using due time, source order, and stable identifiers as tie-breakers.

## Evidence boundary

Only exercise types already scored by the deterministic local exercise checker can create generic review observations. Self-practice, writing and speaking rubrics, pronunciation, AI-practice protocols, drafts, lesson completion, skipped unsupported activities, and time spent cannot create review outcomes.

The review screen reuses supplied objective exercises or existing WordSense cards. It does not generate replacement questions, diagnoses, corrections, or practice content.

## Grammar practice progress (Step 13.4)

`/learn/en/grammar` is a separate English-only local state layer. Its grammar target catalog is a dedicated safe snapshot built from explicit current English packet exercise bindings and allocation records whose dimension is exactly `grammar`. The main learner display snapshot does not supply grammar mappings, and M15 `DRAFT` planning data is never used.

Only an existing deterministic objective outcome can update a target that the dedicated catalog explicitly binds to that exact `lessonId + exerciseId`. Writing, speaking, self-practice, AI protocols, drafts, lesson completion, generic review history, prose, titles, objectives, and unbound activities cannot update grammar state. When an activity has multiple explicit grammar links, the same aggregate outcome is recorded for each; this does not decide which target caused an incorrect result.

Grammar state is isolated at `english-master.grammar.v1.<learnerId>.en` and retains only aggregate counts, local score, stage, and timestamps. It uses the 1/3/7/14/30/60-day ladder. `locally_consolidated` means only the final local schedule stage, never verified grammar knowledge, diagnosis, CEFR attainment, placement, or proficiency. German has no grammar route because its current pilot lacks an equivalent granular binding inventory. See [Grammar Mastery](GRAMMAR_MASTERY.md).

## Activity outcome patterns (Step 13.3)

The `/learn/{language}/{level}/mistakes` page is a read-only projection of the current generic objective-review state. It resolves each retained `lessonId + exerciseId` only against the current course catalog and shows an entry only when that lesson and objectively scored exercise still exist.

Each entry contains aggregate correct/incorrect/review counts, an incorrect-outcome percentage, the latest factual result, timestamps, and the supplied lesson title, topic, and objectives as **associated lesson context**. Two or more recorded incorrect outcomes are described only as **repeated incorrect outcomes**. This is a recurrence threshold, not a claim that the learner is weak, why they answered incorrectly, or what grammar they need.

The view stores no separate state and shows no learner answer, prompt, attempt history, correction, error type, grammar ID, target ID, packet hash, provenance, vocabulary record, or knowledge-graph record. Missing, stale, course-mismatched, or no-longer-objective entries are excluded without modifying local storage. The only actions return to the supplied lesson or course review route.

## Deferred work

A future semantic Mistake / Weakness Engine may assign error types or grammar relationships only after an explicitly authored and validated exercise-to-error mapping exists. It must not infer those mappings from lesson prose, objectives, titles, or the M15 planning graph.

Grammar Mastery (Step 13.4) remains separate. The broad M15 graph is `DRAFT` planning material and cannot be exposed as learner grammar instruction or used to infer exercise-to-grammar mappings. A future grammar module needs independently authored, validated learner-facing grammar references and explicit exercise mappings.

## Local reset

The review page can reset only generic objective-exercise history for its current learner/language/course scope. It does not reset course completion or vocabulary state.
