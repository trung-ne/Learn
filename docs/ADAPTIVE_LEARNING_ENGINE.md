# Browser-Local Adaptive Learning Engine

The Home page's `TODAY` section is a deterministic, browser-local projection of existing learner activity. It supplements **Continue learning**; it does not create a course-lock rule, persist a daily plan, or change any source progress state.

## Inputs and precedence

On Home hydration, the browser selects one course in this order:

1. the valid course with the most recently accessed supplied lesson;
2. the first available course for the active target language; or
3. the first supplied course in stable inventory order.

For that course, the engine can show at most one card in this fixed order:

1. a due English vocabulary review from the existing local WordSense queue;
2. a due English grammar review from the existing explicitly bound grammar queue;
3. transcript-based listening practice after a locally submitted, incorrect English assessment listening item maps to a supplied lesson practice protocol;
4. an unfinished supplied pronunciation prompt after course activity; and
5. the first supplied lesson that is not locally marked complete.

Cards derive again on each hydration from current local state. There is no `TODAY` localStorage record, quota, streak, deadline, random selection, or calendar/scheduling claim. Vocabulary and grammar cards expose only the actual selected item count. A new-lesson card uses only that packet's supplied duration.

## Evidence boundaries

The planner fails closed: malformed time values, mismatched course scopes, unknown inventory identifiers, unsafe destinations, stale assessment hashes, and unavailable practice protocols are omitted. It does not infer an activity from lesson prose.

Vocabulary and grammar queues are English-only and use their existing independent learner-and-language scoped stores. German receives only its course-local continuation/new-lesson recommendation unless a future German-specific local evidence lane and safe target are added. Assessment evidence remains English-only and maps listening only to a supplied **transcript-based** activity; it is not audio-listening assessment and does not diagnose speech rate or a listening cause.

Pronunciation is availability-based rather than score-based. The current protocol inventory does not supply a `/θ/` activity, so the engine does not name `/θ/` or any other sound. It can only invite the learner to open an unfinished supplied prompt, and it records no pronunciation score. Speaking and writing have no scored recommendation category.

`TODAY` uses neutral language such as “review,” “revisit,” and “open.” It never calls an area strong or weak, claims mastery or proficiency, certifies CEFR attainment, diagnoses the learner, unlocks a course, or asserts a learner outcome. The Home UI states this boundary directly: suggestions use activity saved in the browser and are not proficiency or mastery ratings.

## Relationship to other workflows

This is a TypeScript browser projection. It does not invoke, replace, or read artifacts from the offline Python [Adaptive Review](ADAPTIVE_REVIEW.md) workflow. The Python workflow remains a hash-validated file-based planning tool over assessment artifacts; this Home feature reads only its existing browser-local stores and static learner-safe inventory.
