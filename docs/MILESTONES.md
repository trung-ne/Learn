# Milestones — English Master

## Overview

This document outlines the major development milestones for the English Master project.

Each milestone has explicit scope, deliverables, and acceptance criteria.

Milestones are executed sequentially. Do not begin the next milestone until the current one is complete.

---

## M0 — Repository Bootstrap

**Status**: Complete (verified 2026-08-28)

**Duration**: ~2-3 days

**Owner**: AI Agent

### Scope

Create the architectural and specification foundation.

Do NOT crawl, download datasets, or generate curriculum.

### Deliverables

1. Repository structure (docs/, src/, tests/, data/, schemas/, etc.)
2. Specification documents:
   - docs/PROJECT_SPEC.md
   - docs/DATA_POLICY.md
   - docs/CURRICULUM_SCHEMA.md
   - docs/QA_SPEC.md
   - docs/MILESTONES.md
3. JSON Schema files for core models
4. Python 3.12+ project with pytest setup
5. Sample validation fixtures
6. .gitignore with data and secrets protection
7. README.md with build/test commands

### Acceptance Criteria

- [x] All specification documents exist and are complete
- [x] Schemas can be loaded and validated
- [x] Sample schema validation passes
- [x] Invalid sample validation fails correctly
- [x] pytest runs successfully
- [x] No external data has been downloaded
- [x] No curriculum has been generated
- [x] Tests document how to use schemas
- [x] README includes step-by-step setup

### Next: M1

---

## M1 — Source Registry & Data Policy

**Estimated Duration**: ~1 week

**Owner**: AI Agent + Human Research

### Scope

Identify, research, and register authoritative data sources for:

- Public domain texts
- Creative Commons datasets
- Official vocabulary lists
- Academic research data
- Official language resources

Do NOT download large quantities yet.

Do register sources and verify licensing.

### Deliverables

1. sources/registry.json: complete list of approved sources
2. sources/license_summary.md: summary of licensing terms
3. Source documentation for each approved source
4. Research notes on rejected sources (why rejected)
5. Policy for quarantine review

### Acceptance Criteria

- [ ] At least 5 approved sources registered
- [ ] All licensing verified
- [ ] Source registry is machine-readable
- [ ] License summary is accurate
- [ ] Rationale for any rejections documented

### Next: M2

---

## M2 — Data Ingestion Pipeline

**Estimated Duration**: ~1-2 weeks

**Owner**: AI Agent

### Scope

Build the data ingestion pipeline:

1. Download/export data from approved sources
2. Parse data into normalized form
3. Validate schema
4. Check provenance
5. Deduplicate
6. Store in data/normalized/

Do NOT classify by CEFR yet.

Do NOT generate curriculum yet.

### Deliverables

1. Python CLI: `ingest.py --source <source_id>`
2. Ingestion scripts for each approved source
3. Normalization for vocabulary, concepts, phrases
4. Deduplicate logic
5. data/normalized/ folder structure
6. Ingestion report: how many records, any errors
7. Tests for ingestion pipeline

### Acceptance Criteria

- [ ] At least one source fully ingested
- [ ] Normalized data is valid
- [ ] Duplicate records are detected
- [ ] Provenance is preserved
- [ ] Ingestion can be reproduced
- [ ] Errors are logged
- [ ] Tests pass

### Next: M3

---

## M3 — Linguistic Analysis & CEFR Classification

**Estimated Duration**: ~2-3 weeks

**Owner**: AI Agent + Linguist

### Scope

Classify ingested content by CEFR level.

1. Analyze vocabulary frequency
2. Analyze word properties (morphology, polysemy)
3. Analyze grammar structures
4. Propose CEFR classifications
5. Manual review and refinement
6. Confidence scoring

### Deliverables

1. Python analyzer: frequency analysis, linguistic features
2. CEFR classifier model (heuristics + manual rules)
3. Classification report for each source
4. Manual review assignments
5. Confidence scores for classifications
6. data/approved/ with CEFR-labeled content
7. Tests for classifier

### Acceptance Criteria

- [ ] Vocabulary is frequency-ranked
- [ ] CEFR classifications exist for majority content
- [ ] High-confidence classifications (>0.8) exceed 70%
- [ ] Manual review completed for low-confidence items
- [ ] Classifications are auditable
- [ ] Tests show classifier behavior

### Next: M4

---

## M4 — Curriculum Architecture & Dependency Graph

**Estimated Duration**: ~2 weeks

**Owner**: AI Agent + Curriculum Designer

### Scope

Design the curriculum structure:

1. Define curriculum units and sequence
2. Group content by CEFR level
3. Build prerequisites and dependencies
4. Verify DAG (no circular dependencies)
5. Design lesson structure and scope
6. Create detailed curriculum roadmap

Do NOT generate lesson content yet.

Do validate curriculum structure.

### Deliverables

1. curriculum/structure.json: units, lessons, dependencies
2. curriculum/prerequisite_graph.json: explicit dependencies
3. Curriculum roadmap: which content belongs in which lesson
4. Lesson templates and structure
5. Tests verifying DAG structure
6. Visualization of curriculum graph
7. Documentation of curriculum design decisions

### Acceptance Criteria

- [ ] Curriculum covers A1.1 through C2.2
- [ ] Dependency graph is acyclic
- [ ] All prerequisites are introduced before use
- [ ] Lessons are balanced in scope
- [ ] Structure supports ~1000 hours of learning
- [ ] Lesson count and structure is reasonable

### Next: M5

---

## M5 — Lesson Generation

**Estimated Duration**: ~2-3 weeks

**Owner**: AI Agent (Claude/Codex)

### Scope

Generate lesson content:

1. Use curriculum structure from M4
2. Extract vocabulary and grammar from M3
3. Generate lesson explanations
4. Create lesson structure (sections, media references)
5. Preserve provenance
6. Run QA

Do NOT generate exercises yet.

Do validate lesson content.

### Deliverables

1. curriculum/lessons/ folder with JSON lesson objects
2. Lesson generator script (prompt-based)
3. QA report: CEFR validation, prerequisite validation, language review
4. Manual review process output
5. Rejected/revised lessons
6. Tests for lesson structure

### Acceptance Criteria

- [ ] At least 10 complete lessons generated
- [ ] All lessons pass schema validation
- [ ] All lessons have correct prerequisites
- [ ] CEFR levels are appropriate (sampled review)
- [ ] No plagiarism detected (spot check)
- [ ] Lessons include vocabulary/grammar references
- [ ] QA report is complete

### Next: M6

---

## M6 — Exercise Generation

**Estimated Duration**: ~3 weeks

**Owner**: AI Agent (Claude/Codex)

### Scope

Generate exercises for lessons:

1. For each lesson, generate exercises
2. Vary exercise types (MC, fill-blank, matching, etc.)
3. Create answer keys
4. Run QA
5. Manual review challenging exercises

### Exercise Types

- Multiple choice
- Fill-in-the-blank
- Matching
- Listening comprehension
- Reading comprehension
- Free response (writing/speaking)

### Deliverables

1. curriculum/exercises/ folder with JSON exercise objects
2. Exercise generator script (type-specific)
3. Answer key validation
4. QA report: answer validation, ambiguity detection, CEFR validity
5. Manual review process output
6. Tests for exercise structure

### Acceptance Criteria

- [ ] At least 50 exercises generated (5 per lesson)
- [ ] Mix of exercise types
- [ ] Answer keys are correct
- [ ] Clarity QA passed
- [ ] CEFR levels appropriate
- [ ] Exercises test correct vocabulary/grammar

### Next: M7

---

## M7 — AI Practice Prompt Generation

**Estimated Duration**: ~1-2 weeks

**Owner**: AI Agent (Claude/Codex)

### Scope

Create AI-driven practice prompts for:

- Listening practice (AI reads, learner listens)
- Speaking practice (AI prompts, learner speaks)
- Pronunciation practice (AI checks pronunciation)
- Writing tutoring (AI gives feedback)

### Deliverables

1. prompts/ folder with JSON prompt templates
2. Prompt generator (system role + template)
3. Evaluation criteria per prompt
4. Tests for prompt structure
5. Sample prompt executions

### Acceptance Criteria

- [ ] At least 20 prompts created
- [ ] Each prompt has clear communicative goal
- [ ] Prompts reference correct vocabulary/grammar
- [ ] Evaluation criteria are reasonable
- [ ] Prompts can be used with Claude API

### Next: M8

---

## M8 — Independent QA

**Estimated Duration**: ~2-4 weeks

**Owner**: Human QA Team

### Scope

Comprehensive QA review:

1. Schema validation (automated)
2. CEFR validation (sampled manual)
3. Grammar/lexical validation (expert review)
4. Pedagogical review (educator review)
5. Copyright/provenance validation (automated)
6. Language quality review (native speaker)

### Deliverables

1. QA report for each content type
2. Identified issues and recommendations
3. Revision requests
4. Revision tickets logged

### Acceptance Criteria

- [ ] All content paths reviewed
- [ ] Critical issues identified
- [ ] >95% content passes automated checks
- [ ] >90% of sample manual review passes
- [ ] Revision queue is prioritized

### Next: M9

---

## M9 — Revision Cycle

**Estimated Duration**: ~2-3 weeks

**Owner**: AI Agent + Subject Matter Experts

### Scope

Fix issues identified in M8:

1. Revise failed content
2. Address QA feedback
3. Re-run QA
4. Approve or escalate

### Deliverables

1. Revised content
2. QA report (second pass)
3. Unresolved issues escalation
4. Final approval list

### Acceptance Criteria

- [ ] >98% of content approved
- [ ] Only critical unresolved issues remain
- [ ] Revisions are auditable

### Next: M10

---

## M10 — Export & Packaging

**Estimated Duration**: ~1 week

**Owner**: AI Agent

### Scope

Package content for different modalities:

1. Export to a selected LMS package format
2. Export to JSON/CSV for data scientists
3. Create mobile-friendly format
4. Create web-friendly format
5. Create printable materials

### Deliverables

1. Standardized export formats
2. Export scripts
3. Format validation
4. Documentation for using exported materials

### Acceptance Criteria

- [ ] All formats valid
- [ ] Data integrity preserved
- [ ] Export commands are reproducible

### Next: M11

---

## M11 — Web Platform (Optional, Future)

**Estimated Duration**: ~4-6 weeks

**Owner**: Frontend Team

### Scope

Build web UI for learners:

- Next.js frontend
- TypeScript
- Lesson viewer
- Exercise taker
- Progress tracking
- Spaced repetition scheduler

### Note

This is future work. Core curriculum is production-ready before web platform.

---

## M12 — Production Deployment

**Estimated Duration**: ~1-2 weeks

**Owner**: DevOps + Product

### Scope

Deploy to production:

1. Infrastructure setup
2. Security hardening
3. Load testing
4. Public launch preparation
5. Documentation for users

### Acceptance Criteria

- [ ] Platform is scalable
- [ ] Security is validated
- [ ] User documentation is complete
- [ ] Support process is in place

---

## Summary

**Total Estimated Timeline**: ~4-5 months

**Core Milestones**: M0 - M10 (most important)

**Future**: M11 - M12 (web platform and deployment)

Each milestone is a deliberate, auditable step toward a complete A1-C2 English learning system.

No milestone is skipped.

No milestone is started until the previous one is complete.

Quality over speed.
