# M9 Lightweight QA

## Objective

Run practical, free development QA for English Master. M9 checks for clear defects before continuing work; it is not an approval or release process.

Do not require 120 AI reviews, full-population live review, paid runners, human reviewers, external approval services, or release authority.

## Required checks

Run:

```bash
python -m pytest
```

The test suite supplies the deterministic checks for:

- schema validity;
- CEFR/reference constraints;
- prerequisites;
- deterministic answer and ambiguity rules; and
- exact/near duplicate detection.

## Representative sample review

Inspect these five lesson packets directly:

1. `A1-U01-L01`
2. `A1-U02-L02`
3. `A2-U03-L01`
4. `A2-U04-L02`
5. `B1-U05-L02`

For each packet, inspect the lesson, exercise set, and four AI-practice prompts for obvious English, CEFR, teaching-clarity, answer, duplication, reference, prerequisite, provenance, and static-protocol defects.

## Decision

Record `M9 DEVELOPMENT: PASS` when pytest passes, all five packets are inspected, and no blocking sampled defect remains. Otherwise record `M9 DEVELOPMENT: FAIL` with the factual defect.

A pass allows the next explicitly requested development step. It does not establish human review, release approval, provider behavior, public distribution, or a content lifecycle change. Historical M9 records remain unchanged.
