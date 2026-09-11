# Lightweight Development Workflow

## Purpose

Routine work uses a small local consistency check rather than approval-like gates. The goal is to identify concrete drift between the active documentation, repository code, and declared local facts.

A passing result does **not** establish content quality, CEFR suitability, human review, release approval, redistribution authority, provider behavior, or public-release readiness.

## Routine checks

After a change, run only the checks relevant to that change:

```bash
python -m english_master.project_audit
python -m pytest tests/<changed-area>
git diff --check
```

`python -m english_master.project_audit` checks that active workflow documents, local implementation paths, and declared repository facts do not drift. It is read-only and requires no network service, paid runner, external tool, or reviewer.

## M9 lightweight QA

When M9 is explicitly requested, run the complete suite and directly inspect five representative lesson packets:

```bash
python -m pytest
python -m english_master.project_audit
git diff --check
```

Record the five selected packets, relevant lesson/exercise/prompt observations, any blocking defect, and the factual result `M9 DEVELOPMENT: PASS` or `M9 DEVELOPMENT: FAIL`. A pass permits the next explicitly requested step; it does not create human review, release approval, public-distribution authority, or a lifecycle transition from `UNREVIEWED`.

Run the full test suite when a shared validator, schema, or core packaging component changes. Otherwise, targeted tests are sufficient.

## Historical evidence

Existing M9, M10, and M11 records remain immutable historical evidence and can still be verified with their original commands. They are not required for routine development work and are not rewritten to match this lightweight workflow.

## Export boundary

An export build must still preserve its own input schema, hashes, source permissions, closed inventory, and deterministic rendering checks. Historical M9 v2 and M10 closure artifacts are not routine-development gates. A development export remains a local artifact; it does not itself authorize public distribution or change generated content from `UNREVIEWED`.
