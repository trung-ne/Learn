# GIAI ĐOẠN 14 — M6: LESSON GENERATOR

## Objective

Build a constrained, reproducible lesson-generation pipeline. M6 consumes independently loaded and hash-bound M5 artifacts, an independent authorization, the source registry, and a bounded lesson request, then produces schema-valid lesson JSON. The request is never its own authority. The backend must never invent identity, scope, level, prerequisites, metadata, or approval status; it returns content sections only and orchestration injects all trusted fields.

M6 generates lesson content only. Do not generate exercises, assessments, AI practice prompts, or web/mobile UI; those belong to later milestones.

## Inputs

The generator must receive a machine-readable generation request containing:

1. **Lesson specification** from `curriculum/structure.json`:
   - lesson ID and title
   - target internal tier
   - objectives
   - grammar references
   - vocabulary references
   - communicative-function references
   - pronunciation references
   - lesson prerequisites and review scope
2. **Concept graph** from `curriculum/prerequisite_graph.json`:
   - prerequisite edges
   - introduction edges
   - review edges
   - resolved taxonomy records and their prerequisite closure
3. **Allowed vocabulary**:
   - previously introduced vocabulary senses
   - bounded target vocabulary senses explicitly allocated to this lesson
   - complete IDs and definitions from approved/validated records
4. **Previous knowledge**:
   - concepts and vocabulary introduced before the lesson
   - prerequisite lessons already completed
   - explicitly allowed review material
5. **Generation constraints**:
   - target CEFR tier
   - allowed grammar concept IDs
   - allowed vocabulary-sense IDs
   - allowed function and pronunciation IDs
   - forbidden grammar/features/lexical items
   - maximum content sizes
   - generator, model, prompt, curriculum, and schema versions

Inputs must be loaded and validated independently before generation. The structure, graph, coverage, taxonomy, source registry, and authorization hashes must match the request pins. Graph context and prerequisite closure must be derived from the loaded M5 bundle, not trusted from request declarations. Missing, contradictory, unauthorized, stale, or unresolved references must fail closed; the generator must not silently repair them.

## Constraint example

For an `A1.1` lesson, a request may specify:

```yaml
target_cefr: A1.1
allowed_grammar:
  - concept_be_present_affirmative
  - concept_subject_pronouns
allowed_vocabulary:
  - known vocabulary from previous lessons
  - explicitly allocated target senses
forbidden:
  - B1 grammar
  - unknown idioms
  - advanced phrasal verbs
```

The implementation must use taxonomy IDs rather than relying on names or the model's self-declared level.

## Generator contract

Create a typed, deterministic interface such as:

```python
class LessonGenerator:
    def generate(self, request: LessonGenerationRequest) -> LessonGenerationResult:
        ...
```

The generator must:

- validate the lesson spec, graph, taxonomy, permissions, and constraints before calling a model;
- pass constraints explicitly in the generation prompt;
- use only allowed grammar, vocabulary, functions, and pronunciation targets;
- distinguish introduction from review;
- preserve prerequisite ordering;
- reject output that contains forbidden or unreferenced content;
- validate generated output against `schemas/lesson.schema.json`;
- preserve all required `generation_metadata`;
- set generated content to `UNREVIEWED`, never `APPROVED` automatically;
- produce deterministic request IDs and audit metadata;
- support a mock/offline generator for tests without network access;
- separate generation from review/QA whenever practical.

No model output may override a curriculum constraint. If the model produces an out-of-scope feature, the result must be rejected or routed to revision rather than silently accepted.

## Output

The provider backend outputs only a JSON object containing `content_sections`. The orchestration layer constructs the final lesson and injects all identity, curriculum references, versions, timestamp, hashes, and `generation_metadata`; backend-supplied trusted fields are rejected.

- deterministic lesson ID matching the lesson specification;
- title, unit, lesson number, and internal CEFR tier;
- objectives copied from or faithfully structured from the lesson specification;
- only permitted vocabulary and grammar references;
- communicative-function and pronunciation references from the allowed sets;
- prerequisite lesson IDs matching the graph;
- review references only to previously introduced material;
- generated content sections with bounded, learner-appropriate text;
- complete `generation_metadata`:
  - generator
  - generator version
  - model when known
  - prompt version
  - generated timestamp
  - curriculum version
  - `qa_status: UNREVIEWED`
  - QA notes

Generated text must be original project output. Do not copy restricted source wording, textbook passages, dialogues, readings, or media transcripts. External material may be used only according to registered source permissions and provenance policy.

## Pre-generation validation

Before generation, reject requests when:

- the lesson ID or tier does not match the curriculum outline;
- a required taxonomy reference is missing or has the wrong type;
- a taxonomy record is not approved/authorized for generation;
- a prerequisite is absent, cyclic, or not earlier;
- allowed vocabulary includes an unknown or unintroduced sense;
- forbidden features overlap with allowed features;
- target vocabulary exceeds the configured bound;
- the request uses raw, quarantined, unauthorized, or unvalidated records;
- the request asks for M7 exercises, assessments, or M8 prompts.

## Post-generation validation

Validate at minimum:

1. JSON Schema validity.
2. Deterministic lesson identity and parent links.
3. CEFR/tier consistency.
4. Exact subset compliance for grammar, vocabulary, functions, and pronunciation references.
5. No forbidden IDs, levels, idioms, or advanced structures.
6. Every referenced concept and sense is allowed and resolvable.
7. Prerequisites and review targets are earlier.
8. Objectives are represented without adding unrelated objectives.
9. Content sections are nonempty, bounded, and suitable for the target tier.
10. No exercises, answer keys, assessments, AI prompts, or unsupported media content.
11. Generation metadata is complete and status is `UNREVIEWED`.
12. Provenance and copyright checks pass for any externally sourced input.

The validator must report all violations deterministically and must not publish invalid output.

## QA boundary

M6 generation is not approval. The pipeline must produce a validation/audit report containing:

- request ID and lesson ID;
- input hashes and versions;
- constraints applied;
- model/generator metadata;
- schema result;
- constraint result;
- prerequisite and CEFR result;
- copyright/provenance result;
- output hash;
- `qa_status` and unresolved issues.

Independent QA remains required before any development or release promotion. Automated M6 validation never makes a lesson `APPROVED`. Development promotion requires separate AI linguistic and pedagogical reviews and a verified hash-bound batch; it is not human or release approval. Human/release promotion requires its separate verified human workflow.

## Reproducibility and safety

- Use pinned input snapshots, prompt version, model/provider identifier, parameters, and seed when supported.
- Serialize canonical JSON and sort references deterministically.
- Do not claim byte-for-byte reproducibility when the model does not support deterministic generation.
- Never make network calls in offline tests.
- Never download data automatically as part of lesson generation.
- Never weaken constraints to make generation succeed.
- Store rejected outputs and reasons in an auditable revision/error record; do not treat them as approved lessons.

## Tests

Add offline tests for:

- valid constrained generation with a mock generator;
- lesson ID, tier, and parent mismatch;
- missing or wrong-type taxonomy references;
- unauthorized or unapproved vocabulary/concepts;
- unknown, unintroduced, and over-limit vocabulary;
- forbidden B1 grammar or advanced lexical features in A1 requests;
- prerequisite and review ordering;
- model output containing out-of-scope references;
- schema-invalid output;
- missing generation metadata;
- accidental `APPROVED` status;
- exercise/assessment/prompt leakage;
- deterministic request and output validation reports;
- rejected generation with no partial publication;
- offline CLI success and nonzero failure behavior.

Use authored fixtures only. Do not call a live model or download external data in tests.

## Explicit exclusions

M6 does not generate exercises, answer keys, assessments, AI practice prompts, web/mobile UI, spaced-repetition scheduling, bulk datasets, or full A1–C2 content. It does not bypass source permissions, approve its own output, or replace independent QA.

## Acceptance criteria

1. Lesson generation accepts explicit lesson, graph, vocabulary, previous-knowledge, and constraint inputs.
2. Constraints are enforced before and after model generation.
3. Generated output conforms to the existing lesson schema.
4. Only allowed grammar, vocabulary, functions, and pronunciation are used.
5. Forbidden advanced content is rejected.
6. Prerequisites and review scope are respected.
7. Provenance, copyright, versions, hashes, and generation metadata are retained.
8. Output remains `UNREVIEWED` until independent QA.
9. Invalid output is rejected without partial publication.
10. Offline tests and CLI behavior pass.
11. M7 and later milestones are not started.

Run the full applicable test suite, inspect generated output and audit reports, inspect the diff, verify every acceptance criterion, report PASS/FAIL and unresolved issues, then STOP.
