# Full C2 Development Corpus

Full C2 derives the exact fifty C2.1/C2.2 outlines in `curriculum/c2-blueprint/m16-c2-blueprint.json` into a separate development corpus under `curriculum/c2-full/v1/`. The `.1` and `.2` tiers are internal curriculum subdivisions, not official CEFR levels.

## Contents

- `allocation.json`: granular target allocation bound to the M15 population and M16 C2 blueprint.
- `units/`: ten project-authored unit files containing fifty lessons.
- `content-manifest.json`: closed, hash-bound inventory of the unit files.
- `runs/`: one source-derived packet per lesson plus a closed run manifest.
- `reports/audit-v1.json`: lightweight deterministic full-population audit.
- `samples/sample-12-v1.json`: reproducible, SHA-256-ranked sample covering every unit.

Each lesson has objectives, two teaching sections, three exercises, and listening, speaking, pronunciation, and writing protocols. Listening is transcript-only, pronunciation returns `NOT_ASSESSED` without audio, and writing is feedback-only.

## Commands

Use the installed `english-master-c2-full` entrypoint, or `python -m english_master.c2_full.cli`, with `build`, `verify`, `audit`, or `sample`. Each command requires the M15 population, M16 C2 blueprint, allocation, and content manifest paths. Build uses atomic no-overwrite publication; verification reconstructs all fifty packets from those inputs.

## Boundary

All content is original project-authored development material and remains `UNREVIEWED`. Deterministic validation does not establish linguistic or pedagogical quality, CEFR endorsement, learner outcomes, human/release approval, live-provider behavior, public-distribution authority, or real-media processing.
