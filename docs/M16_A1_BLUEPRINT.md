# M16 A1 Blueprint

The `english_master.curriculum_blueprint` CLI builds and validates an immutable, deterministic A1 outline from an M15 population:

```bash
python -m english_master.curriculum_blueprint build population.json blueprint.json
python -m english_master.curriculum_blueprint validate population.json blueprint.json
```

The output covers ten units (A1.1 and A1.2), fifty lesson outlines, review placements, and unit/tier assessment blueprints. All targets are resolved against M15 nodes. It is fixture/development evidence with `OUTLINE_ONLY` status only. It contains no prose, exercises, answers, or media and does not alter M2 or M5.
