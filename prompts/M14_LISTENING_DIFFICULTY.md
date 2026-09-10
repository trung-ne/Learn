# M14 — Listening Difficulty Analyzer

**Status:** hardened fixture-only implementation. Operational analysis remains blocked pending operational predecessor authority.

## Goal and hard boundary

Produce auditable multidimensional listening evidence without treating vocabulary as overall listening difficulty. M14 is offline and makes no provider, model, network, or media call.

Publication accepts only a local M13 run that passes M13's independent verifier and whose artifact is English and `fixture_only: true`. Arbitrary schema-valid JSON may be analyzed through the internal Python `analyze()` API, but it cannot be published. The CLI has no arbitrary-input publication option.

## Required dimensions

Every profile addresses lexical difficulty, grammar difficulty, speech rate, utterance length, reductions, connected speech, accent/variety complexity, speaker count, speaker overlap, noise, and discourse complexity.

Every feature retains:

- score or `NOT_ASSESSED`;
- confidence;
- structured source record, exact SHA-256, locator, and evidence detail;
- method and method version;
- limitations;
- explicit composite inclusion, weight, weighted score, and rationale.

## Acoustic fixture sidecar

Direct acoustic observations are prohibited in the transcript projection. Before operational media processing is authorized, acoustic evidence may enter only through a separate strict `listening-acoustic-fixture-sidecar`.

The sidecar must declare `SYNTHETIC_ACOUSTIC_FIXTURE`; bind the exact projected transcript, M13 manifest and verification, transcript artifact, and parent-media lineage; retain its own canonical payload hash and identity; and declare no network, model, or media access. Each annotation identifies a fixture record and locator, a versioned method, bounded score, low/medium confidence, and limitations. It is synthetic development evidence, not an observed media measurement.

## Fail-closed composite

A composite requires lexical, grammar, speech-rate, utterance-length, and discourse evidence plus at least one assessed nonlexical audio or interaction feature. Otherwise it is `INSUFFICIENT_EVIDENCE`, has no score or confidence, and no feature contributes.

For a qualifying fixture profile, the five core features share 80% equally. The assessed qualifying nonlexical features share 20% equally. The ledger reconstructs the score from explicit contributions. Composite confidence remains `LOW`. No output claims official CEFR alignment, learner outcomes, real-media behavior, or operational completion.

## Lifecycle

All generated M14 records remain `UNREVIEWED`, with `human_reviewed` and `release_approved` false. Internal `analyze()` results are explicitly `INTERNAL_ANALYSIS_ONLY`. Only a profile produced while publishing from a reverified M13 fixture run may state `VERIFIED_M13_FIXTURE_RUN` and `MACHINE_VALIDATED`. Passing evidence remains development-only.

## Immutable bundle

Publication re-verifies M13 before creating an atomic no-overwrite directory. The closed inventory contains the M13 projection, optional acoustic sidecar, profile, and an immutable verification receipt. The manifest hash-inventories the receipt itself. Read-only verification independently reconstructs hashes, identities, sidecar lineage, feature semantics, contributions, profile, manifest bindings, and receipt. Any missing, extra, linked, drifted, or malformed file fails closed.
