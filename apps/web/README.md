# English Master learner web app

A lightweight, static learner interface for the existing English Full A1–C2 packets and German A1.1 pilot packets.

## Local use

```bash
npm install
npm run check:snapshot
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
- `/learn/{language}/{level}` — a level catalog
- `/learn/{language}/{level}/{unit}/{lesson}` — a static learner packet

Language metadata is intentionally limited to the two supported target languages in `src/content/languages.ts`. Course links are derived from the current snapshot inventory: English currently exposes A1–C2 and German exposes only its available 10-lesson A1 pilot. Missing levels, lessons, exercises, and practice protocols are not fabricated; the interface displays an availability notice or omits an unavailable learner section.

## Content boundary

The app consumes the committed `src/content/generated/curriculum-snapshot.json`. Its build script reads only the explicitly declared, immutable English and German manifests, verifies their closed packet inventories and SHA-256 hashes, validates a narrow learner-facing projection (including usable exercise data and local learner identifiers), and produces a presentation snapshot. It does not generate, validate, approve, export, or alter curriculum content.

Run `npm run build:snapshot` only after an explicit upstream artifact update; use `npm run check:snapshot` for ordinary verification. `npm run build` runs that same check automatically before the static export and fails if the committed snapshot is stale. The browser projection contains learner-facing material only; upstream validation data remains outside learner pages. Its small TypeScript model represents that projection rather than duplicating the upstream packet and governance schemas.

## Learner boundaries

Progress, attempts, basic per-exercise results, runner position, last lesson access time, protocol completion, and writing drafts are local browser data scoped by a browser-local learner identifier, target language, and course level; reserved concept progress is stored separately from lesson progress. Course and unit summaries count only lessons in the current snapshot, so stale local IDs do not affect totals. The home page keeps English and German continuation independently and selects its convenience continue link from the most recently accessed valid course. Free-text exercise responses, answers, prompts, transcripts, analytics events, and personal profile data are not persisted. There are no accounts, server routes, analytics, network tutoring, live AI calls, media playback, audio collection, or pronunciation scoring. Answer concealment is a user-interface feature, not a security boundary. Native controls, visible keyboard focus, semantic navigation, and reduced-motion preferences are supported without a separate accessibility framework.

## Stored AI-practice prompts

When a lesson packet supplies a practice protocol, its exact lesson-specific `instruction` is displayed and can be copied into a learner's preferred AI or voice-AI tool. Writing shows the lesson’s target CEFR band, exact supplied task, and only supplied goal, checklist, or useful-language fields; drafts remain local and no writing evaluation or replacement text is generated. Current listening is transcript-only: no packet has an authorized browser-playback asset, so the app shows no audio player and never fabricates an audio URL. A transcript remains hidden until the learner attempts the supplied question, then its reveal state is announced accessibly. Speaking and pronunciation are prompt-first; the app renders only explicitly supplied roles, targets, examples, explanations, and guidance, and never records audio or scores pronunciation. The web app does not regenerate prompts, invoke a provider, create a chat session, or assess the learner.

The app has no runtime curriculum or provider dependency for basic use once served as static files: lessons, exercises, stored prompts, and local progress operate in the browser. It deliberately does not install a service worker or pre-cache resources, so it is not an installable PWA and a remotely hosted page is not guaranteed to reload without a network connection.
