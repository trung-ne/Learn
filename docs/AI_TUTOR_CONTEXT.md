# AI Tutor Context

## Purpose

Tutor Context prepares a bounded prompt for a learner to copy into an external AI tool. It helps the external tool keep practice inside a learner's selected course scope without adding a provider, chat session, API key, account, server endpoint, or network request to English Master.

The application does not send context anywhere. It stays in the browser until the learner explicitly copies it. Once pasted into another tool, that tool's privacy terms apply.

## Local declaration and scope

A learner selects a **self-reported current A1–C2 band** and may select an aspirational target band plus structured current goals. These are browser-local preferences. They are not a placement result, CEFR assessment, certification, or conclusion derived from lessons, review results, WordSense records, or grammar records.

A Tutor Context page only copies the current course when its band is at or below the self-reported current band. An aspirational target never permits higher-level course material. An incompatible page shows its boundary instead of exporting the course.

## Included local signals

When they exist and resolve to the current committed inventories, a context may include:

- the self-reported band, permitted course, and structured goals;
- exact local WordSense states: `learning`, `reviewing`, or `mastered`;
- exact local English grammar-target states: `practising`, `reviewing`, or `locally_consolidated`;
- recent locally accessed lesson titles;
- supplied activities with aggregate, objective incorrect outcomes; and
- existing scheduled local review items.

The terms describe local records only. A WordSense or grammar state is not general language knowledge. A locally completed lesson is not proof of proficiency. An incorrect objective outcome does not identify a grammar/vocabulary cause or establish a weakness diagnosis.

Every projection is capped and deterministic. Stored records that no longer resolve to the current catalog are excluded.

## Excluded information

Tutor Context never exports learner identifiers, local-storage keys, raw timestamps, raw exercise answers, writing drafts or revisions, audio, transcripts, provider material, credentials, internal IDs, or generated response history. It does not record a copied prompt, an external response, or any feedback from an external tool.

Previewing or copying context never updates Review, Vocabulary, Grammar, Activity Outcome Patterns, assessment/mastery, or course progress.

## Prompt boundary

The exported wrapper instructs an external tool to treat the local records as learner-provided signals, remain inside the declared permitted course, use only supplied scope, ask one bounded practice turn at a time, and avoid proficiency, assessment, diagnostic, or causal claims.

This feature does not reuse or map the separate M8.2 historical AI-practice pilot. Current web content remains `UNREVIEWED`; Tutor Context does not change its lifecycle, authorize new curriculum content, or establish pedagogical quality.
