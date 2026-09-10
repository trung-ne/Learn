# M13 — ASR, Transcript, and Timestamp

**Status:** Hardened fixture-only preparation framework. No real ASR, external call, model download, or parent-media transformation is authorized.

## Boundary

The implemented lane accepts caller-authored inline segments and publishes immutable transcript fixture evidence. It does not read parent media as a transcription input and cannot claim ASR accuracy, provider behavior, real-media processing, redistribution, curriculum use, human review, or release approval.

New derivatives require a verified, stored M12 v2 parent. M12 v1 lineage is verification-only for existing legacy M13 v1 bundles and must never authorize a new run.

## Authority contract

Before publication, independently verify and bind:

- the complete M12 v2 run, verification, authorization, acquisition receipt, evidence assessment, asset, registry snapshot, source identity, payload hash, and duration;
- source-registry transcript and timestamp permission for the exact media kind;
- record authorization values `can_generate_transcript: true` and `can_generate_timestamps: true`; and
- exactly two ordered M13 evidence projections, transcript then timestamp, from the corresponding M12 v2 record-level evidence and `CONSISTENT` assessment results.

For each operation retain and revalidate the parent evidence-entry hash, snapshot path/hash/size, locator, located-value hash, assessment-result hash, and copied M13 snapshot. Missing, ambiguous, source-only, reordered, stale, malformed, or conflicting evidence fails closed.

## Fixture processing contract

Create a separately hash-bound processing plan with mode `INLINE_FIXTURE_COPY_NO_MEDIA_ACCESS`. It must state all of these as false:

- parent-media read;
- media decode;
- audio extraction;
- media transformation;
- external-process invocation; and
- network access.

The only processing input is the inline fixture segment array. Use exact-copy text semantics, one ASCII space when joining segment text, millisecond timestamps, and anonymous sequential speaker labels.

Record factual provenance only:

- tool: `english_master.transcription.fixture_copy`;
- tool version: `2.0`;
- implementation: `PROJECT_PYTHON`;
- model invoked: false;
- provider/model/version/model-file hash: null.

Do not populate model or provider facts when no model ran. Do not imply that the parent payload was decoded, transformed, or transcribed.

## Transcript rules

Segments must be nonempty, contiguous by one-based sequence, nonoverlapping, and within the parent duration. Text is copied without normalization. Speaker labels begin with `SPEAKER_01` and advance by first appearance within the artifact only. Names, biometric properties, persistent voice profiles, and cross-record identity/linkage are prohibited.

The transcript artifact binds the authorization, request, processing plan, M12 lineage, exact tool/model/parameter facts, segment inventory, complete joined text, and hashes. It remains `UNREVIEWED`; deterministic success is at most `MACHINE_VALIDATED`.

## Immutable publication

Publish atomically with no overwrite. The closed inventory must contain exactly the declared files and roles for:

- authorization, request, processing plan, and transcript artifact;
- retained M12 authorization, receipt, assessment, report, verification, and asset;
- retained source registry and both permission-evidence snapshots; and
- five ordered authorization, request, processing-plan, segment, and artifact receipts.

Reject extra files, missing files, duplicate paths, role drift, unsafe paths, content/hash drift, receipt drift, plan drift, provenance drift, and any inability to independently reconstruct the stored verification. A failure publishes no partial accepted derivative.

Future real ASR requires a separate explicit implementation request and all predecessor gates; this fixture contract does not authorize it.
