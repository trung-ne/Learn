---
name: english-master-rules
description: "Global project rules and policies for English Master. Mandatory reading for all agents. Defines mission, principles, architecture, quality standards, and development process."
---

# English Master — Global Project Rules

## Mission

Build a complete self-study English learning system covering CEFR A1 through C2.

The system should eventually support approximately 1,000+ hours of learning and include:

- Grammar
- Vocabulary
- Vocabulary senses
- Collocations
- Lexical chunks
- Pronunciation
- Listening
- Speaking
- Reading
- Writing
- Communicative functions
- Pragmatics
- Reviews
- Spaced repetition
- Exercises
- Unit tests
- Level tests
- Placement tests
- AI listening practice prompts
- AI speaking practice prompts
- AI pronunciation prompts
- AI writing tutor prompts

Primary learner profile:

Vietnamese learners of English.

Vietnamese explanations may be used when pedagogically useful.

---

# Core Principle

Do NOT attempt to generate the entire A1-C2 course directly.

The main product is a reproducible system that can:

1. collect permitted data
2. normalize data
3. validate provenance
4. classify linguistic content
5. construct curriculum
6. generate lessons
7. generate exercises
8. audit generated content
9. regenerate bad content
10. export development-validated learning materials

Content generation must be reproducible and testable.

---

# CEFR

CEFR is the primary proficiency framework.

Use authoritative CEFR resources as references.

CEFR alignment must be represented explicitly in machine-readable data.

Never trust a generator's self-declared CEFR level without independent validation.

---

# Copyright

Never crawl or copy educational content merely because it is available online.

External sources must be registered before ingestion.

Each source must have a status:

- APPROVED
- REFERENCE_ONLY
- QUARANTINED
- REJECTED

Unknown licensing means QUARANTINED.

REFERENCE_ONLY content may be studied for taxonomy or coverage but must not be copied into generated learning content.

Never bypass:

- authentication
- paywalls
- robots restrictions
- rate limits intended as access controls
- technical access restrictions

Prefer:

- official datasets
- official APIs
- official dumps
- Creative Commons sources
- public domain sources

over scraping webpages.

---

# Provenance

Every externally sourced record must retain provenance.

At minimum:

- source_name
- source_url
- source_record_id
- retrieved_at
- license
- attribution
- content_hash
- ingestion_version

Generated material must retain:

- generator
- model when known
- prompt_version
- generated_at
- curriculum_version
- QA_status

---

# Curriculum

Curriculum must be dependency-based.

Every concept should support:

- id
- name
- CEFR level
- prerequisites
- related concepts
- introduced_in
- reviewed_in

Lessons must not depend on concepts that have not been introduced.

---

# Internal Levels

Support:

- A1.1
- A1.2
- A2.1
- A2.2
- B1.1
- B1.2
- B2.1
- B2.2
- C1.1
- C1.2
- C2.1
- C2.2

Lesson IDs should be deterministic.

Example:

A1-U01-L01

---

# Quality

Generated content remains `UNREVIEWED` in its content lifecycle.

Routine development validation is intentionally lightweight. Check only the concrete risk introduced by the change: documentation/code/knowledge drift, relevant local schema or unit tests, and repository whitespace. Do not require paid services, live AI runners, human review, broad review batches, or approval-like evidence for routine work.

Use `python -m english_master.project_audit` to check active documentation, local implementation paths, and declared repository facts for drift. A passing audit is a consistency result only; it does not establish pedagogical quality, approval, release, provider behavior, or public-distribution authority.

## Development-only validation policy

This project does not require, request, infer, or record human review, human endorsement, or release approval. `HUMAN_REVIEWED` and `RELEASE_APPROVED` are not valid active project statuses or gates.

Historical deterministic and AI evidence may retain their existing `MACHINE_VALIDATED`, `AI_REVIEWED`, or `DEVELOPMENT_APPROVED` labels, but future routine work does not need to create them. If a recorded AI fact is retained, it must identify itself as AI and use factual provider/model provenance or `UNKNOWN`.

Existing immutable artifacts that contain historical human/release fields remain historical records only. They must not be modified, regenerated, or used as authority for new work.

---

# Development Process

Work milestone by milestone.

Do not silently begin the next milestone.

For every requested milestone or scoped change:

1. read the relevant specifications and implementation
2. implement only the requested scope
3. run the project-consistency audit and relevant local tests when code changes; for an explicitly requested M9 run, execute `python -m pytest` and record the required five-packet direct inspection
4. inspect and report concrete failures
5. provide a concise summary and STOP

A change is not complete while its relevant targeted checks fail. Run the full suite only after changes to shared validators, schemas, or other core components.

---

# Technology Direction

Core pipeline:

Python 3.12+

Preferred characteristics:

- typed Python
- structured schemas
- pytest
- reproducible command-line tools
- deterministic identifiers
- structured JSON/YAML data

Do not introduce infrastructure unless there is a demonstrated need.

Start simple.

A future learner web application may use:

- Next.js
- TypeScript
- PostgreSQL

but web UI is not part of the initial milestones.

---

# Repository Hygiene

Never commit:

- secrets
- API keys
- private credentials
- enormous raw datasets
- downloaded data with unclear redistribution rights

Use environment variables when credentials become necessary.

Maintain:

.gitignore

and documentation for all external dependencies.

---

# Agent Behaviour

Before modifying the repository:

1. inspect relevant specifications
2. inspect existing implementation
3. inspect tests

Do not rewrite functioning architecture without explaining why.

Avoid placeholders that pretend a feature has been implemented.

TODO markers must describe specifically what remains incomplete.

Never fabricate test results.

Never claim a command passed unless it was actually executed.

---

# Completion Rule

When completing a task, report:

- files created
- files modified
- commands executed
- tests executed
- pass/fail status
- unresolved issues
- next recommended milestone

Then STOP.
