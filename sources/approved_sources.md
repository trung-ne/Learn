# Approved-source ingestion and media profiles

This is a policy profile for later work, not an ingestion implementation. M1 did not download a source payload. Before any M2 action, load [registry.yaml](registry.yaml), run its schema validator, and call the corresponding fail-closed authorization predicate.

## Required gate sequence

1. Locate the exact `source_id` in the registry.
2. Require `status: APPROVED`.
3. Require the operation-specific permission; do not replace it with a generic source-level permission.
4. Apply the record's source-specific restrictions below.
5. Preserve required provenance and attribution before storing any payload.
6. Quarantine the record when its individual metadata conflicts with, omits, or narrows the source-level approval.

The available operation predicates are `can_ingest_text`, `can_download_audio`, `can_download_video`, `can_extract_audio`, `can_generate_transcript`, `can_generate_timestamps`, `can_create_clip`, `can_redistribute_media`, `can_redistribute_derived_media`, and `can_use_for_generated_exercises` in [schema_validation.py](../src/english_master/schema_validation.py).

## Text

### `src_tatoeba_text`

- **Permitted:** official API/download text records with complete, compatible record-level rights; normalized text; modified and redistributed derivatives when attribution/license obligations are retained.
- **Prohibited:** page crawling, importing audio based on the text decision, or use of a sentence that lacks complete rights metadata.
- **Attribution:** retain sentence ID, contributor, source URL, license URL, and modification indication.

### `src_wiktionary_en_text`

- **Permitted:** text from official English Wiktionary dumps, under CC BY-SA obligations.
- **Prohibited:** bulk webpage scraping, importing files/media attached to pages, or relicensing adaptations without ShareAlike compliance.
- **Attribution:** retain page/revision identity or equivalent author credit, page URL, license link, and change indication.

## Audio

### `src_tatoeba_audio_cc_by_4`

- **Permitted:** official audio records with affirmative CC BY 4.0 metadata; download, storage, transformations, clips, timestamps, transcripts, exercises, and redistribution under CC BY 4.0.
- **Prohibited:** selecting a recording based merely on a contributor name or attribution; treating the linked sentence as cleared without separately checking it.
- **Attribution:** audio ID, sentence ID, creator, source URL, attribution URL, license, and modification indication.

### `src_common_voice_scripted_speech`

- **Permitted:** controlled acquisition through an authorized Mozilla route; storage, processing, clips, timestamps, internally retained transcripts, and internally generated exercises.
- **Prohibited:** re-hosting/re-sharing original or derived material, identifying speakers, and treating the transcript text as distributable material without separately established text rights.
- **Audit fields:** release ID/version, language, terms version, official source URL, retrieval metadata, and content hash.

### `src_librivox_us_recordings`

- **Permitted:** U.S.-scoped recording use, transformations, clips, timestamps, exercises, and redistribution where the individual recording remains within the public-domain determination.
- **Prohibited:** assuming worldwide legal status; reusing underlying edition text/translation; creating or redistributing a transcript before item and jurisdiction review.
- **Audit fields:** LibriVox catalog/work/section IDs, recording source URL, applicable jurisdiction, edition/translation information, and content hash.

## Video

### `src_nasa_svs_plain_moon_video`

- **Permitted:** download, storage, factual/educational clips, timestamps, original redistribution, and derived exercise material for selected plain video assets under the recorded NASA conditions.
- **Prohibited:** audio extraction, transcript generation, music-bearing variants, third-party elements, NASA insignia use, implied endorsement, and promotional/merchandise uses.
- **Attribution:** `Source: NASA Scientific Visualization Studio, NASA SVS ID 5587.`

## Required provenance additions for future media records

The common provenance object remains mandatory. For audio/video records also retain:

- `original_media_url`
- `media_type`
- `original_filename` when available
- `duration_seconds` when available
- `mime_type` when available
- source-specific catalog/release/asset identifier
- exact license and attribution carried by the asset
- relevant terms or evidence URL/version

These additions are a governance requirement for later schemas; M1 intentionally does not ingest, normalize, transcribe, or validate payload records.
