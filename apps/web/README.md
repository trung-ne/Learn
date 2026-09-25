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

Language metadata is intentionally limited to the two supported target languages and their available levels in `src/content/languages.ts`.

## Content boundary

The app consumes the committed `src/content/generated/curriculum-snapshot.json`. Its build script reads only the explicitly declared, immutable English and German manifests, verifies their closed packet inventories and SHA-256 hashes, and produces a presentation projection. It does not generate, validate, approve, export, or alter curriculum content.

Run `npm run build:snapshot` only after an explicit upstream artifact update; use `npm run check:snapshot` for ordinary verification. All displayed material is `UNREVIEWED` development content.

## Learner boundaries

Progress, attempts, protocol completion, and writing drafts are local browser data separated by target language. There are no accounts, server routes, analytics, network tutoring, live AI calls, media playback, audio collection, or pronunciation scoring. Answer concealment is a user-interface feature, not a security boundary.
