# B1 Blueprint Authoring Contract

Build an outline-only B1 curriculum blueprint from the existing M15 knowledge-graph population.

## Inputs and scope

- Use `curriculum/a1-full/v1/m15-population.json` as the exact M15 input.
- Cover the internal curriculum tiers `B1.1` and `B1.2`; these are internal subdivisions, not official CEFR levels.
- Preserve the M15 population and all A1/A2 artifacts unchanged.
- Use deterministic IDs beginning with `m16b1-v1-b1-`.
- Produce ten units and fifty lesson outlines: five units per tier and five lessons per unit.
- Mark each fifth lesson as a review lesson and place one unit test after it.

## Required outline fields

Each lesson outline must retain only:

- deterministic ID, unit, tier, and sequence;
- concise title and objectives;
- resolved M15 target-node IDs with their dimensions and `INTRODUCE`, `PRACTISE`, or `REVIEW` use;
- internal lesson prerequisites.

Units identify their lessons, review lesson, and unit test. Unit tests identify their placement, assessed lessons, tier, and covered dimensions.

## B1 progression

Use the broad M15 B1 nodes to plan a progression through life experience, personal change, supported opinions, media and relationships, tactful disagreement, coherent narrative, clarification, register choices, community events, and extended familiar discussion. Do not claim granular CEFR certification or use a broad M15 node as a substitute for generated lesson content.

The B1 blueprint uses direct M15 A2.2 prerequisite-node edges only as a lightweight entry context. It does not load an A2 blueprint, create an authority bridge, or authorize lesson generation.

## Validation boundary

Validate only local structural facts:

- all M15 target and entry-prerequisite IDs resolve;
- target tier and dimension match;
- every B1 M15 node is introduced exactly once and reviewed later;
- unit, lesson, review, and unit-test links agree;
- lesson prerequisites are non-forward and acyclic;
- all ten dimensions have a B1.1 and B1.2 allocation.

Do not generate lesson prose, examples, exercises, answer keys, media, practice protocols, assessment items, source payloads, approval evidence, or release claims. The output remains `OUTLINE_ONLY` and is project-authored planning material only. Do not begin a B1 pilot, full B1 corpus, B2 blueprint, or later-level work.

## Commands

```bash
python -m english_master.b1_curriculum_blueprint build \
  curriculum/a1-full/v1/m15-population.json \
  curriculum/b1-blueprint/m16-b1-blueprint.json

python -m english_master.b1_curriculum_blueprint validate \
  curriculum/a1-full/v1/m15-population.json \
  curriculum/b1-blueprint/m16-b1-blueprint.json
```
