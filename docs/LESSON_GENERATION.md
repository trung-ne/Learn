# M6 Lesson Generation

## Approval lanes and boundary

M6 has two separate authority lanes:

- **Development lane:** an immutable M5 development snapshot authorizes bounded M6 development only. It preserves `DRAFT` taxonomy and `OUTLINE_ONLY` M5 records. It may lead to `MACHINE_VALIDATED`, `AI_REVIEWED`, and `DEVELOPMENT_APPROVED` evidence.
- **Release lane:** the existing strict M5 human-review snapshot remains separate. It is required for human/release claims and cannot be satisfied by an AI record.

`DEVELOPMENT_APPROVED` is not `HUMAN_REVIEWED`, `RELEASE_APPROVED`, public publication, certification, or a statement about a real person's judgment. M6 produces lesson content sections only: no exercise bank, answer keys, assessments, media, UI, or M7 behavior.

## Development authority

`python -m english_master.curriculum_review.cli develop-publish` writes an immutable M5 development snapshot from an independently revalidated manifest, M5 bundle, source registry, canonical hashes, producing-tool version, timestamp, and optional Git commit. The snapshot is then reverified before every development generation/review/batch operation.

M6 uses only `REVIEWED_M2_M5_TAXONOMY_ONLY`. M3/M4 data has no CEFR authority here. The request is deterministically rebuilt from the exact M5 outline, graph, taxonomy scope, prerequisite closure, prior knowledge, and bounded configuration. Citation wording and external payloads are excluded; Vietnamese annotations are contextual guidance only.

## Generation provenance and machine validation

The backend returns only `content_sections`. Orchestration injects trusted identity, references, `exercises: []`, and initial `UNREVIEWED` metadata. The automated audit validates request/authorization reconstruction, schema, exact scope, prerequisite context, section bounds, no-M7 leakage, source-payload prohibition, and cryptographic hashes. A passing audit is only `MACHINE_VALIDATED` evidence; it is not linguistic, pedagogical, human, or release approval.

A session-captured response may be retained when no provider receipt exists, but its provider/model/run facts must be recorded exactly or as `UNKNOWN`. Test-only mocks and replay-only fixtures can validate code but cannot support development promotion. No Internet-wide plagiarism search is implied.

## Independent AI reviews

Each accepted development lesson needs two separate, hash-bound AI records:

- `LINGUISTIC_AI_REVIEWER`: CEFR, grammar/lexical accuracy, naturalness, prerequisite use, target-language compliance, and originality limits.
- `PEDAGOGICAL_AI_REVIEWER`: objectives, teachability, progression, clarity, cognitive load, Vietnamese-learner relevance, and coherence.

The reviewers receive the lesson, audit, and authoritative context—not generator reasoning or self-assessment. Each record retains exact artifact/prompt/response hashes, provenance mode, provider/model or `UNKNOWN`, run ID when known, timestamp, verdict, checklist, findings, and limitations. AI records never include human names, qualifications, trusted-human registry entries, or `HUMAN_REVIEWED` status.

## Development batch and M7 gate

A development batch requires exactly these graph-ordered lessons:

`A1-U01-L01`, `A1-U01-L02`, `A1-U02-L01`, `A1-U02-L02`, `A2-U03-L01`, `A2-U03-L02`, `A2-U04-L01`, `A2-U04-L02`, `B1-U05-L01`, and `B1-U05-L02`.

The immutable development batch reports hashes for every lesson, audit, and AI review, and binds the M5 development snapshot. It rejects missing roles, failed machine checks, blocking AI findings, drifted hashes, duplicate content, mixed snapshots, unsafe paths, test-only evidence, and M7 leakage. `python -m english_master.lesson_development` may publish only `DEVELOPMENT_APPROVED`. `python -m english_master.lesson_review m7-eligibility` is read-only and does not implement M7.

The completed development evidence is batch `m6devbatch_4883cca8dea320c18b26a99316041dec1101c7dd28e551e265654c367af93d26` in `data/generated/m6/development-batches/20260903-v6/`. It binds the verified M5 snapshot in `data/reviews/m5/development-20260903-062008/` and the byte-for-byte assembled candidate evidence in `data/generated/m6/development-candidates/20260903-v6-selected/`. This evidence does not make a human or release claim.

## Commands

```bash
python -m english_master.curriculum_review.cli develop-verify \
  curriculum/structure.json --source-registry sources/registry.yaml \
  --snapshot data/reviews/m5/development-20260903-062008

python -m english_master.lesson_generate --development \
  --lesson-id A1-U01-L01 --snapshot-dir data/reviews/m5/development-20260903-062008 \
  --captured-response <session-captured-response.json> \
  --output-dir <new-immutable-bundle-directory>

python -m english_master.lesson_review ai-review \
  --snapshot-dir data/reviews/m5/development-20260903-062008 \
  --review <review.json> --lesson <lesson.json> --audit <audit.json>

python -m english_master.lesson_review development-batch \
  --snapshot-dir data/reviews/m5/development-20260903-062008 \
  --bundle-root data/generated/m6/development-candidates/20260903-v6-selected \
  --report data/generated/m6/development-batches/20260903-v6/development-batch.json

python -m english_master.lesson_review m7-eligibility \
  --snapshot-dir data/reviews/m5/development-20260903-062008 \
  --bundle-root data/generated/m6/development-candidates/20260903-v6-selected \
  --report data/generated/m6/development-batches/20260903-v6/development-batch.json
```

The old human-review commands remain valid for their separate release-quality evidence lane.
