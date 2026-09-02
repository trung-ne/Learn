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

---

## M6 Lesson Generation Contracts

M6 adds strict machine-readable contracts for `lesson-generation-authorization`, `lesson-generation-request`, `lesson-generation-audit`, and `lesson-generation-rejection`. An authorization snapshot contains only independently approved records and distinguishes grammar, vocabulary senses, communicative functions, and pronunciation. A request embeds the selected lesson specification, graph context, previous knowledge, exact allowed and forbidden sets, size bounds, pinned versions, backend parameters, and the authorization snapshot. Request and authorization identities are canonical SHA-256 values.

The lesson schema remains backward compatible with M0 fixtures while accepting internal-tier unit IDs and optional explicit function/pronunciation introduction and review arrays. The M6 semantic validator requires these arrays, exact correspondence with the request, canonical ordering, bounded nonempty sections, and `exercises: []`. Audit and rejection records preserve hashes, applied constraints, validation outcomes, unresolved issues, candidate output when rejected after generation, and the non-approval QA boundary. See [LESSON_GENERATION.md](LESSON_GENERATION.md).

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
