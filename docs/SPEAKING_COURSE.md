# Speaking Course

## Purpose

The Speaking Course separates source-backed speaking self-practice from generic prompt panels. It provides a language-scoped index of exactly one supplied speaking protocol per verified lesson packet and a small application-authored orientation for the practice sequence:

1. Repeat
2. Read aloud
3. Controlled response
4. Guided response
5. Roleplay
6. Free speaking

For English, the orientation also presents the requested A1–C2 communicative progression. This is navigation for self-practice only. It is not copied from every source packet, a protocol classification, a claim that an individual learner progressed, or CEFR attainment evidence. German shows only the available source-backed A1 pilot inventory.

## Inventory boundary

`apps/web/scripts/build-speaking-snapshot.mjs` reads only the closed manifest sources declared in `apps/web/scripts/lib/sources.mjs`, verifies each manifest and packet SHA-256 binding, and extracts exactly one speaking protocol from each current packet. The committed snapshot retains only a deterministic opaque application ID, language/lesson context, supplied display title/topic, and exact supplied instruction plus optional supplied goal and guidance list.

The learner-facing inventory excludes upstream packet identifiers, source locations, hashes, provenance, source `target_ids`, raw manifests, provider facts, evaluation results, and fields not supplied by the selected protocol. Its content lifecycle remains `UNREVIEWED`.

## Local-only assessment boundary

The application does not run an AI/provider, capture audio, create a chat session, collect or store a transcript, or evaluate typed or spoken performance. Overall availability and the grammar, vocabulary, fluency, pronunciation, coherence, and appropriacy dimensions are all `NOT_ASSESSED`.

The workspace reuses only the existing lesson record `CourseProgress.lessons[lessonId].protocols.speaking`. A checked box means the learner marked self-practice in this browser. It is not a result, score, correction, success signal, proficiency claim, CEFR outcome, or course-unlock signal.

It does not update generic Review, vocabulary learning, grammar progress, Mistake/Weakness, assessment/mastery, or a Weakness Engine. Therefore it cannot produce feedback or recommendations to review grammar or vocabulary.

## Future feedback bridge

A future speaking-feedback-to-grammar/vocabulary link requires a separately authorized implementation with:

- explicit learner consent and audio/transcript storage, retention, and deletion policy;
- factual evaluator/provider/model/run provenance;
- an auditable assessed-result contract that distinguishes evaluated dimensions from `NOT_ASSESSED`;
- exact pre-authored, validated mapping from individual factual findings to grammar targets or vocabulary senses; and
- attribution and eligibility rules before any review or weakness pathway consumes results.

No mapping may be inferred from lesson titles, prompt text, objectives, targets stripped from the browser snapshot, or self-practice completion.

## Verification

Use `npm run check:speaking-snapshot` to verify the committed projection when dependencies are available. The Python schema validator and focused tests validate projection shape and reject assessment, feedback, score, source, and provenance leakage. Web lint, typecheck, Vitest, and build remain subject to the documented dependency blocker in [WEB_VALIDATION_BLOCKERS.md](WEB_VALIDATION_BLOCKERS.md).
