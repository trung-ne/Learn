# M11 Export & Packaging

## Status and authority boundary

The M11 framework is implemented, but this repository currently has no eligible release candidate and no export has been published. `data/approved/` is empty; the M9 evidence is representative and cannot authorize release; the M10 run is escalated; and all current generated lessons, exercises, and AI-practice protocols remain `UNREVIEWED` development material.

The production builder is authority-first and fail-closed. It independently reloads the authorization, complete M9 development batch, genuine human-review batch, separate release decision, source registry, and every declared content record. It checks schemas, canonical identities, exact hashes, path containment, content identity, lifecycle status, redistribution permissions, and release-chain bindings before creating a staging directory. The existing M9 rule that a representative sample cannot authorize release is retained.

An authorization must request all six profiles and use `SEPARATE_INSTRUCTOR_EDITION`:

- canonical JSON;
- RFC-4180 CSV;
- static mobile HTML/JSON/CSS;
- static web HTML/JSON/CSS;
- print HTML; and
- IMS Common Cartridge 1.3.

Development approval, AI review, machine validation, a schema-shaped record, or a caller-set boolean is not human or release approval.

## Commands

All commands are offline and require explicit paths. Timestamps never default to the wall clock.

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

The installed command is `english-master-export`. Ineligibility exits with status 2 and the builder creates no export directory. Publication uses an atomic, no-overwrite directory rename.

## Output layout

```text
data/exports/m11export_<sha256>/
  authorization.json
  manifest.json
  verification.json
  json/catalog.json
  json/artifacts/<type>/<id>.json
  csv/lessons.csv
  csv/sections.csv
  csv/exercises.csv
  csv/references.csv
  csv/provenance.csv
  mobile/{index.html,catalog.json,styles.css,lessons/...}
  web/{index.html,catalog.json,styles.css,lessons/...}
  print/learner.html
  print/instructor-answer-key.html
  lms/english-master.imscc
```

The manifest inventories authorization and payload files by POSIX-relative path, byte count, and SHA-256. The manifest and verification receipt are control records whose identities bind their contents; they are the two necessary non-self-hashed files. Read-only verification permits no other unreferenced file.

## Format guarantees and limits

All renderers consume one normalized deterministic model. JSON is the lossless catalog and per-artifact representation. CSV is a tabular projection; irregular exercise data remains canonical JSON in `payload_json`. HTML/XML text is escaped, files use normalized encodings/newlines, and ZIP members have fixed ordering, timestamps, permissions, and compression settings.

The learner print edition omits answer material. The separately labelled instructor edition includes it. File separation is not access control, and PDF conversion is outside this standard-library profile.

The `.imscc` archive contains only ungraded XHTML `webcontent` resources and a closed `imsmanifest.xml`. It does not implement or claim QTI, SCORM, gradebook support, target-LMS certification, or IMS certification.

Mobile and web packages are static offline projections. They contain no application runtime, authentication, telemetry, media downloader, live AI provider, or runtime-behavior assurance. AI-practice records describe static protocols only.

## Exclusions

Raw, normalized, deduplicated, and quarantined ingestion paths are rejected. Private model captures, secrets, credentials, and reviewer identity evidence are not exported. The Post-M3 Tatoeba real-record pilot is categorically excluded by path and provenance and cannot become curriculum or release content through M11.
