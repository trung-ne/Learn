GIAI ĐOẠN 10 — M2: CEFR TAXONOMY

M2 rất quan trọng.

Chưa crawl corpus.

M2 xây "bộ xương kiến thức".

Tạo:

prompts/M2_CEFR_TAXONOMY.md

Nội dung:

# M2 — CEFR Taxonomy and Linguistic Knowledge Model

## Objective

Create the structured linguistic taxonomy that will govern curriculum generation.

Do NOT generate hundreds of lessons.

Do NOT bulk ingest corpora.

---

# Dimensions

Model at minimum:

CEFR levels

Skills:
- listening
- speaking
- spoken interaction
- reading
- writing
- mediation where useful

Grammar

Vocabulary senses

Collocations

Lexical chunks

Pronunciation

Communicative functions

Topics

Discourse

Pragmatics

Assessment capabilities

---

# CEFR Levels

Support:

A1.1
A1.2
A2.1
A2.2
B1.1
B1.2
B2.1
B2.2
C1.1
C1.2
C2.1
C2.2

These internal subdivisions must not be falsely presented as official CEFR levels.

They are internal curriculum subdivisions.

---

# Concepts

Each linguistic concept requires:

id
type
name
description
minimum_cefr
prerequisites
related_concepts
evidence_or_reference
status

---

# Vocabulary

Vocabulary must support senses.

Do NOT classify only surface words.

Example:

run

may contain multiple senses at different proficiency levels.

Model:

lemma
part_of_speech
sense_id
definition
cefr
collocations
chunks
examples
relationships

---

# Grammar

Represent grammar as concepts and capabilities rather than chapter titles only.

Support dependency relationships.

Example:

past_simple
    ↓
past_continuous
    ↓
narrative_sequence
    ↓
past_perfect

---

# Pronunciation

Create taxonomy for:

phonemes
minimal pairs
syllables
word stress
sentence stress
weak forms
linking
connected speech
rhythm
intonation

---

# Vietnamese Learner Layer

Define schema for Vietnamese learner difficulty annotations.

Possible categories:

articles
tense
plural endings
final consonants
clusters
stress
prepositions
countability
collocations
literal translation

Research claims and pedagogical observations must be distinguishable.

---

# Coverage Matrix

Create a machine-readable coverage matrix showing what categories are expected at each CEFR range.

Do not fabricate precision when authoritative references do not provide it.

Use confidence/evidence metadata where appropriate.

---

# Validation

Implement tests for:

- concept ID uniqueness
- valid CEFR
- valid prerequisite references
- no cycles where cycles are invalid
- valid concept relationships
- vocabulary sense integrity

---

# Prototype

Populate only enough representative concepts to prove the system.

Do NOT attempt to finish every grammar point from A1 to C2 during M2 unless the milestone specification explicitly supports controlled taxonomy population.

Architecture first.

---

# Acceptance

1. taxonomy schemas exist
2. concept graph works
3. prerequisites work
4. vocabulary senses work
5. internal CEFR subdivisions work
6. Vietnamese learner annotations work
7. graph validators work
8. tests pass

Report PASS/FAIL.

Then STOP.