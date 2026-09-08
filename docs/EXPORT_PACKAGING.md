# M11 Export & Packaging

## Status and AI-only authority boundary

M11 is an AI-only development packaging gate. An active authorization hash-binds a `DEVELOPMENT_APPROVED` M9 development batch, the source registry, and every declared content record. Human-review batches and release decisions are not active inputs, and M11 does not create or report human review, endorsement, or release approval.

The builder independently reloads and validates the authorization, M9 evidence, registry, and content. It checks canonical identities, exact hashes, path containment, content identity, chronology, source redistribution permission, prohibited lineage, and lifecycle status before staging output. Every applicable lifecycle value on an exported generated record must remain exactly `UNREVIEWED`; absent, mixed, or differently labeled values fail closed. AI development approval is documented as development evidence and never silently changes content lifecycle state.

The current repository has no completed M9 development batch, `data/approved/` has no eligible inventory, current generated artifacts remain `UNREVIEWED`, and M10 is escalated. It therefore cannot currently build an M11 package. Existing immutable historical records are not changed.

An authorization requests all six profiles and `SEPARATE_INSTRUCTOR_EDITION`:

- canonical JSON;
- RFC-4180 CSV;
- static mobile HTML/JSON/CSS;
- static web HTML/JSON/CSS;
- print HTML; and
- IMS Common Cartridge 1.3.

## Commands

All commands are offline and require explicit paths and timestamps.

```bash
python -m english_master.export_packaging inspect-authority \
  --authorization path/to/m11-authorization.json \
  --repository-root .

python -m english_master.export_packaging build \
  --authorization path/to/m11-authorization.json \
  --repository-root . \
  --output-root data/exports \
  --exported-at 2026-09-07T12:00:00Z

python -m english_master.export_packaging verify \
  data/exports/m11export_<sha256> \
  --repository-root .
```

The installed command is `english-master-export`. Ineligibility exits with status 2 and creates no export directory. Publication uses an atomic, no-overwrite directory rename.

## Output layout

```text
data/exports/m11export_<sha256>/
  authorization.json
  manifest.json
  verification.json
  json/catalog.json
  json/artifacts/<type>/<id>.json
  csv/{lessons,sections,exercises,references,provenance}.csv
  mobile/{index.html,catalog.json,styles.css,lessons/...}
  web/{index.html,catalog.json,styles.css,lessons/...}
  print/learner.html
  print/instructor-answer-key.html
  lms/english-master.imscc
```

The manifest inventories authorization and payload files by POSIX-relative path, byte count, and SHA-256. Read-only verification reconstructs the authority and normalized model and rejects missing, changed, or unexpected files. Manifest and verification identities bind their contents. Both report only `DEVELOPMENT_APPROVED`.

## Format guarantees and limits

All renderers consume one deterministic model. JSON is lossless; CSV is a tabular projection with irregular exercise data retained as canonical JSON in `payload_json`. HTML/XML text is escaped, and ZIP ordering, timestamps, permissions, and compression are fixed.

Learner print output omits answers; the separate instructor edition includes them. File separation is not access control. The `.imscc` archive contains ungraded XHTML `webcontent`, not QTI, SCORM, gradebook integration, target-LMS certification, or IMS certification. Mobile and web exports contain no runtime, authentication, telemetry, media downloader, live AI provider, or runtime-behavior assurance.

## Exclusions

Raw, normalized, deduplicated, and quarantined ingestion paths are rejected. Private captures, secrets, credentials, and identity evidence are not exported. The Post-M3 Tatoeba pilot is excluded by path and provenance. No media is downloaded by M11.
