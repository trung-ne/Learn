# GIAI ĐOẠN 15 — M7: EXERCISE GENERATOR

## Objective

Build a constrained exercise-generation pipeline driven by approved lesson JSON. Generate varied practice activities only when they serve the lesson objectives and can pass independent QA. Exercise count is a planning ceiling, not a success metric: correctness, unambiguous answers, level alignment, pedagogical value, and auditability take priority.

M7 consumes lessons from M6 and produces exercises. Do not generate AI practice prompts, web/mobile UI, spaced-repetition scheduling, or later-milestone content.

## Inputs

The generator must receive a validated machine-readable request containing:

1. An approved lesson snapshot and its exact hash.
2. Lesson objectives, CEFR tier, grammar, vocabulary-sense, function, pronunciation, and skill targets.
3. The curriculum graph and prerequisite/previous-knowledge context.
4. Allowed target and review references from the lesson.
5. Exercise constraints:
   - permitted exercise types;
   - requested maximum counts per type;
   - difficulty distribution;
   - language/translation direction where applicable;
   - maximum prompt, option, and stimulus sizes;
   - forbidden content and later-level references.
6. Generation metadata:
   - generator/version;
   - model when known;
   - prompt version;
   - curriculum and schema versions;
   - deterministic seed/parameters when supported.

Reject missing, stale, unapproved, contradictory, or unauthorized inputs before invoking a generator.

## Exercise mix

A lesson may request up to the following authored defaults:

- 8 multiple-choice questions;
- 8 fill-in-the-blank items;
- 5 matching items;
- 5 ordering items;
- 5 error-correction items;
- 5 sentence-construction items;
- 5 translation items;
- 1 reading task;
- 1 listening task;
- 1 speaking task;
- 1 writing task.

These are maximum planning values, not mandatory quotas. The generator should omit a type when it does not meaningfully practice a stated objective, lacks a defensible answer key, or would reduce clarity. A smaller high-quality set is preferable to padded repetition.

## Generator contract

Provide a typed interface such as:

```python
class ExerciseGenerator:
    def generate(self, request: ExerciseGenerationRequest) -> ExerciseGenerationResult:
        ...
```

The generator must:

- use only the lesson's allowed grammar, vocabulary senses, functions, pronunciation, and skills;
- distinguish target practice from review practice;
- preserve prerequisite ordering and CEFR constraints;
- create deterministic exercise IDs tied to the lesson and sequence;
- produce complete answer keys and scoring guidance where objectively possible;
- mark subjective speaking/writing tasks for rubric-based human/independent review;
- retain provenance and generation metadata;
- set generated content to `UNREVIEWED`, never `APPROVED` automatically;
- support an offline deterministic mock backend for tests;
- never invent unsupported vocabulary, idioms, facts, source text, or advanced grammar.

No generator response may override lesson constraints. Out-of-scope output must be rejected or sent to revision.

## Exercise-specific requirements

### Multiple choice

- Exactly one primary answer unless explicitly declared multi-answer.
- Distractors must be plausible, relevant, and objectively wrong.
- Do not use trick questions or ambiguous contexts.
- Option order and answer IDs must be deterministic.

### Fill in the blank

- Context must make the expected answer clear.
- Acceptable variants must be explicitly listed.
- Check grammar, spelling policy, morphology, and semantic fit.

### Matching

- Every item has one unambiguous match.
- No duplicate labels or accidental multiple matches.
- Answer mapping must be complete and deterministic.

### Ordering

- The ordering principle must be stated: chronology, syntax, procedure, discourse, or another objective rule.
- At least one valid order must be demonstrable.

### Error correction

- The stimulus contains a deliberate, target-relevant error.
- The answer identifies the error and supplies the correction.
- Do not mark acceptable variation as an error.

### Sentence construction

- Required words and target structure are explicit.
- Acceptable variants are reviewed rather than assuming one word order is always unique.

### Translation

- Direction, register, and expected meaning are explicit.
- Preserve meaning rather than enforcing an unjustified word-for-word answer.
- Vietnamese-English tasks must account for acceptable natural alternatives.

### Reading and listening

- Stimulus, questions, answer key, and target references are linked.
- Copyright and provenance checks apply to every external stimulus.
- Do not copy restricted passages or transcripts.
- Listening tasks must not require unavailable media; an authored offline fixture may use a declared transcript only for tests.

### Speaking and writing

- Prompt specifies communicative goal, constraints, and expected output.
- Use a clear rubric rather than pretending subjective output has one exact answer.
- Do not generate later-milestone AI tutoring or evaluation prompts.

## QA pipeline

Every generated exercise passes independent validation stages:

1. **Schema validation** — required fields, types, IDs, enums, answer-key shape.
2. **Reference validation** — lesson, taxonomy, vocabulary, grammar, and graph references resolve.
3. **CEFR validation** — declared level and difficulty are appropriate; self-declared model labels are not trusted without independent checks.
4. **Prerequisite validation** — all tested material is introduced or explicitly reviewed earlier.
5. **Answer validation** — primary answers are correct, complete, and objectively defensible.
6. **Distractor validation** — distractors are plausible but not accidentally correct.
7. **Ambiguity detection** — context, instructions, and expected responses are clear.
8. **Grammar/lexical validation** — examples use the intended sense and structure naturally.
9. **Duplicate detection** — no exact or near-identical exercise padding without a distinct purpose.
10. **Difficulty and workload validation** — avoid excessive repetition, impossible jumps, and unreasonable response demands.
11. **Copyright/provenance validation** — external stimuli use registered approved sources with required attribution.
12. **Language-quality review** — independent human or separate reviewer checks naturalness and pedagogy.

Generator and reviewer should be separate passes whenever practical. Failure at any required gate prevents publication.

## Audit and status

Each exercise and generation run must retain:

- deterministic exercise and request IDs;
- lesson ID and exact input hashes;
- target references and constraints applied;
- generator/model/prompt/curriculum/schema versions;
- generation timestamp and parameters;
- QA checks, reviewer, timestamp, issues, and revisions;
- output hash and provenance/copyright decisions;
- content status `UNREVIEWED`, `IN_REVIEW`, `NEEDS_REVISION`, `REVISION_SUBMITTED`, `APPROVED`, `REJECTED`, or `ARCHIVED` as applicable.

M7 generation must never mark exercises `APPROVED` without the independent QA workflow.

## Failure handling

- Reject invalid output atomically; do not publish partial exercise sets.
- Record every failure and its stage in an auditable error/rejection record.
- Preserve candidate output only in the restricted review/rejection area when policy allows.
- Regeneration must use a new deterministic revision identity while retaining the prior audit trail.
- Never lower constraints merely to reach a requested count.

## Tests

Use authored offline fixtures and a deterministic mock backend. Test:

- generation from a valid approved lesson;
- quality-first omission of unnecessary exercise types;
- all supported exercise types and their contracts;
- deterministic IDs, ordering, hashes, and reruns;
- missing/stale/unapproved lesson snapshots;
- unknown or unauthorized references;
- wrong CEFR, unintroduced prerequisites, and forbidden advanced material;
- ambiguous prompts, multiple correct MCQ answers, invalid distractors, incomplete mappings, and missing answer keys;
- fill-blank variants, translation alternatives, subjective rubrics, and ordering ambiguity;
- duplicate exercises and padded repetition;
- copyright/provenance failures for reading/listening stimuli;
- AI-practice-prompt and later-milestone leakage and unsupported media;
- schema-invalid backend output;
- atomic rejection and no partial publication;
- independent QA status and audit metadata;
- offline CLI success and nonzero failure behavior.

No live model, network request, bulk download, or external corpus is permitted in tests.

## Explicit exclusions

M7 does not generate AI practice prompts, speaking/pronunciation evaluation agents, web/mobile UI, spaced-repetition schedules, placement/level assessments beyond exercise records, or later-milestone artifacts.

## Acceptance criteria

1. Exercise generation consumes validated lesson constraints rather than inventing scope.
2. Supported exercise types have strict type-specific contracts.
3. Exercise count is treated as a bounded option, not the primary success criterion.
4. Answer correctness and ambiguity checks prevent unsafe publication.
5. CEFR, prerequisite, reference, duplicate, provenance, and copyright checks are auditable.
6. Subjective tasks include usable rubrics and remain reviewable.
7. Invalid or low-quality output is rejected without partial publication.
8. All generated content remains `UNREVIEWED` until independent QA.
9. Offline tests and CLI checks pass.
10. Later milestones are not started.

Run the full applicable test suite, inspect exercises and QA reports, inspect the diff, verify every acceptance criterion, report PASS/FAIL and unresolved issues, then STOP.
