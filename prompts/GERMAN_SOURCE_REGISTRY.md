# 12.5C — German Source Registry

This milestone adds a small, language-scoped German source registry without crawling,
downloading, or ingesting payloads. The registry is an additive wrapper and leaves the
legacy English registry and its hash-bound artifacts unchanged.

Registered German lanes:

- German Wiktionary official dumps — `APPROVED`, CC BY-SA 4.0, text/reference and
  future record-level ingestion only through the official dump route.
- German Wikibooks official dumps — `APPROVED`, CC BY-SA 4.0, text/reference and
  future record-level ingestion only through the official dump route.
- Wikidata German lexeme metadata — `APPROVED`, CC0-1.0, structured metadata/API
  reference lane with exact record provenance and rate-limit compliance required.
- Goethe-Institut resources — `REFERENCE_ONLY` until affirmative reuse permission is
  documented.
- Deutsche Welle resources — `REFERENCE_ONLY` until affirmative reuse permission is
  documented.

Every record is explicitly scoped to target language `de`. Reference-only records cannot
be ingested or redistributed. All records retain source URLs, license/terms notes,
operation permissions, attribution requirements, and review timestamps. The artifact is
a registry record, not evidence that any payload was accessed or that a license permits
an unrequested future operation.

Implementation lives in `english_master.german_source_registry`; its immutable JSON
artifact is `sources/german-registry-v1.json`. Future ingestion must independently verify
record-level license, attribution, source status, and the exact requested operation.
12.5D remains blocked until explicitly requested.
