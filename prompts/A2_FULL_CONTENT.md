# Full A2 Content

This prompt contract describes the bounded Full A2 development corpus. It consumes the hash-bound M15 population and M16 A2 blueprint, then compiles one original-authored content unit for each of ten blueprint units and five lessons per unit.

The compiler must preserve lesson IDs, global ordering, tier (`A2.1` or `A2.2`), lesson kind, targets, and prerequisites from the blueprint. Packets remain `PROJECT_AUTHORED` and `UNREVIEWED`.

Each packet contains structured sections, multiple-choice, fill-blank, reading, and speaking exercises, plus listening, speaking, pronunciation, and writing protocols. Listening is transcript-only with a private transcript-before-answer boundary. Pronunciation assessment is audio-only and returns `NOT_ASSESSED` without audio. Writing is draft-first and feedback-only; the tutor must not replace the learner draft.

The offline service validates schemas, source hashes, references, prerequisite order, exercise answer contracts, modality/media boundaries, prohibited claims, and normalized exact duplicates. It publishes immutable no-overwrite runs and supports deterministic 10–15 lesson unit-stratified samples. These checks establish repository consistency only and do not claim human review, live provider behavior, CEFR endorsement, release approval, or public distribution.
