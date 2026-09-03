# M5 Curriculum Architecture and Dependency Graph

## Scope

M5 defines an outline-only, machine-readable curriculum architecture from A1.1 through C2.2. It does not contain lesson explanations, dialogues, readings, listening scripts, exercises, answer keys, assessments, or AI prompts.

The committed architecture is deliberately compact: one representative globally numbered unit per internal tier, two lesson outlines per unit, and one review node per unit. Its scale ranges describe the intended expansion envelope; they are planning estimates, not claims that M5 contains 1,000 hours of finished learning material.

## Authoritative artifacts

- `curriculum/structure.json` — hierarchy, units, lesson outlines, reviews, scale assumptions, and taxonomy gate.
- `curriculum/prerequisite_graph.json` — explicit typed nodes and edges plus deterministic topological order.
- `curriculum/coverage-roadmap.json` — introduction, development, and review placements for all required dimensions.
- `curriculum/curriculum-graph.dot` — compact offline view of unit, lesson-outline, and review sequencing.
- `curriculum/validation-report.json` — reproducible validation result for the committed artifacts.

Draft 2020-12 schemas in `schemas/` remain authoritative for record shape. Cross-record and graph invariants are implemented in `english_master.curriculum_validation`.

## Hierarchy and identifiers

The `.1` and `.2` tiers are internal curriculum subdivisions, not official CEFR levels. Every unit belongs to exactly one internal tier and every lesson or review belongs to exactly one unit.

Unit numbers are global across the whole A1-C2 sequence:

- `A1.1-U01`
- `A1.2-U02`
- `A2.1-U03`
- ...
- `C2.2-U12`

Lesson and review IDs omit the internal half-tier, so global unit numbers prevent collisions:

- `A1-U01-L01`
- `A1-U02-L01`
- `A1-U02-REV`

Unit numbers never restart at `U01` in a `.2` tier.

## Taxonomy review gate

The M2 taxonomy is schema-valid but its representative records remain `DRAFT`. M5 may reference those records only under the explicit `CONDITIONAL_DRAFT_REFERENCE` gate in `structure.json`:

- references are authorized for outline planning only;
- generated-content work is blocked;
- statuses other than those explicitly accepted fail validation; and
- independent linguistic and pedagogical review is required before M6.

This gate does not convert DRAFT taxonomy records to approved records. Raw, quarantined, normalized, unregistered, or otherwise unauthorized records cannot become curriculum dependencies.

## Graph semantics

Edges point from predecessor or source to dependent or target.

Ordering edges:

- `lesson_prerequisite`
- `unit_ordering`
- `taxonomy_prerequisite`

Non-ordering edges:

- `introduction`
- `review`
- `related_non_ordering`

A taxonomy relationship never creates prerequisite order unless a separate `taxonomy_prerequisite` edge exists. Only ordering edges participate in cycle checks and deterministic topological sorting. Nodes are serialized by sequence key and ID; edges by type, source, and target.

The DOT view uses shape and direct labels rather than color: boxes are units, ellipses are lesson outlines, and diamonds are reviews. It is a compact inspection aid; the JSON graph is authoritative.

## Coverage model

The coverage roadmap has exactly one row for each required dimension:

- listening, speaking, spoken interaction, reading, writing, mediation;
- grammar, vocabulary senses, collocations, lexical chunks, pronunciation;
- communicative functions, topics, discourse, pragmatics, and assessment capabilities.

Every row declares one introduction lesson, later development lesson(s), and later review node(s). Every introduction and development lesson must declare the row's dimension, and each review node must review at least one lesson that declares it. Placements are original planning decisions with explicit confidence and remain subject to curriculum review.

## Offline validation

Run the complete bundle validator:

```bash
python -m english_master.curriculum_validate curriculum/structure.json
```

Write a deterministic report:

```bash
python -m english_master.curriculum_validate curriculum/structure.json \
  --report curriculum/validation-report.json
```

The installed equivalent is:

```bash
english-master-curriculum-validate curriculum/structure.json
```

The validator returns nonzero for schema errors, hierarchy or deterministic-ID violations, duplicate IDs or edges, missing references, unauthorized dependencies, parent mismatches, non-earlier prerequisites, ordering cycles, unresolved or premature reviews, graph drift, nondeterministic serialization/topology, coverage gaps or dimension-placement mismatches, and version mismatches. All operation is local and offline.

## Independent human review snapshots

The M5 review workflow prepares a canonical hash manifest, independently loads and binds the source registry, rejects taxonomy or Vietnamese-annotation citations whose source is missing or ineligible for reference, validates distinct linguistic and pedagogical human submissions against the complete taxonomy and annotation scopes, atomically publishes an immutable approval overlay, and verifies that overlay against current source and registry values. Reviewed annotations remain contextual evidence and do not enter the approved-taxonomy generation-authority set. The workflow never edits `OUTLINE_ONLY` structure records or `DRAFT` taxonomy records, and the manifest itself does not authorize content generation.

No real review or approval snapshot is committed by this implementation. See [M5_REVIEW_WORKFLOW.md](M5_REVIEW_WORKFLOW.md) for trust boundaries, forms, commands, checklist criteria, revision handling, storage layout, and exit codes.

```bash
python -m english_master.curriculum_review prepare curriculum/structure.json --source-registry sources/registry.yaml --output <new-manifest-directory>
python -m english_master.curriculum_review publish curriculum/structure.json --source-registry sources/registry.yaml --manifest <manifest.json> --linguistic-review <review.json> --pedagogical-review <review.json> --reviewer-registry <trusted-reviewer-registry.json> --approved-at <ISO-8601> --published-by <publisher-id> --output <new-snapshot-directory>
python -m english_master.curriculum_review verify curriculum/structure.json --source-registry sources/registry.yaml --snapshot <snapshot-directory> --reviewer-registry <trusted-reviewer-registry.json>
```
