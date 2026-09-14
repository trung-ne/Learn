# 12.5B — German Bootstrap

Create a separate, original-authored German linguistic model using the shared CEFR framework and language-bound core from 12.5A. German is not an English translation: the model explicitly includes noun gender, Nominativ/Akkusativ/Dativ/Genitiv, article and adjective declension, verb position and sentence bracket, separable and modal verbs, Perfekt/Präteritum, subordinate clauses, capitalization, pronunciation, and German communicative functions.

The bootstrap is a bounded planning graph, not exhaustive German coverage, official CEFR endorsement, lesson content, or generation authority. It contains 120 deterministic nodes across the twelve internal tiers and ten common dimensions, with German-specific target labels and `kg_de_<tier>_<dimension>` IDs. It is original project-authored, `DRAFT`/`UNREVIEWED`, fixture-only, hash-bound, and uses no external payload, crawl, download, or network service.

Implementation uses the language-qualified graph schemas and builder in `english_master.german_bootstrap`; the existing English M15 builder and its immutable artifacts remain untouched. Later 12.5C may add source governance, and 12.5D may consume only the German nodes needed by its mini blueprint.
