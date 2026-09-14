# Multilingual Core

## Purpose

English Master supports language-scoped courses in one repository. English is a target-language namespace, not an implicit global setting. This initial core supports `en` and `de`; it establishes contracts only and does not create a German curriculum, sources, or learner content.

## Language boundary

- `language_code` is the target language learned by the course.
- `learner_language_code` is separate contextual information. Existing Vietnamese learner annotations remain compatible and are not reinterpreted.
- New language-scoped paths use `course/<language_code>/...`; language-scoped supporting data uses `data/<area>/<language_code>/...`.
- Existing English paths and immutable artifacts remain unchanged for backward compatibility.
- New collision-prone knowledge-graph identities use `kg_<language_code>_<tier>_<dimension>`, for example `kg_de_a1_1_grammar`.
- Vocabulary senses retain their language-bearing identity, for example `vocab_de_haus_001`.

## Core contracts

- A language profile accepts only the currently declared `en` and `de` target-language codes.
- New taxonomy work uses a language-bound wrapper with an explicit target language. Its vocabulary senses and relationships must match that target language.
- New source-registry work uses a language-scoped wrapper. A source declared for one language cannot authorize a taxonomy citation for another. Legacy source records remain compatible until a later language-scope record is created.
- Future multilingual assessment packages and submissions use language-bound wrappers. Their learner state is a language-bound v2 envelope and objective concept IDs must use that language's `kg_<language>_` namespace.

## Compatibility and limits

This core does not move legacy English content, modify legacy English IDs, alter existing CLI defaults, create any German linguistic model or source record, or call network/AI services. Existing English v1 state stays valid. A future explicit migration may copy it into a language-bound `en` state; it must not overwrite the original.

All future content remains `UNREVIEWED`; a passing local validation only establishes contract consistency.
