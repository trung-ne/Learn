# B2 Blueprint Authoring Contract

Build an outline-only B2 curriculum blueprint from the existing M15 knowledge-graph population.

## Inputs and scope

- Use `curriculum/a1-full/v1/m15-population.json` as the exact M15 input.
- Cover internal curriculum tiers `B2.1` and `B2.2`; these are internal subdivisions, not official CEFR levels.
- Preserve M15 and all earlier-level artifacts unchanged.
- Use deterministic IDs beginning with `m16b2-v1-b2-`.
- Produce ten units and fifty lesson outlines: five units per tier and five lessons per unit.
- Mark each fifth lesson as a review lesson and place one unit test after it.

## Required outline fields

Each lesson retains only deterministic identity and placement, concise title and objectives, resolved M15 targets with `INTRODUCE`, `PRACTISE`, or `REVIEW` use, and internal lesson prerequisites. Units and unit tests retain their closed links and placement.

## Continuity and validation

Use direct M15 B1.2 prerequisites only as entry context. Do not load an earlier-level blueprint, create an authority bridge, or authorize generation. Validate source hashes, node resolution, tier/dimension agreement, exact introduction and later review coverage, link integrity, non-forward prerequisites, and acyclicity.

Do not generate lesson prose, examples, exercises, answer keys, media, practice protocols, assessment items, source payloads, approval evidence, or release claims. Output remains `OUTLINE_ONLY`. Do not begin a B2 pilot or full B2 corpus.

## Commands

```bash
python -m english_master.b2_curriculum_blueprint build   curriculum/a1-full/v1/m15-population.json   curriculum/b2-blueprint/m16-b2-blueprint.json

python -m english_master.b2_curriculum_blueprint validate   curriculum/a1-full/v1/m15-population.json   curriculum/b2-blueprint/m16-b2-blueprint.json
```
