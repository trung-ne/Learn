# Full A1 development curriculum

## Scope

`curriculum/a1-full/v1/` implements the complete M16 A1 outline as ten units and fifty original project-authored learner packets. The separate `a1_full` v2 pipeline does not alter or supersede the immutable ten-lesson `a1_pilot` v1 run.

The allocation binds the exact M15 population and M16 blueprint hashes. It adds granular targets, broad-target bindings, target prerequisites, lesson-level `INTRODUCE`/`PRACTISE`/`REVIEW`/`REQUIRE` usage, permitted exercise types, and the exact M16 lesson prerequisites. A closed content manifest hash-binds ten ordered unit files of five lessons each.

Every packet contains concise sections, three structured exercises, and listening, speaking, pronunciation, and writing protocols. Listening material is project-authored transcript text and requires no media. Pronunciation returns `NOT_ASSESSED` without learner audio. Writing waits for a draft and provides feedback without replacing it. All material remains `UNREVIEWED` and `PROJECT_AUTHORED`.

## Commands

From an installed checkout, set these paths or substitute their literal values:

```bash
BASE=curriculum/a1-full/v1
RUN=$BASE/runs/a1full_a45a6b574127a4328b518da37be8f15ac83696d3ae77b0af4ff1e637740edc87

english-master-a1-full verify "$RUN" \
  --population "$BASE/m15-population.json" \
  --blueprint "$BASE/m16-blueprint.json" \
  --allocation "$BASE/allocation.json" \
  --content-manifest "$BASE/content-manifest.json"

english-master-a1-full audit "$RUN" \
  --population "$BASE/m15-population.json" \
  --blueprint "$BASE/m16-blueprint.json" \
  --allocation "$BASE/allocation.json" \
  --content-manifest "$BASE/content-manifest.json" \
  --output /tmp/a1-full-audit.json

english-master-a1-full sample "$RUN" \
  --population "$BASE/m15-population.json" \
  --blueprint "$BASE/m16-blueprint.json" \
  --allocation "$BASE/allocation.json" \
  --content-manifest "$BASE/content-manifest.json" \
  --audit-report /tmp/a1-full-audit.json \
  --seed direct-use-1 --size 12 --output /tmp/a1-full-sample.json
```

`build` accepts the same four source arguments plus `--output-root` and an explicit `--built-at` timestamp. Publication is atomic and refuses overwrite.

## Lightweight audit

The `A1_FULL_LIGHTWEIGHT_V2` audit verifies all fifty packets, not just the sample. It checks closed inventories and hashes, source/reference bindings, tier and target scope, lesson and target prerequisite order, structured exercise contracts, no-media boundaries, forbidden claim fields, and normalized exact duplicates across sections, exercise prompts, exercise answers, and protocol instructions. Findings have stable issue codes, deterministic ordering, per-check counts, and a hash-bound `PASS` or `FAIL` consistency result.

This audit does not establish prose-level linguistic correctness, pedagogical quality, learner outcomes, human review, approval, release authority, provider behavior, live AI execution, or real-media validation.

## Deterministic direct-use sample

Sampling requires a verified run and a hash-valid passing audit report. The default size is 12; valid sizes are 10–15. Candidate rank is SHA-256 over the audit-report hash, required seed, policy version, and lesson ID. The algorithm selects the top-ranked lesson from each of ten units, then the globally top-ranked unselected lessons until the requested size is reached. It persists all fifty rankings and input hashes, so selection is reproducible and independent of input iteration order.

The sample is only a bounded set for direct use or inspection. It is not a review or approval gate.

## Practical-content successor

`curriculum/a1-full/v1/` is an immutable predecessor. A successor source may live under `curriculum/a1-full/v2/` while reusing the pinned v1 M15 population, M16 blueprint, and allocation as independent inputs. `english-master-a1-full seed-authoring` creates a retained 50-card authoring source, and `compile-authoring` validates it and atomically produces the successor unit files plus content manifest.

The authoring compiler rejects the specific recurring failures discovered by the initial practical check: legacy metadata exercises, a visible listening transcript, non-roleplay speaking instructions, generic pronunciation instructions, insufficient section structure, missing ordered coverage, and target-scope drift. These are limited local content lints; they do not establish linguistic quality, pedagogical approval, human review, or release authority.

A successor still requires a new immutable run, verification, audit, deterministic sample, and the requested direct practical inspection before any `A1 PRACTICAL CHECK: PASS` or `A1 DEVELOPMENT READY` statement.
