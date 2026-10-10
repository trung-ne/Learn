# Pronunciation Engine

## Current Step 13.6 scope

The web app provides a local **Pronunciation self-practice** index at `/learn/{language}/pronunciation`. It is an organization view for exact, lesson-bound pronunciation protocols already supplied by the current immutable English A1–C2 packet manifests and the available German A1 pilot manifest.

The builder verifies each declared manifest and packet SHA-256 hash, requires `UNREVIEWED` source packets, accepts exactly one pronunciation protocol per packet, and creates `apps/web/src/content/generated/pronunciation-snapshot.json`. The learner snapshot contains only an opaque app ID, lesson location/context, supplied instructional text, and fixed states:

- `assessmentAvailability: NOT_ASSESSED`
- `contentStatus: UNREVIEWED`

It deliberately excludes packet/source identities, hashes, provenance, media, transcript data, score/rubric fields, provider details, and approval-like fields. Run `npm run check:pronunciation-snapshot` for routine verification. Run `npm run build:pronunciation-snapshot` only after an explicitly intended upstream packet update.

## Audio-free boundary

No browser microphone, upload, `getUserMedia`, `MediaRecorder`, speech recognition, text-to-speech, audio playback, acoustic analysis, provider call, or speech result is implemented in this lane.

M8.2 pronunciation contracts require `AUDIO` for assessment and require `NOT_ASSESSED` without it. Accordingly, the index must not render or store a pronunciation, word-stress, fluency, or intonation score; percentage; rating; bar; correction; accent inference; phonetic-correctness judgment; problem sound; or problem word.

The existing lesson completion checkbox remains the sole local action. It is called **locally marked self-practice** and is stored only in the pre-existing course-local `CourseProgress.lessons[lessonId].protocols.pronunciation` field. It does not mean the learner was assessed, accurate, proficient, complete, or at a CEFR level.

## State and Weakness boundary

Pronunciation self-practice does not write to:

- generic objective Review;
- vocabulary progress;
- grammar progress;
- activity outcome patterns / Mistake-Weakness; or
- a future Weakness Engine.

Those local lanes require deterministically checked objective exercise outcomes. Text-only self-practice and `NOT_ASSESSED` pronunciation protocols are not eligible evidence.

## Planning-data exclusion

M15 and taxonomy pronunciation records remain project-authored `DRAFT` planning material. This implementation does not use them to invent or classify target families, IPA, sounds, minimal pairs, linking, reductions, stress, intonation, examples, correction criteria, rubrics, prerequisite data, or Weakness Engine labels.

The index displays only target wording, examples, explanations, and guidance that its current source packet expressly supplied. Missing fields remain missing.

## Future assessment gate

A future separately requested assessment lane would need, at minimum:

1. explicitly authorized model/reference audio and delivery permissions;
2. learner-audio consent, storage, retention, deletion, and secure browser handling;
3. an evaluator with factual tool/model/version and input/output provenance;
4. explicit target-specific assessment mappings and rubrics;
5. a result contract with dimension-specific statuses rather than an invented aggregate; and
6. an independently defined eligibility rule before a factual assessed result can feed a Weakness Engine.

Until those requirements are implemented and validated, every dimension remains `NOT_ASSESSED`. This local development view creates no human/release/provider authority, pedagogical-quality claim, CEFR endorsement, learner-outcome claim, or public-distribution authority.
