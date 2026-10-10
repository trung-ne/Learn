# Reading Module

## Current scope

The Reading Module is an English-only, static projection of current project-authored, `UNREVIEWED` lesson material. It contains exactly:

- 112 short **supplied objective reading** records from A1–B1 lesson reading exercises. Each retains its supplied passage, question, and accepted answers.
- 100 **supplied text** records from C1–C2 reading sections. These have no supplied question, so the module adds none.

B2 has no eligible reading source. German has no reading inventory. There is no source-authored intensive-reading activity, extensive-reading library, reader-choice collection, generated question, genre label, word-count target, proficiency result, or CEFR attainment claim.

The module uses an application presentation label for close reading of the supplied C1–C2 texts. It does not claim that all records are pedagogically intensive or that any individual learner completed intensive reading. No source-authored main-idea, detail, or inference labels are currently supplied. Vocabulary-in-context is limited to the exact, explicitly mapped WordSense ranges described below.

## Exact WordSense contract

A clickable range is present only when `curriculum/web-reading/v1/english-reading-map.json` explicitly binds that literal occurrence to a current English WordSense. The deterministic builder checks the current packet hash, source identity, UTF-16 start/end offsets, exact surface text, non-overlap, and the exact WordSense ID.

The browser receives only the validated range and exact `senseId`. It does not receive source hashes, source paths, provenance, source target IDs, offsets’ authored surface values, or a generic dictionary lookup.

The module never guesses a meaning by spelling, lemma, casing, morphology, nearby text, exercise binding, lesson title, or CEFR band. Unmapped text remains plain text. Selecting a mapped range reveals only the matched WordSense definition, optional IPA and Vietnamese meaning, and an existing example.

**Add to vocabulary** explicitly calls the existing local `startWordSense` lifecycle for that exact ID. It is idempotent and does not register a result, attempt, mistake, mastery change, or inferred knowledge.

## Objective answer boundary

For an objective record, the local interface compares a typed answer only with the record’s supplied accepted answers through the existing deterministic comparator. “Correct” means the response matches supplied answer data; it is not a reading score, assessment result, lesson completion, or proficiency claim.

Reader answer text and answer history are not persisted. Reading does not update course completion, Review, grammar, vocabulary outcomes, Mistake/Weakness, assessment/mastery, or a Weakness Engine.

## Local bookmarks

Bookmarks use the isolated browser-local key:

```text
english-master.reading.v1.<learnerId>.en
```

They retain only reading IDs and timestamps, are invalidated when the reading snapshot version changes, and do not retain selected passage text, annotations, typed answers, range notes, scores, or review intervals. A bookmark is not completion evidence.

## Build and validation

```bash
cd apps/web
npm run build:reading-snapshot  # only after an intentional upstream update
npm run check:reading-snapshot
```

`npm run build` checks the committed snapshot before static export. The snapshot builder only loads declared source manifests, verifies their closed packet inventories and SHA-256 values, and validates the fixed 212-record inventory before projection.

## Future expansion

Adding reading sources requires an explicit source record with browser-display authorization, exact provenance and hash binding, a source-authored or deliberately authored record type, and a clear local-state policy. Claims about extensive reading, a level, mode, genre, inference, main idea, detail, or vocabulary-in-context need explicit source/record metadata rather than a text-derived guess. Each new clickable word requires an explicit, hash-bound literal WordSense occurrence mapping.
