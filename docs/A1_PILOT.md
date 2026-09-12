# A1 Pilot

## Purpose

The A1 pilot is a bounded development artifact: ten ordered A1.1 lesson packets built from the first ten M16 outline lessons. Each packet includes original project-authored lesson content, exercises, and one private learner-practice protocol for each modality: listening, speaking, pronunciation, and writing.

It is intended for direct learner use and a small user-plus-AI development review. Every packet remains `UNREVIEWED`; the pilot does not assert human review, release approval, provider authentication, public-distribution authority, or real-media behavior.

## Build and verify

The committed inputs are `curriculum/a1-pilot/m15-population.json`, `curriculum/a1-pilot/m16-blueprint.json`, and `curriculum/a1-pilot/content-input.json`.

```bash
python -m english_master.a1_pilot.cli build \
  --population curriculum/a1-pilot/m15-population.json \
  --blueprint curriculum/a1-pilot/m16-blueprint.json \
  --content curriculum/a1-pilot/content-input.json \
  --output-root curriculum/a1-pilot/runs \
  --built-at <ISO-8601>

python -m english_master.a1_pilot.cli verify \
  curriculum/a1-pilot/runs/<pilot-id> \
  --population curriculum/a1-pilot/m15-population.json \
  --blueprint curriculum/a1-pilot/m16-blueprint.json
```

Build rejects non-M16 lesson IDs, incomplete ten-lesson scope, missing modalities, broken prerequisite ordering, answer/rubric gaps, duration outside 15–45 minutes, exact normalized duplicate learner-facing text, unsafe inventories, hash drift, or overwrite attempts.

## Review

Review all ten packets for explanation clarity, grammar correctness, vocabulary difficulty, exercise quality, prompt usability, duration, and repetition. Start with an explicitly incomplete template, complete it from actual observations, then summarize it:

```bash
python -m english_master.a1_pilot.cli review-template \
  curriculum/a1-pilot/runs/<pilot-id> \
  --population curriculum/a1-pilot/m15-population.json \
  --blueprint curriculum/a1-pilot/m16-blueprint.json \
  --output <review.json>
```

A completed review binds the exact pilot manifest and can include a `USER` reviewer plus an `AI` reviewer with factual provider/model values or `UNKNOWN`.

```bash
python -m english_master.a1_pilot.cli summarize-review \
  curriculum/a1-pilot/runs/<pilot-id> \
  --population curriculum/a1-pilot/m15-population.json \
  --blueprint curriculum/a1-pilot/m16-blueprint.json \
  --review <completed-review.json> \
  --output <new-review-summary.json>
```

A finding marked `SYSTEMIC` must name a generator rule to repair. The summary returns `FIX_GENERATOR` for systemic defects, `REPLACE_LOCAL_PACKETS` for isolated defects, or `NO_BLOCKING_FINDINGS`. Corrected packets are new immutable candidates; existing artifacts are never edited in place.

## Boundaries

The pilot does not replace historical M6–M8.2 records or use their approval artifacts as authority. It contains no external media payload, source content, live AI execution, or learner-result claim.
