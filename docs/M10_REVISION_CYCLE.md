# M10 Revision Cycle

## Purpose

M10 turns independently retained M9 findings into auditable successor work. It never edits an immutable M6, M7, or M8.2 artifact in place and never converts a failed AI review into `AI_REVIEWED`, `DEVELOPMENT_APPROVED`, `HUMAN_REVIEWED`, or `RELEASE_APPROVED` evidence.

## Evidence intake

A completed M9 review that returns `NEEDS_REVISION` or `REJECT` is imported as an `m10_review_input` with:

- exact M9 selection, subject, artifact, and fresh machine-report bindings;
- the exact reconstructed M9 prompt and raw structured response;
- factual capture fields, using `UNKNOWN` rather than inventing an unavailable fact;
- a distinct M10 import time; and
- `promotion_status: NON_PROMOTABLE` and content status `UNREVIEWED`.

A closed, immutable `m10_finding_batch` retains the selection, machine reports, and all declared imported inputs. A batch is evidence of an issue, not evidence that a correction is approved.

## Revision planning

M10 generates one `m10_revision_request` per affected review subject. Each request retains predecessor artifact and audit hashes, source input hashes, verbatim findings, repair constraints, acceptance checks, and dependency closure.

- A lesson finding targets M6 and requires rebuilding its M7 set and the full closed M8.2 pilot.
- An exercise-set finding targets M7 and requires a new immutable exercise-set successor.
- An AI-practice-prompt finding targets M8.2 and requires a new complete 40-artifact pilot.

A repair must be a new successor. Existing artifact bytes and M9 evidence stay preserved.

## Immutable attempts and full static QA

An `m10_governance_run` freezes the exact finding batch, revision request, predecessor hashes, policy version, and an attempt budget of one to three attempts (three by default) before attempt one. Every `m10_candidate_attempt` is a separate immutable record. Attempt one binds the predecessor; every later attempt binds the immediately preceding complete `m10_rejection`. No attempt may overwrite or reinterpret an earlier revision.

Every attempt stores an `m10_regeneration_capture` with prompt and raw-response hashes, actual capture facts, parameters, and a factual provider/model/execution identifier (or `UNKNOWN`). `TEST_ONLY` and `REPLAY_ONLY` captures may support tests but can never establish readiness.

M10 runs all six static stages for every candidate in this exact order:

1. `CAPTURE_INTEGRITY`
2. `SUCCESSOR_SCHEMA`
3. `AUTHORITY_BINDING`
4. `REPAIR_SCOPE`
5. `DEPENDENCY_REBUILD`
6. `CLOSED_INVENTORY`

The first `FAIL` or operational `ERROR` makes all later stages `NOT_RUN`. An immutable rejection binds all receipt hashes, blocking issues, derived repair constraints, retryability, and remaining budget. Authority, authority-conflict, provenance, identity, path safety, request binding, and capture-integrity defects are non-retryable and escalate; no requirement may be weakened to consume a retry.

The only terminal states are `READY_FOR_FRESH_M9`, `RETRY_EXHAUSTED`, `ESCALATED`, and `OPERATIONAL_FAILURE`. `READY_FOR_FRESH_M9` means all static M10 work passed and downstream closure is complete; it is never approval and it never runs M9. A closed run can be independently checked offline with:

```bash
python -m english_master.revision_cycle verify-run <immutable-run-directory>
```

## Authority-conflict escalation

M10 cannot silently amend M5 authority. If a mandatory repair requires changing an M5-bound M6 field, no regeneration attempt is authorized. M10 instead publishes an immutable `m10_escalation` record that binds the finding input, request, frozen run, predecessor, authority record, exact conflicting repair constraint, and external resolution boundary.

The current `A1-U01-L01` finding includes a title replacement. M6 requires that title to equal the M5-derived lesson specification, so this run is terminally `ESCALATED` with no successor evidence and zero attempts. A separately authorized M5 amendment, followed by rebuilt downstream authority, is required before a new M10 run can address that title finding. The grammar and pronunciation recommendations are not treated as a partial successful successor while a mandatory finding remains unresolved.


M10 treats the existing M6, M7, and M8.2 validators as read-only predecessor authority and does not patch their immutable schemas, reports, batches, or pilot directories. M6 and M7 legacy development-batch validators each require their original closed ten-item inventory, while M8.2 requires its original 10×4 / 122-file pilot layout and v9 contract. Therefore a successor is represented through M10-owned lineage records and explicit closure evidence, not by adding revision fields to legacy objects or by claiming that a legacy batch now validates revised bytes.

- An M6 successor requires explicit M7 subject-set and complete M8.2 closed-pilot rebuild evidence.
- An M7 successor must bind the unchanged or successor M6 lesson authority; stale reuse is rejected by exact closure comparison.
- An M8.2 successor must prove a complete 40-artifact pilot; static protocol checks do not claim provider runtime behavior.

## Supersession and archive

Predecessors and rejected candidates remain in their original immutable locations. An append-only `m10_supersession_index` references terminal run-manifest hashes as `ACTIVE`, `SUPERSEDED`, or `CLOSED_AFTER_FRESH_M9`. A supersession identifies exactly one prior run and a reason; duplicate run IDs, forks, hash drift, and cycles are rejected. A later M9 result can only be retained as closure evidence, never converted into an M10 approval claim.


## M9 handoff

M10 may establish only readiness for a **fresh** M9 review after successor authority is fully rebuilt and verified. Previous M9 review captures cannot be reused for successor hashes. The later review must use a new M9 selection, fresh machine reports, and separate actual linguistic and pedagogical captures.

No M10 result establishes human review, release approval, provider authentication, runtime AI behavior, learner outcomes, or an Internet-wide originality search.
