# A1 Full Content Authoring Contract

Author exactly one of the ten five-lesson unit files declared by `curriculum/a1-full/v1/content-manifest.json`.

- Use only the exact ordered lesson IDs, target usage, permitted exercise types, and prerequisites in `allocation.json`.
- Write original A1 learner material; do not copy or adapt external lessons, examples, or media.
- Give each lesson 2–4 concise sections, 2–4 allocated objectives, and 3–6 exercises.
- Every section, exercise, and practice protocol must cite only target IDs allocated to that lesson.
- Follow the type-specific multiple-choice, fill-blank, matching, ordering, reading, listening, speaking, and writing fields in the v2 content-unit schema. Every exercise sets `media_required: false`.
- Include exactly four practice protocols. Keep listening transcript-only and hidden before the attempt; use `NOT_ASSESSED` when pronunciation audio is unavailable; wait for the learner's writing draft and provide feedback without a replacement answer.
- Keep content `PROJECT_AUTHORED`; do not add human-review, approval, release, provider-authentication, live-AI, network, or real-media claims.
- Avoid normalized exact reuse of learner-facing sections, exercise prompts or answers, and protocol instructions.

Validate the complete manifest and all ten units through `english-master-a1-full build`, then run `verify` and the full-population `audit`. Do not edit a published run in place.
