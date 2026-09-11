# M14 Listening Difficulty Analyzer

## Local operational-pilot metrics

`english_master.listening_difficulty.local_metrics` provides a small offline metric surface for local-pilot transcript artifacts: speech rate, vocabulary proxies, grammar-complexity proxies, length measures, and anonymous speaker-label count. It produces no CEFR level, composite difficulty score, diarization-quality claim, or model judgment.

The existing fixture publication framework below remains unchanged for historical verification.

## Historical fixture framework

M14 is hardened as a deterministic, offline, fixture-only analysis stage. A publishable M14 run must be built directly from an independently verified M13 fixture run. A caller-supplied JSON projection can be passed to the Python `analyze()` API for non-publishing internal analysis, but it cannot authorize `run()` or the CLI publication command.

## Publication authority

`run` accepts `--transcription-run-directory`, not an arbitrary transcript JSON file. It invokes the M13 read-only verifier, reloads the M13 manifest, verification receipt, and transcript artifact, checks their hashes and lineage, and accepts only an English `fixture_only: true` artifact. No M13 or controlled-media file is modified.

```bash
python -m english_master.listening_difficulty run \
  --transcription-run-directory <verified-m13-run> \
  --output-root <m14-output-root>

python -m english_master.listening_difficulty verify \
  --run-directory <m14-run-directory>
```

`project-m13` remains available to prepare an internal analysis projection or to author a matching acoustic sidecar. Its output is explicitly non-publishable by itself.

## Acoustic boundary

The M13 projection cannot contain acoustic observations. Reductions, connected speech, accent/variety complexity, and noise remain `NOT_ASSESSED` unless a separate `listening-acoustic-fixture-sidecar` is supplied. The sidecar:

- is synthetic fixture evidence, never direct acoustic observation;
- is hash- and identity-bound to the exact M14 projection, M13 run, M13 manifest and verification receipt, transcript artifact, and parent media lineage;
- records a bounded feature score, `LOW` or `MEDIUM` confidence, structured fixture evidence, method name/version/parameters, and limitations;
- declares that no media, model, network, or provider was accessed.

A drifted or duplicated sidecar feature fails closed. Use `--acoustic-sidecar <path>` only with the exact M13 run from which it was bound.

## Feature ledger and composite

Every profile has exactly eleven ordered entries: lexical, grammar, speech rate, utterance length, reductions, connected speech, accent, speaker count, speaker overlap, noise, and discourse complexity. Each entry records:

- `ASSESSED` or `NOT_ASSESSED` and a bounded score or `null`;
- explicit confidence;
- structured evidence provenance with source record/hash and locator;
- method and method version;
- limitations;
- whether it contributes, its weight, and weighted score.

The composite is withheld as `INSUFFICIENT_EVIDENCE` unless all five core dimensions and at least one nonlexical audio or interaction dimension are assessed. A scored fixture composite uses fixed weights: 80% divided equally across the five core features and 20% divided across the qualifying nonlexical features. Fixture composites have `LOW` confidence and are not CEFR judgments.

## Lifecycle and immutable verification

Profiles always state `content_status: UNREVIEWED`, `human_reviewed: false`, and `release_approved: false`. Non-publishing `analyze()` results explicitly state `publication_status: INTERNAL_ANALYSIS_ONLY` and `validation_tier: INTERNAL_ANALYSIS_ONLY`. Only a profile created inside a verified-M13 publication run states `publication_status: VERIFIED_M13_FIXTURE_RUN` and `validation_tier: MACHINE_VALIDATED`. This is development evidence only.

A published run is deterministic, atomic, no-overwrite, and closed. Its manifest inventories:

- `input.json` — verified M13 fixture projection;
- optional `acoustic-sidecar.json`;
- `profile.json`;
- `verification.json` — immutable deterministic verification receipt.

The receipt is itself hash-bound in the manifest inventory. Read-only verification checks the closed file set, hashes, identities, sidecar lineage, feature and contribution semantics, profile reconstruction, manifest bindings, and receipt reconstruction. No external calls occur.
