# Browser-Local Personal Study Plan

## Route

`/learn/{language}/plan` lets a learner select a self-reported current band, an aspirational higher target band, and a planned daily allocation of 15, 30, 45, 60, or 90 minutes.

The selection is stored only in browser-local Tutor preferences, scoped by the local learner identifier and target language. The current and target bands are learner choices; they are not placement, proficiency, diagnostic, mastery, retention, or CEFR-attainment results.

## Supplied-curriculum corridor

A plan is available only when every course band from the selected current band through the higher target exists in the supplied inventory. For example, a valid English A2 → B2 selection orders the remaining supplied A2 packets, then B1, then B2. Completed known packets are removed; stale or foreign local records are ignored.

The app sums only catalog-supplied lesson `durationMinutes`. It labels the result as a planning allocation from supplied packet display durations. It is not elapsed study time, an expected pace, a completion forecast, a deadline, or a promise of a learning outcome.

The current German inventory has only A1. Its A2 → B2 path is therefore explicitly unavailable rather than inferred.

## Daily and weekly plan

The plan reserves one third of the selected daily allocation for saved-review planning and uses the rest as a supplied-packet display-duration budget. Its review quota is a bounded, deduplicated projection of valid local objective-review, vocabulary, and English grammar queues. It does not identify a learner weakness or retention target.

Weekly targets are catalog-ordered seven-day planning blocks. They have no dates, deadlines, streaks, adherence tracking, or access consequences.

The available-practice rotation lists only supplied activity categories: vocabulary, grammar, reading, transcript-based listening, speaking, writing, and pronunciation when those categories are actually present. It is not a skill score or ability balance. Transcript-based listening is not audio-listening assessment; speaking, writing, and pronunciation remain unscored.

## Adjustment and privacy

The view recalculates from valid browser-local records after hydration, learner selection changes, window focus, and cross-tab storage events. Known supplied completions and valid review queues can change the next packet allocation and review quota. It never changes the learner’s stated bands, unlocks content, sends a provider request, creates an account, transmits data, stores a derived schedule, or records study time.

The page receives only learner-facing static packet labels/routes/durations/activity types. It does not expose raw answers, free-text drafts, prompt bodies, transcripts, or upstream governance records.
