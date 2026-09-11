# M9 Lightweight QA

## Active workflow

M9 is the active free development check. It runs `python -m pytest` and a direct review of five representative lesson packets:

- `A1-U01-L01`
- `A1-U02-L02`
- `A2-U03-L01`
- `A2-U04-L02`
- `B1-U05-L02`

The test suite covers schema, CEFR/reference constraints, prerequisites, deterministic answer/ambiguity rules, and duplicate checks. The sample review looks only for clear defects in the lesson, exercise set, and four AI-practice prompts.

M9 does not require 120 AI reviews, a full-population live review, a paid runner, human review, external approval, or release authority.

## Decision

Record `M9 DEVELOPMENT: PASS` when pytest passes, all five packets are inspected, and no blocking sampled defect remains. Otherwise record `M9 DEVELOPMENT: FAIL` and the factual issue.

A pass permits the next explicitly requested development step. It does not change generated artifacts from `UNREVIEWED` or make human, release, provider, public-distribution, or runtime-behavior claims.

## Historical records

Existing M9 v2 and 2026-09-11 reports remain immutable historical evidence. They can be verified with their original tooling but are not additional requirements for the active workflow.
