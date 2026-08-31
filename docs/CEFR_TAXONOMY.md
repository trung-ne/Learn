# CEFR Taxonomy Foundation

## Scope

M2 defines a small, authored linguistic knowledge skeleton for later curriculum and classification work. It is not a corpus, a lesson collection, or an exhaustive CEFR inventory. Prototype descriptions and examples are original; links to external sources are citations only.

The canonical prototype is under `curriculum/taxonomy/`. The authoritative schemas remain in `schemas/`. Existing M0 record schemas remain canonical for ordinary records; M2 taxonomy records use the taxonomy-specific schemas and collection-level semantic validation.

## CEFR model

The six CEFR bands are `A1`, `A2`, `B1`, `B2`, `C1`, and `C2`. The twelve values `A1.1` through `C2.2` are English Master internal curriculum subdivisions, not official CEFR levels. Taxonomy data must not claim that the subdivisions have independent official descriptor authority.

`minimum_cefr`/`cefr` expresses the earliest internal curriculum placement in the prototype. Broad coverage claims use official bands and qualitative states (`introduced`, `developed`, `expected`, `not_specified`) rather than fabricated counts or unsupported precision.

## Dimensions and records

Concept records cover skills, grammar, collocations, lexical chunks, pronunciation, communicative functions, topics, discourse, pragmatics, and assessment capabilities. Prerequisites form the directed dependency graph. Related concept links are typed associations and are not prerequisites.

Vocabulary is represented by sense. A surface lemma can have multiple records with distinct IDs, definitions, levels, collocations, chunks, examples, and relationships. It must never be reduced to a single word-level classification.

Vietnamese learner annotations explicitly distinguish `RESEARCH_CLAIM` from `PEDAGOGICAL_OBSERVATION`. Research claims require appropriately labelled evidence; observations are teaching hypotheses/observations and must not be presented as research findings.

## Evidence and source governance

A taxonomy citation is not ingestion, provenance, or permission to copy. A `REFERENCE_ONLY` source may inform taxonomy research through a locator and link, but its wording, descriptors, corpus, or examples must not be copied into generated learning material. Unknown or quarantined sources cannot support an approved taxonomy claim. See `sources/registry.yaml` and `docs/DATA_POLICY.md` for source status and licensing rules.

## Validation

Validate all schemas:

```bash
python -m pytest
```

Validate the prototype and coverage matrix:

```bash
python -m english_master.schema_validation --schema taxonomy curriculum/taxonomy/taxonomy.json
python -m english_master.schema_validation --schema coverage-matrix curriculum/taxonomy/coverage-matrix.json
```

Validation checks schema shape, duplicate IDs, CEFR values, prerequisite and relationship references, dependency cycles, vocabulary sense identity, annotation targets, and coverage-range completeness. The validator is deterministic and offline.

## M2 exclusions

M2 does not download or ingest source records, crawl pages, classify a corpus, generate lessons/exercises, build curriculum sequencing, or implement M3 ingestion and linguistic analysis. `data/` and `curriculum/` payload locations remain reserved for later milestones; `curriculum/taxonomy/` contains only this representative authored prototype.
