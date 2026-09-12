# A1 Practical Content Check

Inspect the existing Full A1 v2 curriculum. Do not rebuild A1.

Select the existing deterministic representative sample of twelve lessons from `curriculum/a1-full/v2/samples/sample-12.json`. It covers all ten units.

For each selected lesson inspect:

- English correctness
- Vietnamese explanation quality
- CEFR A1 suitability
- grammar scope
- vocabulary load
- example naturalness
- exercise usefulness and answer correctness
- lesson length
- repetition with nearby lessons
- listening AI prompt usefulness
- speaking roleplay usefulness
- pronunciation usefulness
- writing-task suitability

Do not require:

- human reviewers
- paid AI runners
- full-corpus AI review
- release approval
- complex new schemas
- new governance infrastructure

Use existing validators and tests. Classify findings as `BLOCKER`, `IMPORTANT`, or `MINOR`.

Fix only clear systemic `BLOCKER` or `IMPORTANT` defects. If the same issue occurs repeatedly, fix the generator, template, or policy rather than manually patching many lesson files. After a fix, regenerate only affected artifacts and run relevant tests.

Run:

```bash
python -m pytest
git diff --check
```

Report:

- lessons inspected
- issues found
- systemic fixes made
- tests
- remaining limitations

State exactly one result:

```text
A1 PRACTICAL CHECK: PASS
```

or:

```text
A1 PRACTICAL CHECK: FAIL
```

If the sample passes, mark the Full A1 v2 corpus `A1 DEVELOPMENT READY`. This is a development readiness result only; it does not establish human review, release approval, provider behavior, or public-distribution authority. Then stop.
