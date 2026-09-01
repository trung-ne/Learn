GIAI ĐOẠN 13 — M5: CURRICULUM GRAPH

Đây là lúc bắt đầu xây curriculum thực sự. Nhưng trước tiên chỉ tạo outline và dependency graph.

# M5 — Curriculum Architecture and Dependency Graph

## Objective

Build a machine-readable curriculum outline for English Master from A1 through C2. Define what is taught, in what order, and where it is reviewed. Do not write full lesson content.

Do NOT write dialogues, readings, listening scripts, exercises, answer keys, assessments, or AI prompts. Do NOT start M6 or later milestones.

## Hierarchy

Represent:

```text
English Master
├── A1
│   ├── A1.1
│   │   ├── Unit 01
│   │   │   ├── A1-U01-L01
│   │   │   ├── A1-U01-L02
│   │   │   ├── A1-U01-L03
│   │   │   └── A1-U01-REV
│   └── A1.2
├── A2
├── B1
├── B2
├── C1
└── C2
```

Support all internal tiers: `A1.1`, `A1.2`, `A2.1`, `A2.2`, `B1.1`, `B1.2`, `B2.1`, `B2.2`, `C1.1`, `C1.2`, `C2.1`, `C2.2`. The `.1` and `.2` values are internal curriculum subdivisions, not official CEFR levels.

Every unit and lesson belongs to exactly one tier and parent level.

## Deterministic IDs

Use stable IDs:

```text
Unit:   A1.1-U01
Lesson: A1-U01-L01
Review: A1-U01-REV
```

Do not use random UUIDs or IDs that change when unrelated content is inserted. Concept, vocabulary-sense, function, and pronunciation references must resolve to M2 taxonomy IDs or explicitly approved compatible records.

## Lesson outline contract

Every lesson outline must specify at least:

```yaml
id: A1-U01-L01
title: Introducing Yourself
unit_id: A1.1-U01
lesson_number: 1
cefr: A1.1
objectives:
  - introduce yourself
  - say your name
  - ask someone's name
grammar:
  - concept_be_present_affirmative
vocabulary:
  - vocab_en_hello_001
  - vocab_en_name_001
functions:
  - func_greeting
  - func_introduction
pronunciation:
  - concept_alphabet_basic
prerequisites: []
review_of: []
lesson_kind: CORE
status: OUTLINE_ONLY
```

Required fields: deterministic ID, title, parent unit, sequence number, internal tier, objectives, grammar references, vocabulary-sense references, communicative-function references, pronunciation references where applicable, lesson prerequisites, reviewed material, lesson kind, and outline status. Objectives describe learner capabilities only; they are not lesson prose.

## Unit and review contract

Every unit specifies deterministic ID, parent level/tier, sequence, title/theme, concise goals, ordered lesson IDs, review node, prerequisites, included skills/dimensions, and outline status.

Review nodes are graph nodes. They must identify earlier lessons or previously introduced concepts, vocabulary senses, functions, and skills. Do not create fake completed lessons to fill gaps; mark intentionally incomplete areas explicitly.

## Curriculum graph

Create an explicit graph:

```json
{
  "nodes": [{"id": "A1-U01-L01", "type": "lesson"}],
  "edges": [{"from": "A1-U01-L01", "to": "A1-U01-L02", "type": "prerequisite"}]
}
```

Distinguish lesson prerequisites, unit ordering, taxonomy prerequisites, introduction edges, review edges, and related/non-ordering links. A related concept is not a prerequisite unless an ordering edge explicitly says so.

Validate that every node/reference exists; every lesson has one parent; every unit has one tier; taxonomy IDs resolve; prerequisites are earlier; self-dependencies and cycles are rejected; review references point to earlier material; cross-tier progression does not skip required prerequisites; and graph serialization/topological ordering is deterministic.

## Sequencing and coverage

Foundational communication must precede dependent communication. Grammar and vocabulary prerequisites must precede use. Pronunciation must progress from foundational sounds toward connected speech and prosody. Distribute listening, speaking, spoken interaction, reading, writing, mediation, grammar, vocabulary senses, collocations, lexical chunks, pronunciation, communicative functions, topics, discourse, pragmatics, and assessment capabilities across the roadmap.

Create machine-readable coverage metadata showing where each dimension is introduced, developed, and reviewed. Record estimates as estimates; do not fabricate unsupported precise counts or hours.

## Governance

Consume M2 taxonomy and only approved/validated data references. Do not use raw, quarantined, or unauthorized records. Preserve source citations where a design decision relies on external evidence, but do not copy restricted source wording or examples. Curriculum outline records are project-authored planning records.

## Schemas and CLI

Create strict schemas for the curriculum manifest, levels/tiers, units, lesson outlines, review nodes, graph nodes/edges, coverage roadmap, and validation report. Reuse the existing offline schema and taxonomy validators.

Provide an offline CLI such as:

```bash
python -m english_master.curriculum_validate curriculum/structure.json
```

It must report schema failures, missing references, invalid IDs, prerequisite violations, cycles, ordering errors, coverage gaps, duplicates, and unresolved reviews, returning nonzero for invalid structure.

## Tests

Test valid and invalid behavior: twelve-tier support; deterministic IDs and topological order; hierarchy/parent links; required outline fields; taxonomy reference resolution; grammar/vocabulary/function/pronunciation links; missing/self/cyclic prerequisites; review-before-introduction; duplicate nodes; prerequisite-versus-related edge distinction; coverage gaps; rejection of full prose/exercise content in outlines; unauthorized dependencies; CLI exit codes; and offline reproducibility.

## Explicit exclusions

M5 does not write full lessons, explanations, dialogues, readings, listening scripts, exercises, answer keys, assessments, AI prompts, web/mobile UI, or spaced repetition. It does not download data, classify CEFR, or implement M6 or later milestones.

## Acceptance

1. A1–C2 hierarchy exists.
2. All twelve internal tiers are represented and labelled correctly.
3. Units, lessons, and reviews have deterministic IDs.
4. Lessons declare tier, objectives, grammar, vocabulary, functions, pronunciation, prerequisites, and review scope.
5. Taxonomy references resolve.
6. The prerequisite graph is acyclic and correctly ordered.
7. Review nodes reference earlier material.
8. Coverage metadata covers required dimensions.
9. Invalid references, cycles, duplicates, and ordering errors fail validation.
10. CLI and tests work offline.
11. No full lesson content is generated.
12. M6 and later milestones are not started.

Run the full applicable tests, inspect the outline and graph and diff, verify every acceptance criterion, report PASS/FAIL and unresolved issues, then STOP.
