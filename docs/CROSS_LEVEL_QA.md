# Cross-level A1-C2 QA

## Scope

`english_master.cross_level_qa` is an offline, algorithm-first consistency check across the six immutable Full A1, A2, B1, B2, C1, and C2 development runs. It first reuses each level's `verify_full_*` function, requires the exact A1 → A2 → B1 → B2 → C1 → C2 order, requires fifty verified packets per level, and rejects a request unless all six runs bind the same M15 population SHA-256.

The request, report, and flagged-region sample are strict schema-validated JSON records. Requests list only local source paths. Reports bind the request hash, all six run-manifest hashes, and the common M15 hash. All published paths refuse overwrite. All records and all source content remain `UNREVIEWED`.

The committed first run is under `curriculum/cross-level-qa/v1/`: `request.json`, `report.json`, and `flagged-region-sample.json`. It verifies the retained Full A1 v1 run and the six committed full-corpus sources; it does not modify those historical artifacts.

## Deterministic checks

The report flattens the verified runs into a fixed 300-packet sequence and checks:

- declared granular target linkage to allocation and M15 dimensions, including grammar and vocabulary-sense dimensions when declared;
- global lesson-prerequisite order and non-forward M15 prerequisite order;
- normalized exact learner-facing text duplicates and bounded, deterministic 3-word-shingle near-duplicate candidates;
- repeated cross-level topic candidates;
- exact four-modality presence, target linkage, transcript-only listening, pronunciation no-audio fallback, and draft-first writing boundaries; and
- structural difficulty-jump diagnostics based on per-level medians for section text, exercises, and target counts.

`BLOCKING` findings make the report `FAIL`. Duplicate, topic, and structural-jump findings are `FLAG` candidates, not automatic content defects. Near-duplicate reporting is deliberately capped at 250 findings in deterministic order so template-heavy populations remain bounded.

## CLI

Create a request with all six source bundles. `create-request --help` lists the five required path arguments for each level; the committed `curriculum/cross-level-qa/v1/request.json` is a complete local example. Then run the report and create a deterministic flagged-region manifest:

```bash
english-master-cross-level-qa run --request curriculum/cross-level-qa/v1/request.json --output /tmp/cross-report.json
english-master-cross-level-qa sample --report /tmp/cross-report.json --seed cross-level-v1 --size 20 --output /tmp/cross-sample.json
```

The sample ranks existing report findings by SHA-256. Its `execution_mode` is `NO_API_DETERMINISTIC_FLAGGED_REGION_MANIFEST`; it does not call an AI API, make a provider claim, assess content, or establish review, approval, release authority, CEFR endorsement, or learner outcomes.

## Boundaries

This is a repository-consistency result only. It does not replace the existing level validators, establish prose-level correctness or pedagogical quality, process media, make live-AI claims, or authorize generation or distribution.
