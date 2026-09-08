# M12 — Real Audio / Video Corpus Ingestion

**Status:** Preparation framework only — real media acquisition and controlled-media publication are blocked until M11 has a complete, independently verified AI-only development export.

## Gate

M12 must not begin operationally until M11 has a complete export whose authorization, manifest, and verification receipt all validate as `DEVELOPMENT_APPROVED` under the active AI-only policy. This is a development gate, not human review, endorsement, release approval, or public-release authority. Creating this document records the design boundary only; it does not authorize acquisition, downloading, transformation, transcription, redistribution, or controlled-media publication.

Current M11 status does not satisfy that gate. No M12 code, source registration, media acquisition, or real media payload is authorized by this document.

## Mission

Build a reproducible, permission-aware pipeline for legitimately supplied audio/video records:

```text
registered source
    ↓
media permission gate
    ↓
audio/video payload
    ↓
checksum
    ↓
provenance
    ↓
metadata
    ↓
controlled media store
```

M12 handles media records and media files only. It does not silently grant curriculum approval or permission to redistribute, and it must not create human-review or release-approval claims.

## Source requirements

Every source must be registered before acquisition and have a verified license, terms of use, official URL, attribution requirements, and operation-specific permissions. Unknown licensing is `QUARANTINED` and cannot be acquired into the controlled store.

The system must not crawl or bypass authentication, paywalls, robots restrictions, captchas, geographic restrictions, rate limits used as access controls, or terms of service. A technically accessible URL is not evidence of permission.

### Explicitly prohibited

- YouTube URLs as ingestion inputs
- `yt-dlp` or equivalent download tooling
- URL scraping or undocumented extraction
- Downloading merely because a file can technically be fetched
- Treating a source-wide license as proof of record-level media rights
- Generating a transcript or derivative clip when that operation is not authorized
- Redistributing media without explicit redistribution permission

## Independent permission gate

Permissions are checked separately for every source and every record. A source is eligible only when the exact intended operation is explicitly authorized:

- `can_download_audio`
- `can_download_video`
- `can_store`
- `can_clip`
- `can_transform`
- `can_extract_audio`
- `can_generate_transcript`
- `can_redistribute`

Missing, ambiguous, expired, conflicting, or inherited-only permission fails closed. Audio permission does not imply video permission. Storage permission does not imply redistribution permission. Extraction, clipping, transformation, and transcription are separate operations and require separate evidence.

## Planned record flow

1. Load the independently pinned source registry and media authorization.
2. Verify source status, exact official route, record identifier, license, attribution, and operation permissions.
3. Accept a locally supplied official payload or an explicitly authorized acquisition result; no generic network crawler is part of the pipeline.
4. Compute SHA-256 over the exact received bytes before modification.
5. Retain immutable acquisition metadata: source, URL, record ID, retrieval time, retrieval method, byte count, MIME type, checksum, license, attribution, and authorization hash.
6. Validate media type, container metadata, duration, dimensions, codec information, and safe filename/path.
7. Store original media immutably under a controlled, gitignored media root.
8. Store every derivative separately with parent hash, operation name, tool/version, parameters, output hash, and permission evidence.
9. Quarantine malformed, mismatched, incomplete, unauthorized, duplicate, or drifted records without partial publication.
10. Produce a deterministic run report and independently verifiable inventory.

## Derivative boundaries

A derivative is not automatically permitted because the original is permitted. Before each operation, verify its corresponding permission and preserve lineage:

- clipping requires `can_clip`
- format or codec conversion requires `can_transform`
- audio extraction from video requires `can_extract_audio`
- transcript generation requires `can_generate_transcript`
- public/export distribution requires `can_redistribute`

If a transcript provider, model, or tool is used, retain factual provider/model/version information. Use `UNKNOWN` when unavailable; never fabricate it. Generated transcripts remain unreviewed until a later approved QA workflow.

## Storage and safety

Controlled media storage must be separate from `data/approved/`, curriculum exports, and generated lesson content until later governance explicitly authorizes those uses. Raw media and derivatives are not committed to Git by default. The pipeline must use safe descendant paths, immutable no-overwrite publication, atomic run directories, deterministic IDs, and complete closed inventories.

The controlled store must reject:

- path traversal and absolute paths
- symlinks/junctions escaping the store
- unexpected files in immutable runs
- payload checksum drift
- MIME/extension mismatch
- duplicate source identity with changed bytes
- output roots inside curriculum, exports, or approved content

## Planned contracts and commands

Future M12 implementation should add strict schemas for:

- media source authorization
- acquisition receipt
- media asset metadata
- derivative operation receipt
- quarantine record
- immutable run report
- independent verification report

Planned offline-first commands:

```bash
python -m english_master.media_ingestion prepare ...
python -m english_master.media_ingestion run ...
python -m english_master.media_ingestion verify ...
```

Acquisition itself remains outside the generic CLI unless a separately authorized official API/download adapter is implemented and permission-checked. No command may accept YouTube URLs.

## QA requirements

Each run must validate schema, source permission, checksum, provenance, MIME/container metadata, duration/size bounds, duplicate identity, path safety, derivative lineage, and output inventory. AI language-quality and transcript-accuracy review, copyright checks, and operation-specific media-rights verification remain separate recorded gates.

A machine-valid media run is not a public release and does not establish redistribution authority.

## Deferred until M11 development PASS

- source selection and registration
- exact production media authorization for a real source/record
- bounded real-pilot size and duration limits
- actual acquisition or import
- controlled-media publication of real payloads
- audio extraction, clipping, transformation, and transcript adapters
- tests using real external media

The offline fixture-only schema, path-safety, and verification framework may be implemented before this gate. It does not authorize real media acquisition or import.
