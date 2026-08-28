# QA Specification — English Master

## Overview

This document defines quality assurance processes and validation rules for English Master.

All generated content must pass applicable QA before approval.

---

## QA Categories

### 1. Schema Validation

**Purpose**: Ensure all data conforms to defined schemas.

**Automated**: YES

**Scope**: Every ingested and generated record

**Process**:

1. Load JSON/YAML record
2. Validate against corresponding JSON Schema
3. Check all required fields present
4. Check all field types correct
5. Check all enum values valid
6. Check string length limits
7. Report schema errors

**Pass Criteria**: Schema is valid

**Failure**: Record is rejected or quarantined

---

### 2. CEFR Validation

**Purpose**: Ensure CEFR level assignments are appropriate.

**Automated**: PARTIAL

**Scope**: All vocabulary, grammar concepts, exercises, lessons

**Process**:

1. Check CEFR level is valid (A1.1 through C2.2)
2. If vocabulary: verify word is typical for that level
3. If grammar: verify structure is typical for that level
4. If exercise: verify difficulty matches declared CEFR
5. Manual review for edge cases

**Pass Criteria**:

- Level is one of defined CEFR levels
- Level assignment is reasonable for the content

**Failure**: Content is downgraded, revised, or rejected

**Example**: Assigning "photosynthesis" to A1 fails (too technical for beginners)

---

### 3. Prerequisite Validation

**Purpose**: Ensure lessons only depend on previously introduced content.

**Automated**: YES

**Scope**: Lessons, exercises, assessments

**Process**:

1. Build curriculum DAG from lesson prerequisites
2. For each lesson, find all vocabulary and grammar needed
3. Check that all prerequisites are introduced in earlier lessons
4. Detect circular dependencies
5. Report missing prerequisites

**Pass Criteria**:

- All prerequisites introduced before use
- No circular dependencies
- DAG is acyclic

**Failure**: Lesson is blocked or prerequisite order is reordered

---

### 4. Grammar Validation

**Purpose**: Ensure grammatical content is accurate.

**Automated**: PARTIAL

**Scope**: Grammar concepts, example sentences, exercises

**Process**:

1. Collect all grammatical rules stated
2. Create example test sentences following and violating rules
3. Check examples follow rule
4. Check violations are actually incorrect
5. Manual linguist review for complex structures
6. Check consistency with stated exceptions

**Pass Criteria**:

- All examples follow stated rules
- Counter-examples actually violate rules
- Exceptions are documented

**Failure**: Content is revised by linguist

---

### 5. Lexical Validation

**Purpose**: Ensure vocabulary definitions and examples are accurate.

**Automated**: PARTIAL

**Scope**: Vocabulary senses, definitions, example sentences, collocations

**Process**:

1. Check definition is accurate and learner-friendly
2. Verify example sentences use word in that sense
3. Check synonyms are truly synonymous
4. Check antonyms are truly opposite
5. Verify collocations are natural
6. Cross-reference with authoritative dictionaries

**Pass Criteria**:

- Definitions are clear and accurate
- Examples demonstrate the sense correctly
- Synonyms/antonyms/collocations are correct
- Usage is natural

**Failure**: Content is revised

---

### 6. Answer Validation

**Purpose**: Ensure exercise answers are correct.

**Automated**: PARTIAL

**Scope**: Multiple-choice options, fill-in-the-blank answers, matching pairs

**Process**:

1. Check correct answer is objectively correct
2. Check distractors are plausible but incorrect
3. Check there is only one correct answer (unless multi-answer)
4. For fill-blank: check answer fits grammatically and semantically
5. For matching: check pairs are correctly matched
6. Manual review for subjective exercises (writing, speaking)

**Pass Criteria**:

- Correct answer is unambiguous
- Distractors are plausible but wrong
- No irrelevant distractors
- Answer key is complete

**Failure**: Exercise is revised

---

### 7. Ambiguity Detection

**Purpose**: Flag content that could be misinterpreted.

**Automated**: PARTIAL

**Scope**: Prompts, instructions, exercises, vocabulary definitions

**Process**:

1. Read content as if learner
2. Identify points of potential confusion
3. Check if instructions are clear
4. Check if context disambiguates meaning
5. Manual review for edge cases

**Pass Criteria**:

- Content is unambiguous
- Instructions are clear
- Context is sufficient

**Failure**: Content is clarified (emphasis, rephrasing, examples)

---

### 8. Duplicate Detection

**Purpose**: Prevent redundant or near-identical content.

**Automated**: YES

**Scope**: Vocabulary entries, exercises, lessons

**Process**:

1. Compute content hashes
2. Check for identical entries
3. Compare semantically similar entries
4. Flag near-duplicates
5. Manual review for true duplicates

**Pass Criteria**:

- No exact duplicates
- Similar content has distinct purpose or level
- Pronunciation variants are marked as variants

**Failure**: Duplicates are merged or one is removed

---

### 9. Provenance Validation

**Purpose**: Ensure provenance is complete and traceable.

**Automated**: YES

**Scope**: All ingested external content

**Process**:

1. Check provenance record is complete
2. Verify source_id matches registered source
3. Verify license is documented
4. Verify attribution is present
5. Verify content_hash matches actual content
6. Check retrievability: can source be re-accessed?

**Pass Criteria**:

- All provenance fields present
- Source is registered
- License is clear
- Attribution is complete

**Failure**: Content is quarantined until provenance is fixed

---

### 10. Copyright Validation

**Purpose**: Ensure all content can be legally used.

**Automated**: PARTIAL

**Scope**: All content, especially ingested external content

**Process**:

1. Check source is registered
2. Check source license is in APPROVED list
3. Check if copyright holder was bypassed
4. Check if content is within fair-use scope
5. Check attribution is proper
6. Legal review for edge cases

**Pass Criteria**:

- Source is APPROVED
- License permits intended use
- Attribution is complete
- No unauthorized bypassing

**Failure**: Content is removed or quarantined

---

### 11. Language Quality Review

**Purpose**: Ensure content is well-written and pedagogically sound.

**Automated**: NO

**Scope**: Explanations, instructions, example sentences, feedback

**Process**:

1. Qualified human reviewer (native or near-native speaker)
2. Read content for clarity, naturalness, pedagogy
3. Check for typos, grammar errors
4. Check for unclear explanations
5. Suggest improvements
6. Approve or request revision

**Pass Criteria**:

- No typos or grammatical errors
- Explanations are clear
- Language is natural
- Pedagogy is sound

**Failure**: Content is revised

---

## QA Workflow

### For Ingested Content

```
Ingest → Schema Validate → Provenance Check → Copyright Check → 
  → Linguistic Validate → Deduplicate → Approve or Quarantine
```

### For Generated Content

```
Generate → Schema Validate → CEFR Check → Prerequisite Check → 
  → Grammar/Lexical Check → Uniqueness Check → Language Quality Review → 
  → Approve or Reject
```

---

## QA Status Levels

- **UNREVIEWED**: Generated but not yet reviewed
- **IN_REVIEW**: Currently being reviewed
- **APPROVED**: Passed all applicable QA
- **NEEDS_REVISION**: Failed QA; requires changes
- **REJECTED**: Failed QA; not salvageable

---

## QA Responsibility

### Generator vs. Reviewer

When practical, generator and reviewer are different processes:

- **Generator**: Creates content
- **Reviewer**: Validates content independently

This separation reduces blind spots.

For critical content (lesson explanations, assessments), reviewer may be a human educator.

---

## QA Escalation

### Ambiguous Cases

Cases that cannot be automatically decided:

1. Flagged for manual review
2. Assigned to subject-matter expert
3. Forwarded to pedagogical committee if needed
4. Decision is documented

### Criteria Changes

If QA criteria change:

- Existing approved content is not retroactively rejected
- New content uses updated criteria
- Grandfathering rules are explicit

---

## QA Auditability

Every QA decision is logged:

```json
{
  "content_id": "ex_A1_001",
  "qa_checks_performed": ["schema", "cefr", "grammar", "answers"],
  "qa_status": "APPROVED",
  "qa_timestamp": "2026-08-28T12:00:00Z",
  "qa_reviewer": "auto_schema_validator",
  "qa_notes": "All checks passed",
  "qa_issues_found": []
}
```

Audit trail is never deleted.

---

## Summary

QA ensures:

1. **Technical Correctness**: schema and logic validity
2. **Pedagogical Soundness**: appropriate for level
3. **Linguistic Accuracy**: grammar and vocabulary correct
4. **Legal Compliance**: proper copyright and licensing
5. **Transparency**: all decisions documented
6. **Reproducibility**: QA can be re-run and should produce same result

QA is not a gate-keeper; it is a feedback loop improving content quality.
