# M0 — Repository Bootstrap

## Objective

Create the architectural and specification foundation for English Master.

Do NOT crawl external websites.

Do NOT download datasets.

Do NOT generate the A1-C2 curriculum.

Do NOT generate large quantities of lessons or exercises.

This milestone establishes the rules and schemas future milestones must follow.

---

# Required Work

Inspect:

- PROJECT_RULES.md
- AGENTS.md or CLAUDE.md as applicable
- current repository state

Then create the initial repository architecture.

At minimum create:

docs/
schemas/
src/
tests/
data/
sources/
curriculum/
prompts/

Appropriate subdirectories may be added when justified.

---

# Required Specifications

Create:

docs/PROJECT_SPEC.md

Document:

- mission
- system boundaries
- architecture
- data flow
- major modules
- expected outputs
- curriculum lifecycle
- data lifecycle
- approval lifecycle
- failure handling
- reproducibility requirements

Create:

docs/DATA_POLICY.md

Document:

- source registration
- license handling
- permitted ingestion
- prohibited ingestion
- provenance
- attribution
- quarantine
- raw data handling
- generated content
- data retention
- copyright safety

Create:

docs/CURRICULUM_SCHEMA.md

Define conceptual models for:

- CEFR levels
- skills
- linguistic concepts
- vocabulary senses
- grammar concepts
- pronunciation concepts
- communicative functions
- lessons
- exercises
- assessments
- reviews
- AI practice prompts
- prerequisites
- curriculum graph

Create:

docs/QA_SPEC.md

Define:

- schema QA
- CEFR QA
- grammar QA
- lexical QA
- prerequisite QA
- answer QA
- ambiguity QA
- duplicate QA
- copyright QA
- provenance QA

Create:

docs/MILESTONES.md

Define detailed milestones from M0 through production-ready A1-C2.

---

# Machine-readable Schemas

Create machine-readable schemas for core objects.

At minimum include:

- source
- concept
- vocabulary sense
- lesson
- exercise
- AI practice prompt

Use a coherent schema strategy.

Prefer JSON Schema or typed models that can also generate JSON Schema.

Do not create multiple competing schema definitions.

---

# Python Project

Create a minimal Python 3.12+ project.

Use typed code.

Create a minimal test setup using pytest.

Provide one or more small fixtures demonstrating schema validation.

Do not introduce complex infrastructure.

---

# Data Folders

Design folders for:

data/raw
data/normalized
data/approved
data/quarantine

Raw datasets must not be committed by default.

Add suitable .gitignore rules.

---

# Source Registry

M0 may define the structure/schema for the source registry.

M0 must NOT yet research and approve external sources.

Actual source research belongs to M1.

---

# Test Fixtures

Add tiny artificial fixtures.

Do NOT use copied educational materials.

Fixtures may contain invented example sentences such as:

"I drink coffee every morning."

They exist only to prove schemas and validators work.

---

# Commands

Document commands for:

- environment setup
- installing dependencies
- running tests
- running validation

---

# Acceptance Criteria

M0 passes only if:

1. repository structure exists
2. required docs exist
3. core schemas exist
4. source status model exists
5. pytest works
6. sample validation succeeds
7. invalid sample validation fails correctly
8. .gitignore protects raw datasets and secrets
9. documentation contains reproducible commands
10. no external content has been crawled
11. no large curriculum has been generated

---

# Completion

Run all M0 tests.

Inspect repository state.

Provide a report containing:

## Created
## Modified
## Commands Run
## Tests
## Test Results
## Design Decisions
## Open Issues
## M0 Acceptance Criteria

Explicitly state whether M0 is:

PASS

or:

FAIL

Then STOP.

Do not start M1.
