# M10 Revision / Regeneration Governance

> Historical contract only. This document governs retained M10 evidence and is not required by the active lightweight revision flow in [M10_REVISION.md](M10_REVISION.md).

M10 starts only from immutable M9 `NEEDS_REVISION` or `REJECT` evidence imported as non-promotable `m10_review_input` records. It must not edit predecessor artifacts, reinterpret old reviews as approval, or start M9.

1. Freeze one `m10_governance_run` before candidate one. The run binds the exact M9 finding batch, revision request, predecessor, policy, and maximum of three attempts.
2. Generate a new immutable candidate for every attempt. Attempt one binds the predecessor; later attempts bind the complete immediately preceding rejection and its repair constraints.
3. Capture the exact regeneration prompt/raw-response hashes and factual runtime metadata. Record `UNKNOWN` for unavailable facts. `TEST_ONLY` and `REPLAY_ONLY` captures cannot establish readiness.
4. Execute all static QA stages in order: `CAPTURE_INTEGRITY`, `SUCCESSOR_SCHEMA`, `AUTHORITY_BINDING`, `REPAIR_SCOPE`, `DEPENDENCY_REBUILD`, `CLOSED_INVENTORY`. Stop later stages as `NOT_RUN` after the first failure.
5. Publish an immutable rejection for every failed attempt. It must retain receipt hashes, blocking issues, constraints, retryability, and remaining budget. Never relax a failed rule to retry.
6. Non-retryable authority, authority-conflict, provenance, identity, path, request-binding, and capture-integrity failures must end as `ESCALATED`. An M5-bound field required by a finding must not be changed without separate M5 authority; retain a hash-bound escalation record instead of creating a partial candidate.
7. A passing full static attempt may end only as `READY_FOR_FRESH_M9`. It remains `UNREVIEWED`; no M10 artifact claims AI review, development approval, human review, release approval, provider authentication, runtime behavior, learner outcomes, or Internet-wide originality review.
8. A fresh M9 selection, machine pass, linguistic review, and pedagogical review are required for changed hashes. Earlier M9 captures are never reused.
9. Preserve every predecessor, attempt, rejection, and run. Record later archival relationships only in the append-only supersession index.
