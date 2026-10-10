# Browser-Local Progress Dashboard

The static learner app provides a language-scoped Progress Dashboard at `/learn/{language}/progress`. It combines existing browser-local records into a factual activity summary. It does not create a profile, change course access, make a network request, invoke a provider, or alter source learning content.

## Course packet activity

Each supplied course band shows the number of supplied lesson packets that are locally marked complete divided by the current supplied lesson inventory. Rows are ordered A1 through C2 and omitted when that language has no supplied course at that band.

Course labels are content organization labels. Packet completion is **not** CEFR attainment, proficiency, certification, placement, a learner outcome, or an unlock condition. Stale locally stored lesson identifiers are excluded.

## Skills and local states

The dashboard separates direct objective evidence from self-marked supplied practice:

- **Vocabulary** and **grammar** direct rows show only current submitted assessment items explicitly bound to those dimensions.
- **Reading** shows only supplied submitted reading-item results.
- **Listening** shows only supplied transcript-based submitted items; it is not audio-listening assessment.
- **Speaking** and **writing** are `NOT_ASSESSED`; the browser does not score learner speech or writing.
- Self-marked listening, speaking, pronunciation, and writing protocol completions are activity counts only. They do not score quality, fluency, pronunciation, or audio listening.

Vocabulary records have separate browser-local states:

- `locally mastered`: a current supplied WordSense reached its local `mastered` state;
- `learning or reviewing`: a current supplied WordSense is active but not locally mastered;
- `recorded mistakes`: a current supplied WordSense has one or more recorded incorrect outcomes; and
- `due now`: the existing fixed local schedule says an active sense is due.

Grammar is English-only. It shows current supplied targets that are `locally consolidated`, practising/reviewing, have recorded incorrect outcomes, or are due under the existing local schedule. These labels describe stored objective activity records; they are not grammar competence or a diagnosis.

## Review, mistakes, and unavailable metrics

Objective-review records show reviewed activities, total correct/incorrect outcomes, currently due activities, and latest incorrect outcomes within seven days. These are local objective-review outcomes, **not** a retention measure.

The dashboard makes unavailable measures explicit:

- **Review retention — `NOT_MEASURED`**: scheduling and objective outcomes do not establish delayed retention.
- **Study time — `NOT_RECORDED`**: lesson durations and timestamps are not elapsed study-time telemetry.
- **Mistake trends — `NOT_TRACKED`**: stored aggregates and latest timestamps cannot create daily or weekly trend lines.
- **Speaking, writing, pronunciation, and audio-listening scores — `NOT_ASSESSED`** where no valid supplied local evaluator exists.

Current recorded mistake-pattern counts are aggregate objective outcomes. They identify neither causes nor learner weaknesses.

## Data boundary and language isolation

The dashboard reloads local state after hydration for the current browser-local learner ID. It reads only records matching that learner, language, course, current static inventory version, and known supplied identifiers. Invalid, stale, foreign-language, foreign-learner, and unavailable records are omitted.

English grammar and assessment records never appear on the German dashboard. A missing applicable store is shown as unavailable rather than as zero performance.

For the separate file-based Python scheduling workflow, see [Adaptive Review](ADAPTIVE_REVIEW.md). The browser dashboard does not execute or read that workflow.
