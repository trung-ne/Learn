# Web Validation Blockers

## Status as of 2026-10-09

This file records web-app validation work that could not run because npm package installation is blocked in the current environment. Update this file whenever a blocker is discovered, resolved, or changes.

## Blocked checks

| Check | Status | Blocker | Resume action |
| --- | --- | --- | --- |
| `npm run lint` | Blocked | On 2026-10-09, the local npm script could not locate the `eslint` executable. | After npm access is available, restore a complete `apps/web/node_modules` installation and run `npm run lint`. Record any remaining configuration error separately. |
| `npm run test` | Blocked | On 2026-10-09, the local npm script could not locate the `vitest` executable. | After npm access is available, restore the normal development dependency installation, then run `npm run test`. |
| `npm run typecheck` | Blocked | On 2026-10-09, the local npm script could not locate the `tsc` executable. | After normal dependency restoration, run `npm run typecheck` and distinguish any remaining diagnostics from the restored dependency baseline. |
| `npm run build` | Blocked | On 2026-10-09, all nine prebuild snapshot checks passed, then the local npm script could not locate the `next` executable. | After the dependency restoration, run `npm run build` and distinguish any remaining static-export failure from the restored dependency baseline. |

## Dependency-install attempts

- `npm install --no-package-lock` was stopped after reaching its background time limit without producing useful output.
- `npm install --no-save --no-package-lock @rollup/rollup-win32-x64-msvc@4.63.5` was stopped because npm access is blocked.
- The untracked repository-root `package-lock.json` predates this work and must remain untouched unless its owner explicitly requests a lockfile change.

## Checks already completed

- `python -m pytest` — 539 passed on 2026-10-07.
- `python -m english_master.project_audit` — passed on 2026-10-07.
- Targeted grammar schema checks — `python -m pytest tests/test_schemas.py tests/test_web_grammar_inventory.py` passed (5 tests) on 2026-10-04.
- Curriculum, vocabulary, and grammar snapshot checks — passed on 2026-10-04 (`310` curriculum packets, `20` vocabulary senses, and `20` grammar targets).
- `python -m english_master.schema_validation --schema web-grammar-inventory apps/web/src/content/generated/grammar-snapshot.json` — valid on 2026-10-04.
- Listening Lab schema checks — `python -m pytest tests/test_schemas.py tests/test_web_listening_inventory.py` passed (6 tests) on 2026-10-04; `python -m english_master.schema_validation --schema web-listening-inventory apps/web/src/content/generated/listening-snapshot.json` was valid.
- Listening Lab availability snapshot — `node scripts/check-listening-snapshot.mjs` passed on 2026-10-04; the checked snapshot deliberately contains `NO_AUTHORIZED_MEDIA` and zero sessions.
- Pronunciation snapshot — `node scripts/check-pronunciation-snapshot.mjs` passed on 2026-10-04; its 310 source-backed protocols are all `NOT_ASSESSED` and `UNREVIEWED`, with no audio capture or scoring.
- Speaking snapshot — `node scripts/check-speaking-snapshot.mjs` passed on 2026-10-05; it contains 310 source-backed `UNREVIEWED` protocols, and overall plus grammar, vocabulary, fluency, pronunciation, coherence, and appropriacy are all `NOT_ASSESSED`. A focused Vitest run remains blocked because the local `vitest` executable is unavailable; no dependency installation was attempted.
- Reading snapshot — `node scripts/check-reading-snapshot.mjs` passed on 2026-10-06; it contains 212 hash-verified English records (112 supplied objective passages and 100 supplied texts), all `UNREVIEWED`. The focused Vitest suites remain blocked because the local `vitest` executable is unavailable; no dependency installation was attempted.
- Writing snapshot — `node scripts/check-writing-snapshot.mjs` passed on 2026-10-07; it contains 300 hash-verified English `UNREVIEWED` writing protocols (50 per A1–C2 band) with the supplied `FEEDBACK_ONLY_NO_REPLACEMENT` boundary. The focused Vitest suites remain blocked because the local `vitest` executable is unavailable; no dependency installation was attempted.
- Tutor Context focused tests — authored for local-preference scope, compatibility boundaries, safe projection serialization, static routing, and explicit-copy UI behavior. They remain blocked because the local `vitest` executable is unavailable; no dependency installation was attempted.
- All nine committed learner snapshot checks — curriculum, vocabulary, grammar, listening, pronunciation, speaking, reading, writing, and assessment — passed on 2026-10-08. The assessment check verified the deterministic 367-package English projection.
- `python -m pytest tests/test_assessment_mastery.py` — 12 passed on 2026-10-08.
- `python -m english_master.project_audit` — passed on 2026-10-08.
- `git diff --check` — passed on 2026-10-08; Git reported only existing LF-to-CRLF warnings.
- VS Code diagnostics are clear for the new assessment catalog, progress library, dashboard, runner, hub, styles, and focused test files. Assessment package-route diagnostics remain blocked by the same missing `next` modules/types as the app-wide typecheck; explicit local narrowing removes feature-specific undefined-package errors. This is not a substitute for the blocked app-wide typecheck or web test suite.
- Direct TypeScript checking was attempted after Step 13.3. It is blocked by missing `next` modules/types and reports additional pre-existing diagnostics outside the new Activity Outcome Patterns files; see the blocked typecheck row above.
- Adaptive Learning Engine focused tests — `npm run test -- adaptive-learning today-recommendations` was attempted on 2026-10-09 and remained blocked because the local `vitest` executable is unavailable. No dependency installation was attempted.
- VS Code diagnostics are clear for the new adaptive planner, TODAY component, Home integration, and their focused test files. This is not a substitute for the blocked app-wide typecheck or Vitest suite.
- Progress Dashboard focused tests — `npm run test -- progress-dashboard` was attempted on 2026-10-09 and remained blocked because the local `vitest` executable is unavailable. `npm run lint` and `npm run typecheck` remained blocked by missing `eslint` and `tsc`; `npm run build` reran all nine successful prebuild snapshot checks before stopping at missing `next`.
- Personal Study Plan focused tests — `npm run test -- personal-study-plan tutor-context` was attempted on 2026-10-09 and remained blocked because the local `vitest` executable is unavailable. `npm run lint` and `npm run typecheck` remained blocked by missing `eslint` and `tsc`; `npm run build` reran all nine successful prebuild snapshot checks before stopping at missing `next`. No dependency installation was attempted.
- Dictionary / Language Library — `npm run check:dictionary-snapshot` passed on 2026-10-09, verifying the deterministic nine-entry original-authored `take` family snapshot. `npm run test -- dictionary` remains blocked because the local `vitest` executable is unavailable. `npm run build` reran all ten prebuild snapshot checks successfully, then stopped because `next` is unavailable. No dependency installation was attempted.

## Resume order

1. Restore npm access and complete the existing local dependency installation without changing the pre-existing root lockfile.
2. Run `npm run lint`, `npm run typecheck`, `npm run test`, and `npm run build` from `apps/web`.
3. Update this file with command results, remaining failures, and any minimal fixes.
4. Re-run `python -m english_master.project_audit` if documentation or implementation changes.
