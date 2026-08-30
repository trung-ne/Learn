# M1 — Source Registry, Licensing and Media Source Governance

## Objective

Build the source governance system for English Master.

This milestone determines which external sources may be:

- referenced
- downloaded
- ingested
- transformed
- redistributed
- used for text
- used for audio
- used for video
- used for transcripts
- used for linguistic analysis

This milestone must cover TEXT, AUDIO and VIDEO sources.

Do NOT build the full crawler yet.

Do NOT bulk-download datasets.

Do NOT generate curriculum lessons.

Do NOT start M2.

---

# Read First

Before making changes, read:

- PROJECT_RULES.md
- AGENTS.md or CLAUDE.md as applicable
- docs/PROJECT_SPEC.md
- docs/DATA_POLICY.md
- docs/CURRICULUM_SCHEMA.md
- docs/QA_SPEC.md
- docs/MILESTONES.md
- existing schemas
- existing tests

Inspect the current repository before modifying it.

---

# Core Principle

Availability on the Internet does NOT mean content may be copied.

Every external source must have an explicit governance decision.

Possible source states:

- APPROVED
- REFERENCE_ONLY
- QUARANTINED
- REJECTED

If licensing is uncertain:

QUARANTINED.

If redistribution rights differ between text/audio/video:

record separate media-specific permissions.

Do not simplify different rights into one generic "allowed" boolean.

---

# Source Categories

Research candidate sources in the following groups.

## A. Authoritative Reference Sources

Research current official information for sources such as:

- Council of Europe CEFR
- CEFR Companion Volume
- English Profile
- Cambridge English public specifications
- British Council public reference resources

These sources may be useful for:

- CEFR taxonomy
- curriculum coverage
- linguistic classification
- assessment design

They may be REFERENCE_ONLY.

Do not assume their educational content may be copied.

---

# B. Open Text / Sentence Corpora

Research candidates such as:

- Tatoeba
- open linguistic corpora
- public-domain English texts
- other properly licensed sentence datasets

Determine:

- text license
- attribution requirements
- redistribution
- modification
- commercial use
- official download/API availability

---

# C. Audio / Speech Corpora

Research candidates such as:

- Mozilla Common Voice
- Tatoeba audio
- LibriVox
- open speech datasets
- public-domain recordings
- other properly licensed English speech corpora

For every audio source determine:

- whether audio files may be downloaded
- whether files may be stored
- whether files may be transformed
- whether clips may be created
- whether audio may be redistributed
- whether transcripts may be created
- whether generated exercises may reference the audio
- whether commercial use is allowed
- required attribution

Do not assume the text license and audio license are identical.

---

# D. Video Sources

Research legally usable video sources.

For each source determine separately whether the project may:

- download video
- store video
- extract audio
- generate transcripts
- generate timestamps
- create clips
- generate exercises based on the media
- redistribute original media
- redistribute derived media

If only embedding/linking is permitted:

do not mark downloading as allowed.

Represent this explicitly.

---

# E. VOA Learning English

Research the CURRENT official VOA copyright/public-domain policy.

Important:

VOA pages may contain:

- VOA-produced content
- third-party agency material
- images
- video
- audio
- text

Do not assume everything hosted on a VOA page has the same copyright status.

Design policy capable of excluding third-party content.

---

# F. LibriVox

Research current official licensing/public-domain information.

Record jurisdiction-related caveats where appropriate.

Separate:

- recording rights
- underlying book/text rights

---

# Source Registry

Implement or extend a structured source registry.

Preferred location:

sources/registry.yaml

Each source should support fields equivalent to:

id
name
owner
homepage
description

content_types:
  - text
  - audio
  - video
  - transcript
  - metadata

access:
  preferred_method
  api_url
  dataset_url
  crawl_allowed
  download_allowed

license:
  name
  url
  reviewed_at
  notes

permissions:
  reference_allowed
  ingest_allowed
  store_allowed
  modify_allowed
  redistribute_allowed
  commercial_use_allowed

media_permissions:
  text:
    ingest_allowed
    store_allowed
    redistribute_allowed
    transform_allowed

  audio:
    download_allowed
    store_allowed
    clip_allowed
    transform_allowed
    transcript_allowed
    redistribute_allowed

  video:
    download_allowed
    store_allowed
    clip_allowed
    audio_extraction_allowed
    transcript_allowed
    redistribute_allowed

attribution:
  required
  format
  requirements

technical:
  robots_notes
  rate_limit_notes
  official_api_available
  official_dump_available

status

evidence:
  - url
  - description
  - checked_at

review_notes

Exact schema naming may be adapted to existing project architecture.

Do not create duplicate competing schema systems.

---

# Source Evidence

Every governance decision must be supported by evidence from current official sources whenever reasonably possible.

Store:

- evidence URL
- what the evidence proves
- review date

Do not rely solely on:

- random blogs
- forum comments
- AI knowledge
- outdated mirrors

Prefer official:

- license pages
- terms pages
- project documentation
- dataset documentation

---

# Media-specific Rights

This project will eventually build a listening corpus.

Therefore M1 MUST distinguish between:

1. content may be referenced
2. content may be downloaded
3. content may be stored internally
4. content may be transformed
5. audio may be extracted from video
6. transcripts may be generated
7. clips may be generated
8. original media may be redistributed
9. derived media may be redistributed

Example:

A video source might permit linking but prohibit downloading.

That source must NOT pass a future media download validator.

---

# Future Pipeline Compatibility

Design source governance so future pipeline stages can ask questions such as:

can_ingest_text(source_id)

can_download_audio(source_id)

can_download_video(source_id)

can_extract_audio(source_id)

can_generate_transcript(source_id)

can_create_clip(source_id)

can_redistribute_audio(source_id)

can_redistribute_video(source_id)

can_use_for_generated_exercises(source_id)

Exact API design may differ, but permissions must be machine-checkable.

---

# Automated Validation

Implement validators preventing unauthorized sources from entering future pipelines.

Tests must prove:

APPROVED + required permission
    -> allowed

REFERENCE_ONLY
    -> cannot enter ingestion

QUARANTINED
    -> cannot enter ingestion

REJECTED
    -> cannot enter ingestion

APPROVED text source without audio permission
    -> cannot enter audio pipeline

APPROVED video source without download permission
    -> cannot enter video download pipeline

APPROVED video source without audio extraction permission
    -> cannot enter audio extraction pipeline

---

# Provenance Requirements

Future downloaded records must support provenance including:

source_id
source_url
source_record_id
retrieved_at
license
license_url
content_type
content_hash

For media additionally support:

original_media_url
media_type
original_filename
duration when available
mime_type when available

M1 only defines/enforces governance structures.

Do not bulk ingest media yet.

---

# No Bulk Downloads

During M1:

DO NOT:

- crawl thousands of pages
- download audio corpora
- download video collections
- download large datasets
- generate transcripts
- run speech recognition

Small requests required for source/license verification are acceptable.

Bulk ingestion belongs to later milestones.

---

# Documentation

Update relevant documentation describing:

- source governance
- text source policy
- audio source policy
- video source policy
- source approval workflow
- evidence requirements
- license review workflow
- quarantine policy

If docs/MILESTONES.md currently lacks explicit media milestones,
update it so future work includes:

- text ingestion
- media ingestion
- transcript/timestamp processing
- listening difficulty analysis
- listening exercise generation

Do not implement those milestones yet.

---

# Tests

Add meaningful tests covering at minimum:

1. valid approved source
2. quarantined source rejection
3. rejected source rejection
4. reference-only ingestion rejection
5. text permission validation
6. audio download permission validation
7. video download permission validation
8. video audio-extraction permission validation
9. transcript permission validation
10. malformed source record rejection
11. missing evidence where required
12. invalid source status

Tests must test real policy behavior, not only schema parsing.

---

# Acceptance Criteria

M1 passes only if:

1. structured source registry exists
2. current candidate sources have been researched
3. official licensing evidence is recorded
4. text/audio/video permissions are represented separately
5. uncertain licensing is quarantined
6. source permission validation exists
7. unauthorized text ingestion is blocked
8. unauthorized audio download is blocked
9. unauthorized video download is blocked
10. unauthorized audio extraction is blocked
11. unauthorized transcript generation is blocked
12. tests cover permission failures
13. relevant documentation is updated
14. no bulk corpus download occurred
15. no curriculum generation occurred

---

# Completion

Run the complete test suite.

Inspect:

- git diff
- source registry
- schemas
- validators
- tests
- documentation

Report:

## Created
## Modified
## Sources Researched
## Licensing Decisions
## Media Permission Decisions
## Commands Run
## Tests
## Test Results
## Open Issues
## Acceptance Criteria

Explicitly state:

M1: PASS

or

M1: FAIL

Then STOP.

Do NOT begin M2.