# Project Specification — English Master

## Mission

Build a complete, reproducible, self-study English learning system covering CEFR A1 through C2.

The system should support approximately 1,000+ hours of quality learning and include:

- Grammar
- Vocabulary (with senses, collocations, chunks)
- Pronunciation
- Listening, Speaking, Reading, Writing
- Communicative functions
- Pragmatics
- Progressive review and spaced repetition
- Exercises and assessments
- AI-driven speaking and listening practice prompts
- Comprehensive testing and validation

Primary learner profile: Vietnamese learners of English

Vietnamese explanations may enhance pedagogy where appropriate.

---

## System Boundaries

### In Scope

- Curriculum design and content generation
- Linguistic analysis and CEFR classification
- Quality assurance and validation
- Data sourcing and licensing compliance
- Exercise and assessment generation
- AI prompt engineering for practice
- Export in multiple formats (JSON, CSV, USDML, etc.)

### Out of Scope (Initially)

- Web/mobile frontend UI (planned for Phase 2)
- Spaced repetition scheduling (algorithmic support, not learning experience)
- Student data storage (focus on curriculum, not LMS)
- Real-time synchronous tutoring (AI prompts are template-based)

---

## Architecture

The system follows a **pipeline architecture**:

```
Data Sources
    ↓
[Ingestion] → Normalize & Validate
    ↓
[Linguistic Analysis] → CEFR Classification
    ↓
[Curriculum Planning] → Dependency Graph
    ↓
[Generation] → Lessons, Exercises, Prompts
    ↓
[QA] → Manual & Automated Validation
    ↓
[Approval] → Publish to Approved Data
    ↓
[Export] → Multiple Formats
```

### Key Components

1. **Source Registry**: Registered, licensed data sources
2. **Ingestion Pipeline**: Download, parse, normalize external data
3. **Linguistic Analyzer**: Frequency analysis, word properties, structure analysis
4. **CEFR Classifier**: Linguistic features → CEFR level assignment
5. **Curriculum Planner**: Design course structure and prerequisites
6. **Lesson Generator**: Create lesson content (Claude/Codex)
7. **Exercise Generator**: Create practice exercises (Claude/Codex)
8. **QA Engine**: Validate schema, grammar, answers, copyright
9. **Approval System**: Manual review and final approval
10. **Export Engine**: Package for different modalities

---

## Data Flow

### Upstream Phase

```
External Sources (Wikimedia, Dictionary APIs, Public Domain, CC-BY) 
  → Licensed & Registered 
  → Downloaded 
  → Parsed 
  → Normalized (JSON schema) 
  → Stored in data/normalized/ 
  → Deduplicated 
  → Linguistically Analyzed 
  → Stored in data/approved/
```

### Generation Phase

```
Curriculum Planning (M4)
  → Lesson Structure (what content, what order)
  → Exercise Requirements (what to practice)
  → AI Prompts (what to generate)
    ↓
[Claude/Codex Generator]
  → Lesson JSON
  → Exercise JSON
  → Prompt Templates
  → QA Metadata
    ↓
[QA Engine]
  → Schema Validation ✓
  → CEFR Validation ✓
  → Prerequisites ✓
  → Grammar ✓
  → Answer Keys ✓
  → Copyright ✓
  → Language Quality [Human]
    ↓
[Status: APPROVED | NEEDS_REVISION | REJECTED]
    ↓
data/approved/[type]/
```

### Export Phase

```
data/approved/
  → Formatting Engine
  → Multiple Exports:
     - JSON (API use)
     - CSV (data analysis)
     - USDML (LMS compatibility)
     - Mobile format
     - Print format
```

---

## Major Modules

### 1. Source Management
- Tracks authorized data sources
- Manages licensing compliance
- Registers provenance
- Maintains source registry

### 2. Data Ingestion
- Downloads/exports from sources
- Parses various formats
- Normalizes to canonical schemas
- Validates and deduplicates
- Stores with full provenance

### 3. Linguistic Analysis
- Computes word frequency
- Analyzes morphology
- Analyzes grammar complexity
- Extracts linguistic features
- Generates classification signals

### 4. CEFR Classification
- Applies linguistic heuristics
- Scores confidence
- Enables manual override
- Produces ranked classifications
- Auditable decisions

### 5. Curriculum Planning
- Designs course structure
- Groups content by level
- Builds prerequisite DAG
- Allocates content to lessons
- Plans review spirals

### 6. Generation
- Generates lesson explanations
- Generates exercises
- Generates AI practice prompts
- Uses templates + AI
- Preserves metadata for traceability

### 7. Quality Assurance
- Validates all schemas
- Checks CEFR alignment
- Verifies answers
- Detects ambiguity
- Performs copyright checks
- Human language review

### 8. Approval System
- Tracks review status
- Records decisions
- Manages revisions
- Logs final approval
- Maintains audit trail

### 9. Data Storage
- Raw data (data/raw/)
- Normalized data (data/normalized/)
- Approved data (data/approved/)
- Quarantine (data/quarantine/)
- Source metadata

### 10. Export Engine
- JSON export
- CSV export
- USDML/IMS export
- Mobile-ready format
- Print-friendly format

---

## Expected Outputs

### Curriculum

- **1,000+ hours** of learning content
- **6 CEFR levels** × **2 subdivisions each** = 12 proficiency tiers
- **Approximately 120 units** (10 per tier)
- **Approximately 600+ lessons** (5-6 per unit)
- **Approximately 3,000+ exercises** (5-10 per lesson)
- **Pronunciation, listening, speaking, reading, writing** - all skills covered

### Lesson Components

Each lesson contains:

- Vocabulary introductions (with senses, examples, pronunciation)
- Grammar explanations (with rules, examples, exceptions)
- Lexical chunks (phrasal verbs, idioms, collocations)
- Communicative functions (what the learner can *do*)
- Content sections (explanations, dialogues, readings)
- Embedded examples and media references
- Prerequisite information

### Exercise Types

- Multiple choice
- Fill-in-the-blank
- Matching (vocabulary, grammar, phrases)
- Listening comprehension
- Reading comprehension
- Free response (writing, speaking)
- Unit tests
- Level tests
- Placement tests

### AI Practice Prompts

- Listening practice (AI speaks, learner listens and responds)
- Speaking practice (AI prompts, learner speaks)
- Pronunciation practice (AI evaluates)
- Writing tutoring (AI gives feedback)

### Assessments

- Placement test (initial level diagnosis)
- Unit tests (after each unit)
- Level tests (after each CEFR tier)
- Progress checks (built into lessons)

---

## Curriculum Lifecycle

### Creation Phase (M4-M7)

1. Curriculum structure designed (prerequisites, sequence)
2. Lessons generated (content)
3. Exercises generated (practice)
4. Prompts generated (AI interaction)

### QA Phase (M8-M9)

1. Automated QA (schema, CEFR, prerequisites)
2. Linguistic QA (grammar, vocabulary, authenticity)
3. Pedagogical QA (clarity, sequencing, pedagogical soundness)
4. Copyright QA (license compliance, attribution)
5. Revisions and approvals

### Publishing Phase (M10)

1. Approved content packaged
2. Exported to multiple formats
3. Version tagged and archived

### Maintenance Phase (Post-Launch)

1. Learner feedback collected
2. Issues reported
3. Content updated
4. New versions released

---

## Data Lifecycle

### Raw Data

- Source: downloaded directly from approved sources
- Storage: data/raw/{source_id}/{timestamp}/
- Retention: ~1-2 cycles after approval
- Deletion: explicitly logged

### Normalized Data

- Extracted from raw, parsed to canonical schema
- Deduplicated, validated
- Storage: data/normalized/{source_id}/
- Retention: during active phase
- Loaded for linguistic analysis

### Approved Data

- Classified, QA-validated, pedagogically reviewed
- Ready for curriculum use
- Storage: data/approved/{category}/
- Retention: permanent
- Basis for lesson generation

### Quarantined Data

- Licensing unknown, incomplete provenance, copyright issues
- Storage: data/quarantine/{reason}/
- Retention: 90 days minimum (for appeal)
- May be moved to APPROVED if provenance resolves

---

## Approval Lifecycle

### Status States

1. **UNREVIEWED**: Generated but not yet reviewed
2. **IN_REVIEW**: Assigned to reviewer
3. **NEEDS_REVISION**: QA failed; changes needed
4. **REVISION_SUBMITTED**: Changes submitted; awaiting re-review
5. **APPROVED**: Passed all QA; ready for use
6. **REJECTED**: Unrecoverable failures; not approved
7. **ARCHIVED**: Previous version after new one approved

### Transitions

```
UNREVIEWED  → IN_REVIEW  → APPROVED (if passes)
                        ↙
          NEEDS_REVISION → REVISION_SUBMITTED → IN_REVIEW (loop)
                        ↘ 
                       REJECTED
```

### QA Gates

Content must pass before state change:

- Schema validation (automated)
- CEFR validation (automated + spot checked)
- Prerequisite validation (automated)
- Grammar/lexical validation (expert review)
- Answer validation (expert review)
- Language quality review (human native speaker)
- Copyright validation (automated + legal)

---

## Failure Handling

### Generation Failures

- Record failure reason
- Log in content_error_log.md
- Trigger regeneration with refined prompt
- If repeated failure: escalate to human review

### QA Failures

- Categorize failure type (schema, CEFR, answer, etc.)
- Generate revision request
- Assign to responsible party (generator or human)
- Track revision status

### Ingestion Failures

- Record source issue (API down, format changed, etc.)
- Quarantine problematic records
- Alert source owner
- Retry on next scheduled run

### Critical Failures

- Data corruption detected: restore from backup
- License conflict: quarantine content, research resolution
- Impossible prerequisites: curriculum DAG violated (shouldn't happen)

---

## Reproducibility Requirements

### Deterministic IDs

All IDs are deterministic:

- Lesson: CEFR_UNIT_LESSON (A1_U01_L01)
- Concept: concept_{snake_case}
- Vocabulary: vocab_en_{word}_{sense}

Regenerating same content produces same IDs.

### Versioning

- Schema versions: major.minor
- Content versions: date-based (YYYYMMDD)
- Generator versions: model + version
- Prompt versions: git commit + version tag

### Audit Trail

- Every ingestion logged with timestamp, source, record count
- Every generation logged with prompt, model, timestamp
- Every QA decision logged with reviewer, criteria, pass/fail
- Every approval logged with reviewer, date, status
- Every export logged with format, timestamp, content_hash

### Reproducible Builds

```bash
# Recreate curriculum from source
python scripts/ingest.py --all
python scripts/analyze.py --classify-cefr
python scripts/plan_curriculum.py
python scripts/generate.py --lessons --exercises --prompts
python scripts/qa.py --all
python scripts/export.py --all-formats
```

Result is byte-for-byte identical to previous run (deterministic generation).

---

## Summary

English Master is a systematically designed, thoroughly validated, production-quality English learning system.

The pipeline ensures:

- **Quality**: extensive QA and human review
- **Compliance**: rigorous copyright and licensing management
- **Traceability**: auditable provenance and decisions
- **Reproducibility**: deterministic, script-driven processes
- **Scalability**: pipeline handles large content volumes
- **Extensibility**: new sources, new exercises, new exports

The project prioritizes building the system correctly over building it quickly.

Content is not rushed to production.

Milestones are sequential and deliberate.