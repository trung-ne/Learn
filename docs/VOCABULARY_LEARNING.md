# Vocabulary Learning Module

## Purpose and boundary

The vocabulary module is a local-first WordSense learning system for the English learner app. A word form and each meaning are separate records, so a future `run` “move quickly” record and `run` “operate” record can receive independent learning state.

It does not use `curriculum/taxonomy/taxonomy.json` as learner content. That collection is a `DRAFT` taxonomy prototype, not a learner-facing inventory. The module instead reads independently authored records in `curriculum/web-vocabulary/v1/` and exports a safe learner-facing snapshot.

The system supports English A1–C2 inventory batches. The first committed batch contains twenty original A1.1 records tied explicitly to the first five A1 Unit 1 lesson packets. Every record remains `UNREVIEWED`.

## Content and build contract

Each inventory record carries a stable application-owned ID, language, band/tier, lemma, sense number, part of speech, definition, optional Vietnamese meaning and IPA, original examples/collocations, introduction lesson, recall answer data, and explicit exercise bindings.

A binding includes its lesson/exercise identity, the upstream target anchor, and the current packet-byte SHA-256. The builder checks packet hashes, the exercise type, and that the target anchor actually belongs to the referenced exercise. It emits no packet hashes, source target IDs, taxonomy data, provenance fields, or other build-only metadata to the browser.

Run from `apps/web`:

```bash
npm run build:vocabulary-snapshot
npm run check:vocabulary-snapshot
```

`npm run build` checks both the curriculum and vocabulary snapshots before the static Next.js build.

## Local learner lifecycle

Vocabulary state is a separate browser-local document, scoped by learner and target language:

```text
english-master.vocabulary.v1.<learnerId>.en
```

No account, server synchronization, learner answer text, free text, prompt text, or per-attempt history is stored. The record retains only:

- `learning`, `reviewing`, or `mastered` state;
- attempt, correct-attempt, and mistake counts;
- deterministic 0–100 local mastery score;
- current interval index;
- introduction, latest-attempt, latest-mistake, and next-review timestamps.

The state is created only when the learner explicitly starts a word or submits a result for an explicitly bound objective exercise. Visiting a lesson or vocabulary page alone does not add records.

Correct results use the UTC review ladder **1, 3, 7, 14, 30, 60 days**. An incorrect result increments mistakes, resets the ladder to learning, and schedules the next review one UTC day later. `mastered` is reached only after the final successful interval, and is still reviewed after sixty days. These are deterministic self-study indicators, not validated evidence of durable knowledge, learner proficiency, CEFR placement, certification, or curriculum authority.

The normal review queue contains at most ten senses and prioritizes recent mistakes, then due senses, using deterministic due-date, score, introduction-order, and ID tie-breakers.

## Lesson links and limitations

Only explicitly bound, objectively checked lesson exercises may create WordSense practice events. Lesson completion, self-practice, writing drafts, AI-practice protocols, unsupported exercises, and unbound exercises never change vocabulary attempts or scores. A linked generic lesson exercise is only an authored local practice observation; it does not prove that the exercise exhaustively measures a sense or that a learner has mastered it.

Course progress and vocabulary progress use separate localStorage keys. Writes are independently best-effort and are not cross-key transactional.

## Dictionary lane

The separate [Dictionary / Language Library](DICTIONARY_LANGUAGE_LIBRARY.md) contains dictionary-only original-authored lexical records and independent browser-local study signals. It neither creates lesson-vocabulary progress nor relaxes this module's requirement that every WordSense record be bound to a current objective lesson exercise.

## Expansion

To add content, author a new versioned JSON batch under `curriculum/web-vocabulary/v1/` using `web-vocabulary-inventory.schema.json`, explicitly bind each record to current immutable English lesson packets, then rebuild and check the snapshot. Stable IDs must retain the same sense meaning across versions. Removed records remain in existing local browser storage but are hidden from inventory views and queues; the module does not destructively rewrite unrelated learner state.

A future German inventory needs its own explicitly authored, language-bound data and validation before `/learn/de/vocabulary` is made available.
