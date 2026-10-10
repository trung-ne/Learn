# Writing Module

## Current scope

The Writing Module is an English-only, static projection of exactly 300 current project-authored lesson writing protocols: 50 per A1, A2, B1, B2, C1, and C2 band. Every supplied protocol remains `UNREVIEWED`.

The module provides source-backed task navigation, filters, local learner-authored drafts, and linked learner-authored revisions. Its A1–C2 orientation is application navigation, not a classification of individual tasks, feedback about a learner, CEFR attainment, or a proficiency result.

German has no Writing Module inventory. The module does not generate new tasks, prompts, task categories, rubrics, answers, or examples.

## Feedback boundary

Every projected source protocol has the exact supplied boundary `FEEDBACK_ONLY_NO_REPLACEMENT`.

No evaluator is connected. The correction workspace explicitly shows that feedback is unavailable for:

- Corrections
- Grammar mistakes
- Vocabulary issues
- Naturalness
- Coherence
- Better alternatives
- Explanation

The displayed **Original** is only the learner’s local draft. **Your revision** is learner-authored. **Try again** creates a linked local revision and does not request or generate an AI rewrite.

The module makes no provider call, external request, AI correction, score, grammar/vocabulary diagnosis, correction claim, evaluation, full replacement text, or learner-outcome claim.

## Local state

Writing state uses the browser-local key:

```text
english-master.writing.v1.<learnerId>.en
```

It stores only bounded learner-authored drafts/revisions with their protocol and lesson IDs, band, local timestamps, status, and optional parent revision ID. It rejects malformed, stale-inventory, language-mismatched, and invalid protocol references.

Existing legacy English lesson drafts can be imported once into the matching writing task. The dedicated Writing route is then the editing surface, preventing a second live lesson draft from diverging.

Writing state does not retain evaluator feedback, provider/model facts, scores, review intervals, correction assertions, grammar or vocabulary outcomes, Mistake/Weakness data, or inferred ability. A draft, revision, or local protocol marker is not completion, assessment, or evidence of skill.

## Weakness boundary

Writing does not update Review, grammar, vocabulary, Mistake/Weakness, assessment/mastery, or the Weakness Engine. Those existing systems accept deterministic objective outcomes only.

A future evaluator requires separate authorization and a versioned, factual provider/provenance/privacy contract. A future writing-to-Weakness bridge also requires a learner-confirmed finding and an explicitly authored mapping from a stable evaluator error code to an allowed grammar target or vocabulary sense. It must not infer mappings from prose, lesson titles, task instructions, or free-form feedback.

## Build and validation

```bash
cd apps/web
npm run build:writing-snapshot # only after an intentional upstream update
npm run check:writing-snapshot
```

The builder reads only declared hash-bound English manifests, verifies closed packet inventories and SHA-256 packet hashes, requires `UNREVIEWED` status, requires exactly one writing protocol per lesson, and produces a deterministic 300-protocol browser projection. `npm run build` checks the committed writing snapshot before static export.
