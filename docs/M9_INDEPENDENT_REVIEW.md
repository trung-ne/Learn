# M9 Independent Review Layer

## Two lanes

M9 keeps development evidence separate from human and release authority.

```text
DEVELOPMENT LANE
fresh static machine QA
+ independent AI linguistic review
+ independent AI pedagogical review
= DEVELOPMENT_APPROVED

OPTIONAL RELEASE LANE
verified DEVELOPMENT_APPROVED scope
+ genuine registry-bound human linguistic and pedagogical review
= HUMAN_REVIEWED
+ separate authorized release decision
= RELEASE_APPROVED
```

Development evidence is not blocked by missing human reviewers. It never changes the reviewed artifacts: lessons, exercise sets, and AI-practice prompt artifacts remain `UNREVIEWED`.

## Initial development sample

The initial pass selects three graph-ordered clusters from the current ten-lesson development authority: `A1-U01-L01`, `A2-U03-L01`, and `B1-U05-L01`. Each cluster includes one lesson, one exercise set, and the listening, speaking, pronunciation, and writing prompt for that lesson: 18 subjects from a frozen population of 60.

This is a representative sample spanning every M9 content type, not a conclusion about unselected artifacts. The batch must say that unselected content remains outside the review sample.

## Authority and checks

M9 independently reloads the M5 development snapshot, M6 ten-lesson batch, M7 ten-set batch, and the complete M8.2 pilot. It does not invent an M8.1 terminal run because none is bound by this M9 contract; it reruns applicable static M9 checks over the selected M7 exercise sets.

- Lesson reports recheck schema, authority/audit binding, CEFR/prerequisite scope, provenance, and lifecycle state.
- Exercise reports rerun the final-set semantic validator and inspect answer/CEFR/prerequisite/provenance constraints.
- Prompt reports rebuild the M8.2 request/artifact/audit contract and check its modality safety boundary.

M8.2 review is **static protocol review only**. It does not assert a live model, audio delivery, speech assessment, conversational execution, writing feedback behavior, or learner outcome.

## Commands

```bash
python -m english_master.independent_review prepare-development \
  --output-dir <new-prepared-directory>

python -m english_master.independent_review publish-development \
  --prepared-dir <prepared-directory> \
  --capture-dir <real-ai-capture-directory> \
  --output-dir <new-immutable-development-directory>

python -m english_master.independent_review verify-development \
  --batch-dir <immutable-development-directory>
```

`prepare-development` creates non-promotable scope and machine-report input. `publish-development` accepts only complete, separately captured linguistic and pedagogical AI evidence for all 18 subjects, verifies the staged closed inventory with freshly reloaded authority, and atomically publishes without overwrite.

## Capture chronology and failed evidence

For every role capture, the recorded order must be `selection.created_at ≤ machine_report.reviewed_at ≤ capture.observed_at ≤ ai_review.reviewed_at ≤ development_batch.created_at`. Equal values are allowed only when operations share the same clock tick. A later wrapper timestamp cannot rehabilitate a response observed before its frozen machine report. Known timestamps must never be replaced with `UNKNOWN` to bypass this rule.

An actionable `NEEDS_REVISION` or `REJECT` response is retained as non-promotable M9 failure evidence; it cannot be included in a `DEVELOPMENT_APPROVED` batch. It may be imported into M10 only after its exact selection, subject, machine report, prompt, raw response, capture metadata, and chronology are independently validated. Historical invalid captures remain preserved but cannot be rewrapped or reused as fresh evidence.

## Human and release boundary

The optional human lane requires real external reviewer-registry evidence, including verified identity, authorized role, qualifications, conflict disclosure, exact development-batch binding, chronology, and two distinct linguistic/pedagogical people. AI output can never substitute for that evidence.

A separate release decision is required after a valid human-reviewed batch. This representative sample is deliberately not a complete release candidate and cannot authorize a release. No human-review, release, or publisher artifact is supplied by the M9 development pass.
