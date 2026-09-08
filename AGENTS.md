---
name: english-master-agents
description: "Codex agent instructions for English Master project. Read all specifications before making changes. Follow only explicitly requested milestone."
---

# English Master Agent Instructions

Before making changes, read:

- PROJECT_RULES.md
- docs/PROJECT_SPEC.md if it exists
- docs/DATA_POLICY.md if it exists
- docs/CURRICULUM_SCHEMA.md if it exists
- docs/QA_SPEC.md if it exists
- docs/MILESTONES.md if it exists

PROJECT_RULES.md is mandatory.

## Validation policy

For future work, use deterministic and AI-based validation only. Do not require, create, infer, or claim `HUMAN_REVIEWED`, `RELEASE_APPROVED`, human review, human endorsement, or release approval. Existing immutable artifacts containing those historical fields must remain unchanged and cannot authorize new work.

Follow only the milestone explicitly requested by the user.

Never automatically begin another milestone.

Do not ingest external learning material until the project's source and licensing system exists.

Do not generate the full A1-C2 curriculum unless the generation and QA systems have already been implemented and validated.

Run all applicable tests before declaring a task complete.

At completion report:

- files created
- files changed
- tests run
- test results
- unresolved issues

Then stop.
