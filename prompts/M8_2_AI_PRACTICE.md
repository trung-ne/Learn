# M8.2 — AI Practice Prompt Pilot Instructions

## Scope

Build only M8.2 lesson-specific AI practice prompt artifacts from the exact verified M6 development-approved batch. Do not start M9, edit upstream immutable artifacts, download a corpus/media payload, or claim human/release/provider approval.

## Required pilot

Publish exactly four prompt artifacts for each of the ten selected M6 lessons:

- `LISTENING`
- `SPEAKING`
- `PRONUNCIATION`
- `WRITING`

Each artifact must be host-bound to `lesson_id`, lesson/audit hash, CEFR, known/target vocabulary and grammar, functions, pronunciation references, prerequisite context, prompt version, and factual provenance. Backend/capture content, if any, is narrow untrusted project-authored payload only; orchestration supplies IDs, hashes, authority, lifecycle, and provenance.

## Mandatory modality constraints

- Listening keeps transcript and answer material private at the opening and exposes only one comprehension question per turn.
- Speaking supplies roleplay roles, a lesson goal, stop condition, and one invitation/question per turn.
- Pronunciation requires audio for acoustic evaluation; non-audio input yields `NOT_ASSESSED`, never a fictional score.
- Writing is draft-first, feedback-bounded, preserves learner meaning, and does not ghostwrite a replacement.

## Evidence boundary

Every artifact remains `UNREVIEWED`. The only batch-level successful result is `MACHINE_VALIDATED`. Set `human_reviewed`, `release_approved`, and `provider_authenticated` to false. Use `UNKNOWN` for unavailable provider/model/run facts. Do not imply an external search or live behavior validation that was not actually performed.

## Required verification

```bash
python -m english_master.ai_practice verify-pilot --pilot-dir <immutable-pilot-directory>
python -m pytest -q
python -m compileall src
git diff --check
```

Inspect the actual published forty prompt files after verification. Repair only M8.2 defects, report M8 PASS or FAIL, then stop without beginning M9.
