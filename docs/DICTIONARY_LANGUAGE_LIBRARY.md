# Dictionary / Language Library

## Scope

`/learn/en/dictionary` is a static, browser-local lexical library. It currently contains one bounded original-authored, `UNREVIEWED` English family: `take`.

The supplied inventory contains four separately identified senses (`A1`, `A2`, `B1`, and `B2`), three explicitly linked phrasal verbs (`take off`, `take over`, `take up`), supplied collocations, and the explicit forms `take`, `taking`, and `taken`.

It is not a comprehensive dictionary, an assessment, a CEFR authority, or a projection of the M15/taxonomy knowledge graph. The displayed bands are authored `UNREVIEWED` labels, not independently validated CEFR decisions. The page does not derive relationships from spelling or import wording from external dictionaries. A relation appears only when the committed inventory explicitly links it.

## Local statuses

The library records only browser-local study state for dictionary entry IDs:

- `✓ learned` — at least three locally recorded supplied recall successes and no recorded incorrect outcome.
- `◉ learning` — explicitly started locally without the learned condition.
- `! weak` — one or more locally recorded incorrect recall outcomes.
- `○ not learned` — no valid local state for that supplied entry.

These are local self-study signals. They do not establish language ability, CEFR attainment, retention, proficiency, or mastery. Searching and opening an entry do not write state. Only explicit start and recall-result controls update browser-local state.

## Data boundary

The source batch under `curriculum/web-dictionary/v1/` is original project-authored data with `PROJECT_AUTHORED` authorship and `UNREVIEWED` content status. `build-dictionary-snapshot.mjs` validates its closed records and produces the browser snapshot. Run `npm run build:dictionary-snapshot` after an intentional source change and `npm run check:dictionary-snapshot` for ordinary verification.

German and any other language remain unavailable until a separate validated learner-facing dictionary inventory exists.
