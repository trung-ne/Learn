# Curriculum Schema — English Master

## Overview

This document defines the data models and schemas for curriculum content in English Master.

All schemas support JSON serialization and machine-readable validation.

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

---

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

A grammar rule, pronunciation pattern, or syntactic structure.

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
```

### Vocabulary Sense

A distinct meaning of a word.

```yaml
VocabularySense:
  id: string                      # e.g., "sense_run_001"
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
  etymology: string?              # Word origin / etymology
  register: string?               # "formal" | "informal" | "academic" | "colloquial"
  prerequisites: string[]         # Concepts that should be known
  related_senses: string[]        # Other senses of same word
  introduced_in: string?          # Lesson ID
  reviewed_in: string[]           # Lesson IDs
  source_id: string?              # Source of this entry
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
  source_id: string?              # If based on external material
  created_at: datetime
  generated_by: string?
  qa_status: string               # "UNREVIEWED" | "APPROVED" | "REJECTED"
```

### ContentSection

A subsection within a lesson (e.g., "Vocabulary", "Grammar Explanation", "Dialogue").

```yaml
ContentSection:
  id: string
  section_type: string            # "vocabulary" | "grammar" | "listening" | "reading" | "dialogue" | "explanation"
  title: string
  body_text: string               # Markdown or plain text
  media: Media[]?                 # Audio, images, videos
  embedded_examples: string[]     # Concept/vocabulary IDs referenced
```

### Exercise

A practice activity.

```yaml
Exercise:
  id: string                      # e.g., "ex_A1_001"
  lesson_id: string
  title: string
  exercise_type: string           # "multiple_choice" | "fill_blank" | "listening" | "speaking" | "writing" | "matching" | "free_response"
  cefr_level: CEFR
  difficulty: string              # "easy" | "medium" | "hard"
  prompt_or_stimulus: string       # Instructions and content
  media: Media[]?                 # Images, audio, video
  test_vocabulary: string[]       # Vocabulary IDs being tested
  test_grammar: string[]          # Concept IDs being tested
  answer_key: AnswerKey
  hints: string[]?
  time_limit_seconds: integer?
  source_id: string?
  created_at: datetime
  generated_by: string?
  qa_status: string
```

### AnswerKey

Defines correct answers for an exercise.

```yaml
AnswerKey:
  answers: Answer[]               # One or more possible answers
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
  model_version: string?          # e.g., "claude-3-5-sonnet"
  created_at: datetime
  qa_status: string
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

- **Lesson**: `{CEFR}_{UNIT}_{LESSON}`
  - Example: `A1_U01_L01`, `B2_U04_L03`

- **Exercise**: `ex_{CEFR}_{UNIT}_{LESSON}_{EXERCISE_NUMBER}`
  - Example: `ex_A1_U01_L01_001`, `ex_B1_U02_L01_002`

- **Assessment**: `assess_{TYPE}_{VERSION}`
  - Example: `assess_placement_v1`, `assess_unit_test_A1_01`

IDs are stable across regenerations of the same content.

---

## JSON Schema

All models should have corresponding JSON Schema definitions in `schemas/`.

Example: `schemas/vocabulary_sense.json`

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
