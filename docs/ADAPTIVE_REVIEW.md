# Adaptive Review

Adaptive Review is a bounded, offline scheduling layer over the existing Assessment + Mastery artifacts. It references existing objective lesson-quiz items; it does not generate questions or alter the immutable 367-package assessment run. The static web app's [Browser-Local Adaptive Learning Engine](ADAPTIVE_LEARNING_ENGINE.md) is a distinct TypeScript Home-page projection over browser-local state; it neither executes this Python workflow nor reads its file artifacts.

## Policy

A plan selects up to ten concepts in strict priority order: `NEW_LESSON`, `RECENT_MISTAKE` (last seven days), `DUE`, then `OLD_WEAK` (mastery below 0.80 and unseen for at least 14 days). The current lesson is supplied by `--lesson-id` and resolved only against the verified assessment run. Plans contain item/package references and hashes, not copied question content.

Adaptive state is a separate caller-owned JSON file because the existing seven-field learner state remains backward compatible. Successful observations advance through 1, 3, 7, 14, 30, and 60 days. Any incorrect mapped result records a recent mistake, resets the stage, and schedules one day. The state is local single-writer data; the assessment state and adaptive state are each atomic, but not cross-file transactional.

## Commands

```bash
python -m english_master.adaptive_review plan \
  --assessment-run curriculum/assessments/v1/runs/<run-id> \
  --state data/learner-state/local-01/concept-state.json \
  --adaptive-state data/learner-state/local-01/adaptive-review-state.json \
  --lesson-id m16a1-v1-a1-u01-l01 --as-of 2026-09-14T12:00:00Z \
  --output data/learner-state/local-01/review-plan.json

python -m english_master.adaptive_review observe \
  --package <lesson-quiz.json> --submission <submission.json> \
  --adaptive-state data/learner-state/local-01/adaptive-review-state.json \
  --output data/learner-state/local-01/observation.json
```

The caller first runs the existing assessment scorer, then observes the same submission, then builds a plan. Outputs refuse overwrite. All artifacts remain development/local artifacts: they are not validated proficiency, CEFR certification, human review, release approval, provider evidence, or learner outcome claims.
