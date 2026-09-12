# A2 Blueprint Authoring Contract

Build an outline-only A2 curriculum blueprint from the existing M15 knowledge-graph population.

## Inputs and scope

- Use `curriculum/a1-full/v1/m15-population.json` as the exact M15 input.
- Cover the internal curriculum tiers `A2.1` and `A2.2`; these are internal subdivisions, not official CEFR levels.
- Preserve the M15 population and all A1 artifacts unchanged.
- Use deterministic IDs beginning with `m16a2-v1-a2-`.
- Produce ten units and fifty lesson outlines: five units per tier and five lessons per unit.
- Mark each fifth lesson as a review lesson and place one unit test after it.

## Required outline fields

Each lesson outline must retain only:

- deterministic ID, unit, tier, and sequence;
- concise title and objectives;
- resolved M15 target-node IDs with their dimensions and `INTRODUCE`, `PRACTISE`, or `REVIEW` use;
- internal lesson prerequisites.

Units must identify their lessons, review lesson, and unit test. Unit tests must identify their placement, assessed lessons, tier, and covered dimensions.

## A2 progression

Use the broad M15 A2 nodes to plan a progression from A1 through recent-event narration, count/noncount transactional language, health/travel/local-service interactions, future plans, work/study/community contexts, offers, invitations, and arrangements. Do not claim granular CEFR certification or use a broad M15 node as a substitute for generated lesson content.

The A2 blueprint uses direct M15 A1.2 prerequisite-node edges only as a lightweight entry context. It does not load an A1 blueprint, create an authority bridge, or authorize lesson generation.

## Validation boundary

Validate only local structural facts:

- all M15 target and entry-prerequisite IDs resolve;
- target tier and dimension match;
- every A2 M15 node is introduced exactly once and reviewed later;
- unit, lesson, review, and unit-test links agree;
- lesson prerequisites are non-forward and acyclic;
- all ten dimensions have an A2.1 and A2.2 allocation.

Do not generate lesson prose, examples, exercises, answer keys, media, prompts, assessments items, source payloads, approval evidence, or release claims. The output remains `OUTLINE_ONLY` and is project-authored planning material only.

## Commands

```bash
python -m english_master.a2_curriculum_blueprint build \
  curriculum/a1-full/v1/m15-population.json \
  curriculum/a2-blueprint/m16-a2-blueprint.json

python -m english_master.a2_curriculum_blueprint validate \
  curriculum/a1-full/v1/m15-population.json \
  curriculum/a2-blueprint/m16-a2-blueprint.json
```
