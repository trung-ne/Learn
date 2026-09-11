# Curriculum Schema — English Master

## Overview

This document defines the conceptual models for curriculum content in English Master. The Draft 2020-12 files in `schemas/` are the single authoritative machine-readable definitions. For the six M0 core records, the descriptions below use the same field names as their schemas; all six additionally carry `schema_version`, shared generated-content fields are represented by `generation_metadata`, and externally sourced fields by `provenance`. Future model descriptions are conceptual until their schemas are introduced in their designated milestones.

---

## CEFR Framework

Supported levels:

- A1.1, A1.2 (Beginner)
- A2.1, A2.2 (Elementary)
- B1.1, B1.2 (Intermediate)
- B2.1, B2.2 (Upper Intermediate)
- C1.1, C1.2 (Advanced)
- C2.1, C2.2 (Mastery)

All CEFR assignments are explicit and independently validated.

The `.1` and `.2` tiers are **internal curriculum subdivisions**. They are not official CEFR levels and must never be presented as such.

---

## M2 Taxonomy Collections

The representative M2 knowledge model is stored in:

- `curriculum/taxonomy/taxonomy.json` — concepts, vocabulary senses, and Vietnamese learner annotations.
- `curriculum/taxonomy/coverage-matrix.json` — broad expected category coverage for each official CEFR band, expressed through internal range labels.

The prototype is deliberately small. Its descriptions, examples, sequencing hypotheses, and coverage emphasis are original project-authored material. External URLs are citations for later review; no cited descriptor, dictionary definition, example, or research text is copied into the prototype.

### Taxonomy Concept

Every concept has `id`, `type`, `name`, `description`, `minimum_cefr`, `prerequisites`, typed `related_concepts`, `evidence_or_reference`, and `status`. Supported types are skills, grammar, collocations, lexical chunks, pronunciation, communicative functions, topics, discourse, pragmatics, and assessment capabilities. Prerequisites form a directed acyclic graph; related concepts are typed, non-ordering links.

### Taxonomy Vocabulary Sense

A vocabulary record identifies one sense, not merely a surface word. Its deterministic ID is derived from `language`, normalized `lemma`, and zero-padded `sense_number`. It separately records part of speech, definition, CEFR tier, collocations, chunks, original examples, concept prerequisites, and typed sense relationships.

### Vietnamese Learner Annotation

An annotation targets a known concept or vocabulary sense. `annotation_kind` distinguishes `RESEARCH_CLAIM` from `PEDAGOGICAL_OBSERVATION`, and matching evidence metadata is mandatory. Difficulty is explicitly variable when evidence does not justify a population-wide prediction. These annotations guide review and teaching responses; they do not label every Vietnamese learner.

### Evidence and Status

Evidence entries distinguish authoritative references, research claims, pedagogical observations, and original authored prototypes. Citation metadata does not grant permission to copy source content. All representative records remain `DRAFT` until independent linguistic and pedagogical review in later milestones.

### Collection Validation

JSON Schema checks record shape and valid CEFR values. Collection validation additionally checks:

- unique concept, sense, and annotation IDs;
- resolvable concept prerequisites and relationships;
- an acyclic prerequisite graph;
- deterministic vocabulary-sense identities and resolvable sense relationships;
- resolvable annotation targets; and
- one unique coverage row for every A1-C2 band.

Run both committed collections through the offline CLI:

```bash
python -m english_master.schema_validation --schema taxonomy curriculum/taxonomy/taxonomy.json
python -m english_master.schema_validation --schema coverage-matrix curriculum/taxonomy/coverage-matrix.json
```

---

## M5 Curriculum Architecture Collections

M5 uses separate outline-only schemas rather than the full lesson schema defined below. The aggregate `curriculum/structure.json` contains six official CEFR bands, all twelve ordered internal tiers, globally numbered units, lesson outlines, and review nodes. Global numbering is required because lesson IDs omit `.1` and `.2`: `A1.1-U01` produces `A1-U01-L01`, while `A1.2-U02` produces `A1-U02-L01`.

The authoritative companion records are `curriculum/prerequisite_graph.json` and `curriculum/coverage-roadmap.json`. Ordering edges (`lesson_prerequisite`, `unit_ordering`, and `taxonomy_prerequisite`) are distinct from introduction, review, and related/non-ordering edges. Coverage records identify introduction, development, and review placements for all sixteen required dimensions.

All current M2 records remain `DRAFT`. M5 references them only under the manifest's explicit conditional review gate for outline planning; the gate blocks content generation and requires independent linguistic and pedagogical review before M6. It does not approve the taxonomy.

The compact M5 artifact demonstrates the complete hierarchy and validation contract. Its target unit, lesson, and hour ranges are planning estimates for later expansion, not generated content or unsupported precise attainment claims.

Validate all linked collections offline:

```bash
python -m english_master.curriculum_validate curriculum/structure.json
```

See [docs/CURRICULUM_ARCHITECTURE.md](CURRICULUM_ARCHITECTURE.md) for identifier, graph, governance, coverage, and CLI details.

### M5 Independent Review Records

M5 review governance uses strict records without changing the source bundle. `curriculum-review-manifest.schema.json` inventories the four independently reloaded canonical parsed artifacts, complete referenced taxonomy prerequisite closure, and every Vietnamese learner annotation with SHA-256 hashes, and separately binds the independently reloaded source registry by actual path, schema version, and complete hash. It also binds the exact checklist/validator/canonicalization profile and transitive hashes of the review schema dependency closure. The workflow validates every externally grounded citation in both reviewed scopes against that registry; only registered `APPROVED` or `REFERENCE_ONLY` sources with reference permission and a matching declared locator scope are eligible. `curriculum-independent-review-draft.schema.json` validates a completed human submission before deterministic ID finalization; `curriculum-independent-review.schema.json` validates the finalized hash-bound linguistic or pedagogical decision. `curriculum-reviewer-registry.schema.json` defines the separately administered trusted identity/evidence boundary. `curriculum-approval-snapshot.schema.json` repeats the source-registry binding and defines a deterministic approval overlay mechanically publishable only after two externally verified, distinct reviewers approve all checks without blocking findings.

The manifest explicitly does not authorize content generation, and the approval snapshot contains no generated lesson content. Reviewed annotations remain a separate context collection and are never included in `approved_taxonomy_records` or treated as generation authority. Canonical identities exclude only their own identity field; complete-record hashes include the identity. See [M5_REVIEW_WORKFLOW.md](M5_REVIEW_WORKFLOW.md).

---

## M6 Lesson Generation Contracts

M6 adds strict machine-readable contracts for `lesson-generation-authorization`, `lesson-generation-request`, `lesson-generation-audit`, `lesson-generation-rejection`, `lesson-independent-review`, and `lesson-batch-qa-report`. Authorization is rebuilt from a reverified M5 approval snapshot and may narrow, but never create, approved taxonomy scope. It binds all six snapshot members plus the independently loaded M5 structure, graph, coverage, taxonomy, source registry, exact allocated/prerequisite-closure records, and their canonical hashes. A request is rebuilt from that authority, the outline projection, graph context, previous knowledge, exact typed allowed/forbidden sets, bounds, and project-authored teaching payload; it contains no caller-declared provider, model, or execution time. The validator rejects any drift; canonical request and authorization identities alone never grant permission.

The shared `common.schema.json` definitions are authoritative for tier-qualified unit IDs, lesson IDs, concept IDs, communicative-function IDs, vocabulary-sense IDs, and syntactically explicit ISO timestamps; M5 reuses those definitions. The backend response contains only `content_sections` in a prompt-hash-bound captured response envelope. Orchestration injects the remaining schema-valid lesson fields, actual runtime provenance, and `UNREVIEWED` status. M6 semantically requires exact reference scope, canonical ordering, bounded nonempty section titles and bodies, and `exercises: []`. Audit checks use `PASS`, `FAIL`, or `NOT_RUN`, report actual capture/reproducibility facts, and retain outstanding independent reviews. Independent review records bind exact lesson and audit hashes without changing approval status; batch reports validate ten ordered immutable bundles and declared human-review evidence without inferring a human result. See [LESSON_GENERATION.md](LESSON_GENERATION.md).

M6 development evidence uses distinct `lesson-ai-review` and `lesson-development-batch` records. Their `approval_tier` values are respectively `AI_REVIEWED` and `DEVELOPMENT_APPROVED`, while `reviewer_type: AI` is mandatory on the former. They hash-bind the exact M5 development snapshot, lesson, audit, prompt, and response evidence; neither schema has human identity, qualifications, or release fields. A passing development batch is not a content-lifecycle `APPROVED` record, `HUMAN_REVIEWED`, or `RELEASE_APPROVED` claim.

## M7 Exercise Generation Contracts

M7 uses separate authorization, request, narrow backend-candidate, exercise-set, audit, rejection, independent-AI-review, and development-batch contracts. Its authority independently revalidates the M5 development snapshot and complete M6 `DEVELOPMENT_APPROVED` batch before it derives a lesson-bound request. Backend responses contain authored exercise items only; host orchestration supplies deterministic `ex_{lesson}_{sequence}` identities, exact upstream bindings, output hashes, `UNREVIEWED` status, and trusted generation metadata.

The current M7 development policy permits only `PROJECT_AUTHORED` inline text and transcript-only listening (`media_required: false`), so no external media or text operation is authorized or exercised. The contracts explicitly support multiple choice, fill blank, matching, ordering, error correction, sentence construction, translation, reading, listening, speaking, and writing. Objective tasks need complete defensible answer data; subjective tasks require analytic rubrics and remain reviewable. Automated acceptance establishes only structural machine validation. Separate AI linguistic and pedagogical reviews may establish `AI_REVIEWED` development evidence for an unchanged set; a complete hash-bound batch may establish `DEVELOPMENT_APPROVED`. Neither changes an exercise's `UNREVIEWED` lifecycle status or claims human/release approval. See [EXERCISE_GENERATION.md](EXERCISE_GENERATION.md).

## M8 QA Engine Contracts

M8 uses strict request, candidate-attempt, stage-receipt, model-invocation, AI-review, rejection, operational-failure, decision, and terminal run-manifest records. Six ordered receipts represent schema, answer, CEFR, prerequisite, duplicate, and language QA. Each candidate and receipt is hash-bound; a failure records an immutable rejection and only a newly generated candidate revision can retry. Regenerated candidates bind an exact host-built prompt and raw response to their parent rejection and receive fresh candidate-bound AI review after machine stages pass. Replay, test, mock, unsupported, parameter-mismatched, and authentication-asserting evidence cannot promote a changed revision. A passing decision is `DEVELOPMENT_APPROVED` while its content lifecycle remains `UNREVIEWED`; every contract prohibits human/release claims. Complete approved, rejected, and operational runs are atomically published with a manifest and independently reverified. See [QA_ENGINE.md](QA_ENGINE.md).

## M8.2 AI Practice Prompt Contracts

M8.2 uses a separate authorization, lesson-derived request, typed lesson-bound prompt artifact, deterministic audit, and closed pilot-manifest family. It independently binds the M5 development snapshot, exact M6 development batch, every lesson/audit hash, CEFR, known/target reference partitions, communicative functions, pronunciation target context, prerequisite context, prompt version, and factual project-authored provenance. The legacy generic `ai-practice-prompt` schema remains a conceptual M0 model and is not used for M8.2 publication.

The compact pilot has exactly ten lessons × four modalities. Its listening contract keeps transcripts private before an attempt and limits questions by turn; speaking uses explicit roles and turn bounds; pronunciation assessment requires audio and returns `NOT_ASSESSED` without it; writing is draft-first and forbids full replacement. A passing audit establishes only `MACHINE_VALIDATED`; every artifact remains `UNREVIEWED`, with `human_reviewed`, `release_approved`, and `provider_authenticated` false. See [AI_PRACTICE_PILOT.md](AI_PRACTICE_PILOT.md).

## M9 Lightweight Development QA and M10 Revision Contracts

The active M9 gate is a bounded personal-project development review: it combines the existing deterministic validator surface with direct current-coding-agent inspection of five representative M6/M7/M8.2 lesson packets. It records `M9 DEVELOPMENT: PASS` only when the automated commands pass, every packet is inspected, no blocking sampled defect remains, and no human/release/provider-authentication/live-AI claim is fabricated. Live AI review is `NOT_RUN` when unavailable. This result leaves all generated content `UNREVIEWED`, is not a M6/M7/M8.2 authority change, and does not authorize M10 or M11.

The retained M9 v2 selection, AI-review, runner, batch, and verification contracts remain historical provider-neutral infrastructure; they are not required for the active lightweight M9 gate. Existing M10 records likewise remain immutable historical evidence and are not modified or started by M9 lightweight development QA.

## Core Models

### Skill

A broad capability area.

```yaml
Skill:
  id: string              # e.g., "skill_listening", "skill_speaking"
  name: string
  description: string
  cefr_level: CEFR        # introduced at this level
  mnemonic: string?       # optional memorable code
```

### Linguistic Concept

A grammar rule, pronunciation pattern, syntactic structure, or phonological pattern. Grammar and pronunciation are `category` values of this single canonical concept model.

```yaml
LinguisticConcept:
  id: string                      # e.g., "concept_present_simple"
  name: string
  cefr_level: CEFR
  category: string                # "grammar" | "pronunciation" | "syntax" | "phonology"
  description: string
  examples: string[]              # Example sentences
  prerequisites: string[]         # IDs of concepts that must be introduced first
  related_concepts: string[]      # Conceptually linked concepts
  introduced_in: string?          # Lesson ID where first introduced
  reviewed_in: string[]           # Lesson IDs where revisited
  rules: string[]?                # Grammatical or phonetic rules
  provenance: Provenance?         # Required for externally sourced records
```

### Vocabulary Sense

A distinct meaning of a word.

```yaml
VocabularySense:
  id: string                      # e.g., "vocab_en_run_001"
  word: string
  part_of_speech: string          # "noun" | "verb" | "adjective" | ...
  cefr_level: CEFR
  sense_number: integer           # 1, 2, 3, ... (ordering)
  definition: string              # Simple, learner-friendly definition
  definition_l1: string?          # Vietnamese explanation if needed
  example_sentences: string[]     # Contextualized example sentences
  synonyms: string[]              # Other words with similar meanings
  antonyms: string[]              # Words with opposite meanings
  collocations: string[]          # Common phrases (e.g., "run a business", "run a race")
  pronunciation_ipa: string?      # IPA notation
  register: string?               # "formal" | "informal" | "academic" | "colloquial" | "neutral"
  prerequisites: string[]         # Concepts that should be known
  related_senses: string[]        # Other senses of same word
  introduced_in: string?          # Lesson ID
  reviewed_in: string[]           # Lesson IDs
  provenance: Provenance?         # Required for externally sourced records
```

### Lexical Chunk

A fixed or semi-fixed expression.

```yaml
LexicalChunk:
  id: string                      # e.g., "chunk_how_are_you"
  chunk_text: string              # "How are you?"
  type: string                    # "phrasal_verb" | "idiom" | "collocation" | "fixed_phrase"
  cefr_level: CEFR
  meaning: string
  meaning_l1: string?
  contexts: string[]              # Situations where used
  related_chunks: string[]        # Similar or variant chunks
  prerequisite_vocabulary: string[]  # Vocabulary IDs needed
  introduced_in: string?
  reviewed_in: string[]
  source_id: string?
```

### Communicative Function

A communicative task or intent.

```yaml
CommunicativeFunction:
  id: string                      # e.g., "func_greeting", "func_request_help"
  name: string
  description: string             # What the learner can do
  cefr_level: CEFR
  example_utterances: string[]    # How to express this function
  example_responses: string[]     # Expected responses
  vocabulary_needed: string[]     # Vocabulary IDs
  grammar_needed: string[]        # Concept IDs
  pragmatic_notes: string?        # Cultural/contextual notes
  introduced_in: string?
  reviewed_in: string[]
```

### Generation Metadata

The required audit metadata on M0 generated records (lessons, exercises, and AI practice prompts).

```yaml
GenerationMetadata:
  generator: string
  generator_version: string
  model: string?                  # When known
  prompt_version: string
  generated_at: datetime
  curriculum_version: string
  qa_status: ContentQaStatus
  qa_notes: string?
```

### Provenance

The metadata required whenever an M0 concept or vocabulary sense is externally sourced.

```yaml
Provenance:
  source_id: string
  source_name: string
  source_url: uri
  source_record_id: string
  retrieved_at: datetime
  retrieved_by: string
  license: string
  attribution: string
  content_hash: sha256
  ingestion_version: string
```

### Lesson

A unit of instruction.

```yaml
Lesson:
  id: string                      # e.g., "A1-U01-L01"
  title: string
  unit_id: string                 # Parent unit
  lesson_number: integer          # Sequence within unit
  cefr_level: CEFR
  duration_minutes: integer       # Estimated time
  objectives: string[]            # What learner will learn
  vocabulary_introduced: string[] # Vocabulary sense IDs
  grammar_introduced: string[]    # Concept IDs
  vocabulary_reviewed: string[]   # Previously seen vocabulary
  grammar_reviewed: string[]      # Previously seen concepts
  communicative_functions: string[] # Function IDs
  prerequisites: string[]         # Lesson IDs that should precede
  content_sections: ContentSection[]
  exercises: string[]             # Exercise IDs
  generation_metadata: GenerationMetadata # Generator and QA audit fields
```

### ContentSection

A subsection within a lesson (e.g., "Vocabulary", "Grammar Explanation", "Dialogue").

```yaml
ContentSection:
  id: string
  section_type: string            # "vocabulary" | "grammar" | "listening" | "reading" | "dialogue" | "explanation"
  title: string
  body_text: string               # Markdown or plain text
  embedded_examples: string[]     # Concept/vocabulary IDs referenced
```

### Exercise

A practice activity.

```yaml
Exercise:
  id: string                      # e.g., "ex_A1-U01-L01_001"
  lesson_id: string
  title: string
  exercise_type: string           # "multiple_choice" | "fill_blank" | "listening" | "speaking" | "writing" | "matching" | "free_response"
  cefr_level: CEFR
  difficulty: string              # "easy" | "medium" | "hard"
  prompt_or_stimulus: string       # Instructions and content
  test_vocabulary: string[]       # Vocabulary IDs being tested
  test_grammar: string[]          # Concept IDs being tested
  answer_key: AnswerKey
  hints: string[]?
  time_limit_seconds: integer?
  generation_metadata: GenerationMetadata # Generator and QA audit fields
```

### AnswerKey

Defines correct answers for an exercise.

```yaml
AnswerKey:
  answers: Answer[]               # One or more answers; at least one is primary
  scoring_rubric: string?         # How answers are scored
  
Answer:
  answer_id: string
  answer_text: string             # The correct answer or acceptable variant
  explanation: string             # Why this is correct
  explanation_l1: string?         # Vietnamese explanation
  is_primary: boolean             # True for the best answer
```

### Assessment

A test or quiz.

```yaml
Assessment:
  id: string                      # e.g., "placement_test_v1"
  name: string
  assessment_type: string         # "placement" | "progress" | "unit_test" | "level_test"
  target_cefr: CEFR or CEFR[]     # What level(s) this assesses
  exercises: string[]             # Exercise IDs in this assessment
  passing_threshold: float        # e.g., 0.75 for 75%
  time_limit_seconds: integer?
  source_id: string?
  created_at: datetime
  qa_status: string
```

### Review

A spaced-repetition review session.

```yaml
Review:
  id: string
  vocabulary_to_review: string[]  # Vocabulary sense IDs
  grammar_to_review: string[]     # Concept IDs
  due_date: date
  difficulty_adjustment: float    # e.g., 1.2 = 20% harder
  review_count: integer           # How many times reviewed
```

### AI Practice Prompt

A template for generating AI-led practice conversations.

```yaml
AIPracticePrompt:
  id: string                      # e.g., "prompt_listening_001"
  prompt_type: string             # "listening" | "speaking" | "pronunciation" | "writing_tutor"
  cefr_level: CEFR
  target_vocabulary: string[]     # Vocabulary IDs to practice
  target_grammar: string[]        # Concept IDs to practice
  communicative_goal: string      # What the learner should accomplish
  prompt_template: string         # Templatized prompt for Claude/other models
  prompt_variables: string[]      # {{variables}} to substitute
  system_role: string             # Role of AI (teacher, conversational partner, etc.)
  evaluation_criteria: string[]   # How to evaluate learner output
  generation_metadata: GenerationMetadata # Generator and QA audit fields
```

### Media

Attached media (audio, images, video).

```yaml
Media:
  id: string
  media_type: string              # "image" | "audio" | "video" | "document"
  url: string                     # Local path or URL
  mime_type: string               # "image/png", "audio/mp3", etc.
  alt_text: string?               # Accessibility text
  transcript: string?             # For audio/video
  source_id: string?              # If from external source
  created_at: datetime
  size_bytes: integer
```

---

## Curriculum Graph

The curriculum is represented as a directed acyclic graph (DAG):

- **Nodes**: lessons, concepts, vocabulary
- **Edges**: prerequisites, concepts introduced/reviewed in lessons

This graph ensures:

- Lessons only depend on previously introduced concepts
- Vocabulary builds progressively
- Grammar complexity increases gradually
- Review spirals are explicit

Graph validation prevents:

- Circular dependencies
- Missing prerequisites
- Lessons introducing concepts out of order
- Vocabulary misalignment

---

## Deterministic IDs

All IDs are deterministic and reproducible.

### ID Patterns

- **Concept**: `concept_{snake_case_name}`
  - Example: `concept_present_simple`, `concept_wh_questions`

- **Vocabulary**: `vocab_{language_code}_{word}_{sense_number}`
  - Example: `vocab_en_run_001`, `vocab_en_run_002`

- **Lesson**: `{CEFR}-{UNIT}-{LESSON}`
  - Example: `A1-U01-L01`, `B2-U04-L03`

- **Exercise**: `ex_{CEFR}-{UNIT}-{LESSON}_{EXERCISE_NUMBER}`
  - Example: `ex_A1-U01-L01_001`, `ex_B1-U02-L01_002`

- **Assessment**: `assess_{TYPE}_{VERSION}`
  - Example: `assess_placement_v1`, `assess_unit_test_A1_01`

IDs are stable across regenerations of the same content.

---

## JSON Schema

The six core M0 models have corresponding JSON Schema definitions in `schemas/`. Future models receive schemas in their designated implementation milestones.

Core schemas are `source.schema.json`, `concept.schema.json`, `vocabulary-sense.schema.json`, `lesson.schema.json`, `exercise.schema.json`, and `ai-practice-prompt.schema.json`; common definitions are in `common.schema.json`.

Validation is performed at ingestion, generation, and storage.

---

## Versioning

Schemas are versioned: `schema_version: "1.0"`

Breaking changes increment the major version.

Curriculum using schema v1.0 must still load if structure is backward compatible.

---

## Summary

This schema framework ensures:

1. **Explicitness**: no hidden dependencies or assumptions
2. **Auditability**: every piece traced to source or generator
3. **Testability**: schema validity is machine-checkable
4. **Reproducibility**: deterministic IDs and structures
5. **Extensibility**: new fields can be added without breaking existing tools
