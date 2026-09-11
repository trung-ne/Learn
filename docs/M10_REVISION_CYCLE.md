# M10 Revision

## Active workflow

M10 is a small revision loop:

```text
failed artifact → new corrected revision → relevant validation/tests
```

The predecessor remains unchanged. Store the corrected artifact at a new path and retain a concise note with the predecessor hash, the observed defect, and the new path. Run only the relevant schema/semantic validator and tests.

A revision does not need a full M9 finding import, supersession system, dependency rebuild, fresh M9 review, paid/live AI review, human review, or approval tier. Revised generated content remains `UNREVIEWED`.

## Historical records

The retained M10 governance records and CLI remain available for immutable historical verification. They are not the required workflow for future routine revisions and must not be altered.
