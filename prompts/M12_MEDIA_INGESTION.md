# M12 — Local Media Pilot

## Active local-pilot workflow

`english_master.m12_local_pilot` validates a manifest for 10–30 explicitly listed local audio/video files. Each record provides its local relative path, observed SHA-256, source URL, license, attribution, and explicit storage, transcript, and timestamp permissions.

```bash
english-master-m12-local-pilot validate \
  --manifest <m12-local-pilot-manifest.json> \
  --input-root <local-media-directory>
```

The command is read-only: it fetches no URL, processes no media, downloads no model, and writes no payload. Local possession alone does not establish permission. The manifest must be valid before the separate M13 local-pilot API can use selected records.

Do not run a real pilot until licensed local files and a manifest with their exact hashes are supplied. Validation is not a redistribution, release, transcript-quality, or public-use claim.

## Historical controlled-media framework

The remaining sections describe the earlier controlled-media framework retained for existing immutable fixture records. Its historical M11 authority gate is not required by the active local-pilot validator.

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
- `can_generate_timestamps`
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
- timestamp generation requires `can_generate_timestamps`
- public/export distribution requires `can_redistribute`

M12 stores the original and derivative authority only. M13 owns ASR execution, transcript segmentation, timestamp validation, optional anonymous speaker segmentation, and its separate immutable derivative runs.

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

## Implemented fixture-only contracts and commands

The repository now provides both the legacy v1 fixture framework and a stricter v2 fixture framework. Neither framework authorizes real acquisition, access to a URL, rights determination, transformation, transcript creation, or redistribution.

The v2 lane adds hash/size/locator-bound evidence snapshots for every enabled operation, an explicit `can_generate_timestamps` permission, retained registry snapshots, direct authorization/payload comparison, and a local consistency assessor. The assessor returns only `CONSISTENT` or `UNVERIFIED` and always records `rights_granted: false`.

```bash
python -m english_master.media_ingestion prepare ...
python -m english_master.media_ingestion run ...
python -m english_master.media_ingestion verify ...

python -m english_master.media_ingestion assess-evidence-v2 ...
python -m english_master.media_ingestion prepare-v2 ...
python -m english_master.media_ingestion run-v2 ...
python -m english_master.media_ingestion verify-v2 ...
```

All arguments that name artifacts are local paths; URLs are rejected. Acquisition remains outside the generic CLI unless a separately authorized official adapter is added.

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
