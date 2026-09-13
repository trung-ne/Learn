# B1 Curriculum Blueprint

## Scope

The B1 blueprint is an original, outline-only planning artifact covering internal tiers `B1.1` and `B1.2`. It contains ten units, fifty deterministic lesson outlines, ten review lessons, and ten unit-test blueprints. The `.1` and `.2` labels are internal curriculum subdivisions, not official CEFR levels.

It retains titles, concise objectives, M15 target-node references, target use, internal lesson prerequisites, review placement, and unit-test placement. It contains no lesson prose, examples, exercises, answer keys, media, practice protocols, or authorization for later generation.

## M15 and A2 continuity

[`m16-b1-blueprint.json`](../curriculum/b1-blueprint/m16-b1-blueprint.json) hash-binds the complete M15 population at `curriculum/a1-full/v1/m15-population.json`. Direct A2.2 prerequisite nodes from M15 define the entry context; the B1 artifact does not read or validate an A2 blueprint and does not create an authority bridge.

The plan advances through life experience, personal change, supported opinions, media, relationships, community issues, coherent narratives, clarification, register, and tier consolidation. These labels are planning allocations, not claims of CEFR endorsement or completed instructional content.

## Local validation

```bash
python -m english_master.b1_curriculum_blueprint validate \
  curriculum/a1-full/v1/m15-population.json \
  curriculum/b1-blueprint/m16-b1-blueprint.json
```

Validation checks source identity/hash binding, node resolution, tier/dimension agreement, exact B1 target introduction/review coverage, unit/lesson/unit-test links, non-forward prerequisites, and cycles. It does not assess pedagogical quality, approval, release authority, provider behavior, or learner outcomes.

The blueprint remains `OUTLINE_ONLY` and project-authored planning material outside any content-generation authority.
