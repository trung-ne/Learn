# Content/KG Quality System

## Scope

`english_master.content_kg_quality` is an offline deterministic consistency layer for the committed Full A1–C2 corpus and its shared M15 knowledge-graph population. It independently revalidates the six ordered Full runs, their common population hash, declared lesson/target links, prerequisite order, exercise-answer contracts, and selected corpus-wide consistency signals.

Every request and report is hash-bound, published without overwrite, and marked `UNREVIEWED`. This system never calls a provider or network service and does not alter its inputs.

## Commands

Create a request using the same five source paths per level as Cross-level QA, then run and verify it:

```bash
english-master-content-kg-quality create-request --output /tmp/content-kg-request.json \
  --a1-run-dir ... --a1-population ... --a1-blueprint ... --a1-allocation ... --a1-content-manifest ... \
  --a2-run-dir ... --a2-population ... --a2-blueprint ... --a2-allocation ... --a2-content-manifest ... \
  --b1-run-dir ... --b1-population ... --b1-blueprint ... --b1-allocation ... --b1-content-manifest ... \
  --b2-run-dir ... --b2-population ... --b2-blueprint ... --b2-allocation ... --b2-content-manifest ... \
  --c1-run-dir ... --c1-population ... --c1-blueprint ... --c1-allocation ... --c1-content-manifest ... \
  --c2-run-dir ... --c2-population ... --c2-blueprint ... --c2-allocation ... --c2-content-manifest ...
english-master-content-kg-quality run --request /tmp/content-kg-request.json --output /tmp/content-kg-report.json
english-master-content-kg-quality verify --request /tmp/content-kg-request.json --report /tmp/content-kg-report.json
```

`--web-lane vocabulary` or `--web-lane dictionary` records an explicit learner-lane scope and deterministically checks supplied lexical identity, declared band/tier consistency, and available example lists. Run the corresponding Node snapshot check separately to verify the browser projection byte-for-byte.

## Finding policy

- `BLOCKING` + `DEFECT` makes the report `FAIL`.
- `FLAG` + `CANDIDATE` produces `PASS_WITH_FLAGS` when no blocker exists.
- `INFO` with `EXPECTED` or `UNAVAILABLE` documents an honest boundary and does not affect the result.

Checks cover broken M15 links, grammar-only dependency cycles, lesson-prerequisite order, target-to-packet linkage, unallocated non-root planning nodes, declared tier consistency, bounded normalized duplicate learner-facing text candidates, media availability, and deterministic Full-packet answer contracts.

The current Full corpus deliberately uses transcript-only listening (`media_required: false`) and a no-audio pronunciation fallback. These are `EXPECTED`, not missing-audio defects. Legacy Full packets do not declare typed example requirements, so the report states `UNAVAILABLE` rather than inferring missing examples from prose. A future source can add an explicit typed requirement and be checked deterministically.

## Limits

This is repository-consistency evidence only. It does not determine whether prose or answers are linguistically correct, whether content is pedagogically effective, whether declared CEFR labels are suitable, or whether learners achieve outcomes. It does not establish approval, human or release authority, provider behavior, or distribution permission.
