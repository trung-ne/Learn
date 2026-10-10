# English Master learner web app

A lightweight, static learner interface for the existing English Full A1–C2 packets and German A1.1 pilot packets.

## Local use

```bash
npm install
npm run check:snapshot
npm run check:vocabulary-snapshot
npm run check:dictionary-snapshot
npm run check:grammar-snapshot
npm run check:listening-snapshot
npm run check:pronunciation-snapshot
npm run check:speaking-snapshot
npm run check:reading-snapshot
npm run check:writing-snapshot
npm run check:assessment-snapshot
npm run dev
```

Open the address printed by Next.js. The production build is fully static:

```bash
npm run build
```

## Routes

- `/` — application landing page
- `/learn` — target-language selection
- `/learn/en` and `/learn/de` — available course levels
- `/learn/en/dictionary` — supplied original-authored English Dictionary / Language Library
- `/learn/{language}/progress` — browser-local cross-course activity and evidence dashboard
- `/learn/{language}/plan` — browser-local supplied-curriculum planning workspace
- `/learn/{language}/{level}` — a level catalog
- `/learn/{language}/{level}/{unit}/{lesson}` — a static learner packet
- `/learn/{language}/{level}/review` — local scheduled review for that course
- `/learn/{language}/{level}/mistakes` — factual local activity outcome patterns for that course
- `/learn/{language}/{level}/tutor` — local Tutor Context preview and explicit external-tool prompt export
- `/learn/en/assessment` — local deterministic English assessment hierarchy and evidence dashboard
- `/learn/en/assessment/{assessmentId}` — one supplied English assessment package
- `/learn/en/grammar` — explicit-binding local English grammar practice progress
- `/learn/en/listening` — authorized-media-ready Listening Lab availability
- `/learn/{language}/pronunciation` — supplied audio-free pronunciation self-practice protocols
- `/learn/{language}/speaking` — supplied local-only speaking self-practice protocols
- `/learn/en/reading` — source-backed English reading availability and exact WordSense lookup
- `/learn/en/writing` — source-backed English writing tasks and local learner-authored revisions
- `/learn/en/vocabulary` — local WordSense learning and review

Language metadata is intentionally limited to the two supported target languages in `src/content/languages.ts`. Course links are derived from the current snapshot inventory: English currently exposes A1–C2 and German exposes only its available 10-lesson A1 pilot. Missing levels, lessons, exercises, and practice protocols are not fabricated; the interface displays an availability notice or omits an unavailable learner section.

## Content boundary

The app consumes the committed `src/content/generated/curriculum-snapshot.json`. Its build script reads only the explicitly declared, immutable English and German manifests, verifies their closed packet inventories and SHA-256 hashes, validates a narrow learner-facing projection (including usable exercise data and local learner identifiers), and produces a presentation snapshot. It does not generate, validate, approve, export, or alter curriculum content.

Run `npm run build:snapshot` only after an explicit upstream artifact update; use `npm run check:snapshot` for ordinary verification. `npm run build` runs that same check automatically before the static export and fails if the committed snapshot is stale. The browser projection contains learner-facing material only; upstream validation data remains outside learner pages. Its small TypeScript model represents that projection rather than duplicating the upstream packet and governance schemas.

The independent vocabulary lane reads explicitly authored English WordSense batches from `curriculum/web-vocabulary/v1/`, verifies their packet-bound exercise references, and writes `src/content/generated/vocabulary-snapshot.json`. Run `npm run build:vocabulary-snapshot` after an intentional vocabulary batch update and `npm run check:vocabulary-snapshot` for ordinary verification. See [Vocabulary Learning](../../docs/VOCABULARY_LEARNING.md) for its local lifecycle and data boundary.

The grammar lane separately derives a learner-safe English A1–C2 target inventory from explicit current packet exercise bindings and allocation grammar targets; it does not use the display snapshot's stripped target mappings or the M15 planning graph. Run `npm run build:grammar-snapshot` only after an intentional upstream artifact update and `npm run check:grammar-snapshot` for ordinary verification. See [Grammar Mastery](../../docs/GRAMMAR_MASTERY.md) for scope and limits.

The Listening Lab lane currently projects only a checked `NO_AUTHORIZED_MEDIA` availability sentinel from `curriculum/web-listening/v1/`; it ships no media or transcript content. Run `npm run build:listening-snapshot` after an intentional source-inventory update and `npm run check:listening-snapshot` for ordinary verification. Do not treat current transcript-only lesson practice as playable media or Listening Lab completion. See [Listening Lab](../../docs/LISTENING_LAB.md) for the authorization and local-state boundary.

The pronunciation lane independently projects one supplied `NOT_ASSESSED` protocol from each hash-verified current English A1–C2 packet and available German pilot packet. It retains only supplied lesson guidance and reuses the existing lesson-level local self-practice marker; it does not ship audio, collect audio, score speech, infer weaknesses, or update review state. Run `npm run build:pronunciation-snapshot` only after an intentional upstream packet update and `npm run check:pronunciation-snapshot` for ordinary verification. See [Pronunciation Engine](../../docs/PRONUNCIATION_ENGINE.md) for its evidence boundary.

The speaking lane independently projects one supplied `UNREVIEWED` speaking protocol from each hash-verified current English A1–C2 packet and available German pilot packet. It retains only supplied lesson guidance and reuses the existing lesson-level local self-practice marker. Grammar, vocabulary, fluency, pronunciation, coherence, and appropriacy are all `NOT_ASSESSED`; it does not collect audio or text, run a provider, generate feedback, score speech, infer weaknesses, link recommendations to grammar or vocabulary, or update review state. Run `npm run build:speaking-snapshot` only after an intentional upstream packet update and `npm run check:speaking-snapshot` for ordinary verification. See [Speaking Course](../../docs/SPEAKING_COURSE.md) for its evidence boundary.

The reading lane independently projects 112 current A1–B1 supplied objective passages and 100 C1–C2 supplied texts from hash-verified English packets. It has no B2, German, or extensive-reading collection. Only explicitly authored, literal, hash-bound WordSense ranges are clickable; adding one uses the exact existing local WordSense state and does not record an answer outcome. Run `npm run build:reading-snapshot` only after an intentional upstream packet update and `npm run check:reading-snapshot` for ordinary verification. See [Reading Module](../../docs/READING_MODULE.md) for the availability and no-guessing boundary.

The writing lane independently projects 300 current English writing protocols (50 per A1–C2 band) from hash-verified lesson packets. It retains only supplied goals, instructions, constraints, and the `FEEDBACK_ONLY_NO_REPLACEMENT` boundary. Drafts and learner-authored revisions remain browser-local; no evaluator, correction, score, Weakness update, provider call, or replacement text is generated. Run `npm run build:writing-snapshot` only after an intentional upstream packet update and `npm run check:writing-snapshot` for ordinary verification. See [Writing Module](../../docs/WRITING_MODULE.md) for the local-state and feedback boundary.

The assessment lane independently projects the pinned immutable English Assessment + Mastery run into 300 lesson quizzes, 60 unit checkpoints, six level tests, and one placement package. It scores only supplied no-media objective contracts locally in the browser, keeps drafts and attempts separate from all other learner state, and does not unlock content, certify CEFR attainment, diagnose placement, or determine proficiency. Writing, speaking, pronunciation, and audio listening remain unavailable rather than scored. Run `npm run build:assessment-snapshot` only after an explicit upstream assessment update and `npm run check:assessment-snapshot` for ordinary verification. See [Web Assessment](../../docs/WEB_ASSESSMENT.md).

Tutor Context locally projects a self-reported band, structured goals, and capped state from existing browser-local records into a prompt that the learner explicitly copies to an external AI tool. It does not call a provider, add a chat session, transmit data, record external responses, infer a learner's level, or treat local vocabulary/grammar state as a proficiency claim. The declared band controls whether the current course can enter the projection; a target band is aspirational only. It excludes raw answers, learner identifiers, writing drafts, audio, transcripts, and provider material. See [AI Tutor Context](../../docs/AI_TUTOR_CONTEXT.md).

Home's `TODAY` section is a separate browser-local, deterministic recommendation projection. It selects at most one due English vocabulary card, grammar card, transcript-based listening revisit, unfinished supplied pronunciation prompt, and next incomplete supplied lesson for one current course. It has no persisted daily plan, randomization, course lock, provider call, proficiency/mastery rating, or pronunciation/audio-listening score. It does not replace the hash-validated Python adaptive-review workflow. See [Browser-Local Adaptive Learning Engine](../../docs/ADAPTIVE_LEARNING_ENGINE.md).

The independent dictionary lane projects a bounded original-authored, `UNREVIEWED` English lexical inventory. It currently contains the explicit `take` family only: four supplied senses, three linked phrasal verbs, supplied collocations, and three word forms. Its browser-local `learned`, `learning`, `weak`, and `not learned` markers are local recall signals, not proficiency, CEFR attainment, retention, or mastery claims. It never uses DRAFT taxonomy or M15 planning records. Run `npm run build:dictionary-snapshot` only after an intentional inventory update and `npm run check:dictionary-snapshot` for ordinary verification. See [Dictionary / Language Library](../../docs/DICTIONARY_LANGUAGE_LIBRARY.md).

The language-scoped Progress Dashboard aggregates only matching browser-local course activity, vocabulary/grammar state, supplied objective assessment evidence, and review outcomes. It explicitly marks retention, study time, historical mistake trends, and unsupported scores as unavailable rather than inferring them. It does not determine CEFR attainment, proficiency, diagnosis, certification, or access. See [Browser-Local Progress Dashboard](../../docs/PROGRESS_DASHBOARD.md).

The language-scoped Personal Study Plan uses learner-reported current/goal bands and a selected daily planning allocation to arrange only the available supplied packet corridor, saved review quota, weekly planning blocks, and explicitly supplied practice categories. Catalog durations are planning inputs, not elapsed study time, expected pace, completion forecasting, CEFR attainment, or access rules. Missing course corridors remain unavailable rather than inferred. See [Browser-Local Personal Study Plan](../../docs/PERSONAL_STUDY_PLAN.md).

## Learner boundaries

Progress, attempts, basic per-exercise results, runner position, last lesson access time, protocol completion, writing drafts, and assessment drafts/results are local browser data scoped by a browser-local learner identifier, target language, and course level or pinned assessment run. Assessment attempts retain only package/run hashes, submission time, factual item correctness, and explicit target bindings after submission; they never retain raw answers. Reserved concept progress is stored separately from lesson progress. Vocabulary has its own learner-and-language-scoped local WordSense state for explicit starts, attempt/mistake counts, deterministic review dates, and self-study mastery indicators. English grammar has a separate language-scoped local state that records only deterministic outcomes from explicitly bound objective activities and uses a fixed schedule; its final local status is not a grammar-competence or proficiency result. The course review foundation stores only aggregate factual outcomes for deterministically scored objective exercises and independently combines those due activities with vocabulary candidates. Its Activity Outcome Patterns view reads only current aggregate incorrect results and supplied lesson context; it neither stores answers nor assigns linguistic causes, grammar weakness, or proficiency. Course and unit summaries count only lessons in the current snapshot, so stale local IDs do not affect totals. Free-text exercise responses, answers, prompts, transcripts, analytics events, and personal profile data are not persisted. There are no accounts, server routes, analytics, network tutoring, live AI calls, media playback, audio collection, or pronunciation scoring. Answer concealment is a user-interface feature, not a security boundary. Native controls, visible keyboard focus, semantic navigation, and reduced-motion preferences are supported without a separate accessibility framework.

## Stored AI-practice prompts

When a lesson packet supplies a practice protocol, its exact lesson-specific `instruction` is displayed and can be copied into a learner's preferred AI or voice-AI tool. Writing shows the lesson’s target CEFR band, exact supplied task, and only supplied goal, checklist, or useful-language fields; drafts remain local and no writing evaluation or replacement text is generated. Current listening is transcript-only: no packet has an authorized browser-playback asset, so the app shows no audio player and never fabricates an audio URL. A transcript remains hidden until the learner attempts the supplied question, then its reveal state is announced accessibly. Speaking and pronunciation are prompt-first; the app renders only explicitly supplied roles, targets, examples, explanations, and guidance, and never records audio or scores pronunciation. The web app does not regenerate prompts, invoke a provider, create a chat session, or assess the learner.

The app has no runtime curriculum or provider dependency for basic use once served as static files: lessons, exercises, stored prompts, and local progress operate in the browser. Its static export now includes an installable, same-origin PWA shell and deliberate offline caching for the app shell plus a learner-selected current review page. It never silently downloads the whole course, caches browser-local learner data, authorizes audio/media, or adds accounts, analytics, remote error reporting, provider calls, or synchronization. A browser-local backup/export is not a server backup or cross-device recovery. See [Production Hardening](../../docs/PRODUCTION_HARDENING.md) for cache, update, local-data, hosting, security, and future-service boundaries.
