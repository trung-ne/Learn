# M15 — Populate Full Curriculum Knowledge Graph

Populate a bounded, original-authored knowledge graph for all twelve internal curriculum tiers: A1.1, A1.2, A2.1, A2.2, B1.1, B1.2, B2.1, B2.2, C1.1, C1.2, C2.1, and C2.2.

Required dimensions:

- grammar
- vocabulary senses
- communicative functions
- pronunciation
- discourse
- pragmatics
- collocations
- lexical chunks
- topics
- skills

Create knowledge targets and explicit typed dependencies only. Preserve deterministic IDs, canonical ordering, prerequisite closure, and internal-tier placement. Example dependency chain:

```text
present simple → adverbs of frequency → routines → discussing habits
```

This milestone does **not** create full lessons, lesson prose, dialogues, readings, scripts, exercises, answer keys, media, or learner-facing prompts. M2 remains the small taxonomy prototype; do not mutate M2 or the hash-bound M5 architecture. M15 output is a separate versioned, immutable development artifact.

All content must be original project-authored. Do not copy, quote, transform, or ingest external educational payloads. Reference-only citations may identify eligible sources and locators but must not contain source wording. Do not claim exhaustive English coverage, official CEFR endorsement, human review, release approval, or lesson-generation authority. `.1` and `.2` are internal subdivisions, not official CEFR levels.

Every shard and aggregate must be schema-valid, hash-bound, deterministic, independently re-validated, and explicitly `DRAFT`/`UNREVIEWED`, fixture/development-only, with `external_content_used: false` and no network access.