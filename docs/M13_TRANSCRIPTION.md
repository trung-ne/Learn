# M13 Transcription

## Local operational-pilot tooling

A separate local pilot API is available in `english_master.m13_local_pilot`. It accepts a selected 10–20-record subset of a validated M12 local-pilot manifest and a caller-controlled local ASR backend. It records tool/model provenance, prohibits reported network use, checks transcript/timestamp permission, bounds ordered timestamps by declared duration, and uses anonymous `SPEAKER_NN` labels. It does not download models, invoke a provider, or include a bundled ASR model.

No real transcription is run until a licensed local M12 manifest, media files, and an explicit local ASR backend/model path are supplied. A pilot transcript remains `UNREVIEWED`; its existence is not an accuracy, release, or redistribution claim.

## Historical fixture framework

M13 is a fixture-only, offline derivative framework. It does not perform ASR, access a provider, download a model, or process parent media bytes.

## Creation gate

New M13 schema-version `2.0` runs require an independently verified, stored M12 v2 fixture run. M12 v1 parents remain supported only when read-only verification reconstructs an existing legacy M13 v1 bundle; they cannot authorize a new derivative.

A new authorization binds the exact M12 v2 authorization, acquisition receipt, evidence assessment, run report, verification, asset metadata, payload hash, source record, duration, and source-registry snapshot. The parent M12 record must explicitly set both `can_generate_transcript` and `can_generate_timestamps` to true.

M13 additionally requires two ordered, record-level permission-evidence bindings:

1. `transcript_generation` bound to the parent's `can_generate_transcript` evidence;
2. `timestamp_generation` bound to the parent's `can_generate_timestamps` evidence.

Each binding retains the parent evidence-entry hash, snapshot path/hash/size, locator, located-value hash, matching M12 assessment-result hash, and an M13-retained snapshot path. The verifier reopens the retained snapshots, resolves their locators, and fails on missing, reordered, stale, unassessed, or mismatched evidence. Source-level registry permission alone is insufficient.

## No-media fixture processing plan

Every v2 run contains `processing-plan.json`. Its only input is the caller-authored inline segment array. The plan and request explicitly prohibit:

- reading or decoding the parent media payload;
- audio extraction;
- media transformation or resampling;
- external-process execution; and
- network access.

The parent payload hash is lineage evidence, not a fixture processing input. The implementation verifies the immutable M12 parent bundle, but the transcript construction step copies only inline fixture text and timestamps.

## Factual provenance

The processing plan and transcript artifact record the fixed local tool as `english_master.transcription.fixture_copy` version `2.0`, implementation `PROJECT_PYTHON`. They truthfully record that no model was invoked: provider, model name/version, and model-file hash are null. Parameters are exact and hash-bound: inline segment source, a single-space text joiner, millisecond timestamps, no text normalization, and sequential anonymous speaker labels.

No provider authentication, model quality, transcript accuracy, live ASR behavior, real-media processing, learner outcome, redistribution right, human review, or release approval is claimed. Transcript content remains `UNREVIEWED`; a passing fixture run is only `MACHINE_VALIDATED` development evidence.

## Artifact and storage rules

Segments are contiguous by sequence, nonempty, nonoverlapping, duration-bounded, and copied exactly. Speaker labels are anonymous, sequential within one artifact (`SPEAKER_01`, `SPEAKER_02`, and so on), and cannot encode identity or support cross-record linkage.

Publication is atomic and no-overwrite. The closed inventory binds every retained M12 authority record, the source-registry snapshot, both operation-evidence snapshots, authorization, request, processing plan, transcript artifact, and five ordered stage receipts. Verification rejects missing, additional, duplicate-path, mis-rolified, hash-drifted, or unsafe inventory entries and deterministically reconstructs identities, bindings, plan, artifact, receipts, and verification evidence.

The CLI accepts local paths only:

```bash
python -m english_master.transcription run \
  --authorization path/to/transcription-authorization-v2.json \
  --request path/to/transcription-request-v2.json \
  --media-run-directory path/to/verified-m12-v2-run \
  --registry sources/registry.yaml \
  --data-root path/to/local-data \
  --started-at 2026-09-10T10:00:00Z \
  --completed-at 2026-09-10T10:01:00Z

python -m english_master.transcription verify \
  --run-directory path/to/transcription-run
```

A failure publishes no partial accepted derivative.
