# German A1 Pilot

## Boundary

The German A1.1 pilot is a closed, deterministic development corpus of ten original project-authored lesson packets derived from [the German A1 blueprint](../course/de/a1/blueprint-v1.json). It tests the additive German language namespace without changing existing English artifacts.

Every packet remains `UNREVIEWED`. The pilot uses no external payloads, media, network access, live audio, or provider invocation. It does not establish pedagogical quality, official CEFR endorsement, source-ingestion or redistribution authority, human review, release approval, provider behavior, pronunciation scoring, learner outcomes, or public-distribution authority.

## Contents

Each packet contains two original German teaching sections, four exercises with answers or a rubric, and one static protocol for each modality:

- **Listening:** transcript-only, with an inline question and answer; no audio is claimed.
- **Speaking:** bounded self-practice or role-play.
- **Pronunciation:** an observable target with `NOT_ASSESSED`; no audio-based assessment occurs.
- **Writing:** draft-first instructions and a static checklist; no replacement text is generated.

The builder rejects claim fields, out-of-scope lesson inputs, invalid modality contracts, duplicate learner-facing text, source-binding drift, hash tampering, and non-closed inventories.

## Local commands

Build a new immutable run:

```bash
.venv/Scripts/python.exe -m english_master.german_a1_pilot build \
  --population curriculum/german-bootstrap/v1/population.json \
  --blueprint course/de/a1/blueprint-v1.json \
  --content course/de/a1/content-input-v1.json \
  --output-root course/de/a1/runs \
  --built-at 2026-09-25T00:00:00Z
```

Verify a published run:

```bash
.venv/Scripts/python.exe -m english_master.german_a1_pilot verify \
  course/de/a1/runs/dea1pilot_078dd4b3e746d82f6f382e50ab7f17b84414e07cb6a1a089dcd73cf7c17cd6ee \
  --population curriculum/german-bootstrap/v1/population.json \
  --blueprint course/de/a1/blueprint-v1.json
```

Publication is atomic and refuses to overwrite an existing run directory.
