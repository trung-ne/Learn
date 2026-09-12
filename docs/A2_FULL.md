# Full A2 Development Corpus

## Scope

Full A2 is a bounded, original-authored development corpus generated from the M16 A2 outline: ten units and fifty lessons spanning internal tiers A2.1 and A2.2. The `.1` and `.2` labels are internal subdivisions, not official CEFR levels.

## Validation

`english_master.a2_full` provides offline `build`, `verify`, `audit`, and `sample` commands. The immutable run binds the M15 population, M16 blueprint, allocation, and ten content-unit files by SHA-256. Verification reconstructs every packet. The audit checks schema/reference integrity, prerequisite order, exercise answer contracts, duplicate projections, media boundaries, and prohibited claims. Sampling accepts 10–15 lessons and stratifies across all ten units.

The checked development run and 12-lesson sample passed these deterministic checks and a bounded direct inspection. All generated content remains `UNREVIEWED`; no live AI, external media, human review, release approval, CEFR endorsement, or public-distribution claim is made.

## Artifacts

- `curriculum/a2-full/v1/allocation.json`
- `curriculum/a2-full/v1/content-manifest.json`
- `curriculum/a2-full/v1/units/`
- `curriculum/a2-full/v1/reports/practical-check.md`
- `curriculum/a2-full/v1/samples/sample-12-v4.json`
