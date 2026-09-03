# M5 Pedagogical Review Form

This is a blank human-review form, not review evidence and not approval. Complete it only after preparing a manifest and inspecting the exact hash-bound files. Transfer the completed information to a JSON draft conforming to `schemas/curriculum-independent-review-draft.schema.json`; omit `review_id` and let the publish command derive it.

## Reviewer

- Reviewer ID from the trusted registry:
- Identity evidence ID from the trusted registry:
- Display name:
- Relevant qualifications:
- Independent of authorship: yes / no
- Conflicts disclosed: yes / no
- Conflict notes, when applicable:
- Reviewed-at timestamp with timezone:

## Bound scope

- Manifest ID:
- Complete manifest SHA-256:
- Confirm all artifacts reviewed: STRUCTURE, GRAPH, COVERAGE, TAXONOMY
- Confirm the manifest names the source-registry path, schema version, and SHA-256 used for citation eligibility:
- Confirm every taxonomy ID in `manifest.json.taxonomy_scope` reviewed:
- Confirm every Vietnamese learner annotation ID in `manifest.json.annotation_scope` reviewed:
- Confirm annotation review was treated as learner-context review, not lesson-generation authorization:

## Required checklist

Record `PASS` or `FAIL` and specific notes for every item.

- Pedagogical sequence:
- Objective coherence:
- Skill balance:
- Review spiral:
- Assessment alignment:
- Scope and hours credibility:

## Findings

For each finding record a unique ID, severity (`INFO`, `MINOR`, `MAJOR`, or `CRITICAL`), category, exact location, description, and required action.

## Decision and attestation

- Decision: APPROVE / REQUEST_CHANGES / REJECT
- I performed a human review of the exact hash-bound manifest and its four artifact versions: yes / no
- I did not edit the source records as part of this decision: yes / no
- I did not review or approve generated lesson content: yes / no

An approval decision is invalid if any required check fails or a major/critical finding remains.
