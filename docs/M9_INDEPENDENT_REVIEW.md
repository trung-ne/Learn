# M9 Independent Review Layer

## Active full-population development lane

The active M9 contract is version 2.0 and covers the complete independently reconstructed current population:

- 10 M6 lessons
- 10 M7 exercise sets
- 40 M8.2 lesson-specific prompt artifacts
- 60 subjects total

Subjects are selected dynamically in M6 graph order and M8.2 modality order. The selection binds repository-relative artifact and machine-audit paths plus canonical hashes. The earlier version-1 representative selection and its immutable prepared evidence remain historical, non-promotable records; they are not rewritten or accepted as full-population authority.

For every selected subject, M9 requires a fresh passing machine report and two separately captured AI reviews: one linguistic and one pedagogical. A complete batch therefore contains 60 machine reports and 120 AI reviews. Execution IDs and raw-response hashes must be globally unique across all 120 reviews. The closed batch inventory contains the selection plus all reports and reviews.

A passing batch establishes only `DEVELOPMENT_APPROVED` evidence. Every generated artifact remains consistently `UNREVIEWED`. No human review, release approval, provider authentication, observed live-provider behavior, or Internet-wide originality search is claimed.

## Authority and checks

M9 independently reloads the M5 development snapshot, M6 ten-lesson batch, M7 ten-set batch, and complete M8.2 pilot. It reconstructs the whole inventory instead of trusting caller counts.

- Lesson reports recheck schema, authority/audit binding, CEFR/prerequisite scope, provenance, and lifecycle state.
- Exercise reports rerun final-set semantic checks and inspect answer, CEFR, prerequisite, and provenance constraints.
- Prompt reports rebuild the M8.2 request/artifact/audit contract and check modality safety boundaries.

M8.2 review is static protocol review only. It does not establish audio delivery, speech assessment, conversation execution, writing-feedback behavior, or learner outcome.

## Commands

```bash
python -m english_master.independent_review prepare-development \
  --output-dir <new-prepared-directory>

# Requires a configured local executable. The repository makes no provider call itself.
export ENGLISH_MASTER_M9_AI_RUNNER='<external-runner-command>'
# Optional: a local JSON configuration path passed hash-bound to the runner.
export ENGLISH_MASTER_M9_AI_RUNNER_CONFIG='<local-runner-config.json>'

python -m english_master.independent_review capture-development \
  --prepared-dir <prepared-directory> \
  --output-dir <new-real-ai-capture-directory>

python -m english_master.independent_review publish-development \
  --prepared-dir <prepared-directory> \
  --capture-dir <real-ai-capture-directory> \
  --output-dir <new-immutable-development-directory>

python -m english_master.independent_review verify-development \
  --batch-dir <immutable-development-directory>
```

`prepare-development` writes a non-promotable version-2 selection, 60 machine reports, and 120 exact role-specific prompt files. `capture-development` sends one canonical JSON request on standard input to the configured executable for each prompt and requires exactly one canonical JSON response plus a newline on standard output. It records only host-observed and runner-returned facts; unavailable provider/model facts remain `UNKNOWN`. No executable, malformed response, duplicate execution identity, nonzero exit, timeout, or partial capture inventory publishes output. `publish-development` imports factual captures only, validates their projections and chronology, verifies the staged closed inventory against freshly reloaded authority, and publishes atomically without overwrite.

## Capture chronology and failed evidence

For every role capture, the order is:

`selection.created_at ≤ machine_report.reviewed_at ≤ capture.observed_at ≤ ai_review.reviewed_at ≤ development_batch.created_at`.

An actionable `NEEDS_REVISION` or `REJECT` response is non-promotable. It may become hash-bound M10 input, but cannot appear in a `DEVELOPMENT_APPROVED` batch. Historical invalid or representative captures cannot be rewrapped as fresh full-population evidence.

## Current blocker

No version-2 full-population AI capture set or development batch has been manufactured. The existing immutable M10 escalation for `A1-U01-L01` also remains unresolved and must block M11 eligibility until separately authorized upstream repair, dependent rebuild, and wholly fresh M9 review close that lineage.
