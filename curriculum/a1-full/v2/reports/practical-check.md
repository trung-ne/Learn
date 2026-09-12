# A1 practical check — v2 successor

## Scope

This direct inspection used the deterministic twelve-lesson sample in
[`../samples/sample-12.json`](../samples/sample-12.json). It covers all ten
units; units 2 and 6 each contribute a second lesson.

Inspected lessons:

- `m16a1-v1-a1-u01-l04`
- `m16a1-v1-a1-u02-l01`
- `m16a1-v1-a1-u02-l02`
- `m16a1-v1-a1-u03-l03`
- `m16a1-v1-a1-u04-l02`
- `m16a1-v1-a1-u05-l01`
- `m16a1-v1-a1-u06-l02`
- `m16a1-v1-a1-u06-l03`
- `m16a1-v1-a1-u07-l01`
- `m16a1-v1-a1-u08-l01`
- `m16a1-v1-a1-u09-l02`
- `m16a1-v1-a1-u10-l01`

## Direct findings

No `BLOCKER` was found: the selected lessons preserve target references and
prerequisite order, keep listening transcripts private before the attempt,
retain the no-media boundary, include the four required modalities, and state
a concrete pronunciation focus.

### IMPORTANT — repeated generic learner prose

Every sampled lesson uses substantially the same explanation, context, and
practice frames. The Vietnamese guidance is understandable, but it is the
same generic advice rather than an explanation of the specific grammar or
communicative decision. The lessons therefore do not provide enough
lesson-specific form, meaning, and use support for independent A1 study.

### IMPORTANT — roleplays are structurally marked but not genuinely situated

Every sampled speaking protocol names roles, a scenario, and an opening, but
uses the same abstract situation ("a short everyday interaction") and the
same follow-up/completion path. It does not consistently provide a
lesson-specific information gap, realistic tutor role, or usable turn path.
The marker-based compiler lint is insufficient to establish an executable
roleplay.

### IMPORTANT — exercise design remains shallow and sometimes defective

The generated exercise template still includes artificial distractors and
matching pairs about a lesson/topic rather than meaningful language choices.
For example, matching a model sentence to "A model sentence for ..." does
not test practical English use. In `m16a1-v1-a1-u10-l01`, the fill-blank
answer is not found in the chosen model sentence, so the compiled prompt has
no blank while retaining an answer key. This is a concrete answer-quality
failure. Similar template logic can affect other fill-blank lessons.

### IMPORTANT — duration is not supported by visible learning work

The replacement lessons declare 30 minutes but normally contain three short,
repeated sections and three shallow exercises. The visible material does not
credibly support the stated duration without adding specific guided practice
and context.

### MINOR — improvements that are present but need further authoring depth

- Listening now uses distinct, private, project-authored transcripts and
  single comprehension questions.
- Pronunciation now identifies a concrete sound, stress, rhythm, linking, or
  contrast action.
- The route example uses natural `the number 6 bus` wording rather than the
  prior unnatural form.
- There were no obvious out-of-scope vocabulary jumps in the sampled material.

## Systemic changes made before this inspection

The v2 successor preserves v1 unchanged and adds a retained 50-card source,
a no-overwrite compiler, a separate v2 manifest/run, and lints for known v1
failures: legacy metadata text, visible listening transcripts, missing basic
roleplay markers, generic pronunciation markers, missing coverage, and scope
drift. The resulting v2 run verifies and its structural audit passes.

Those changes fixed the previously exposed transcript and pronunciation
problems, but the direct inspection shows that template-level learner prose,
roleplay design, exercise design, and duration support still require a
substantial authoring repair. A marker lint alone is not sufficient.

## Validation executed

- `python -m pytest` — **PASS**: 401 passed.
- `python -m english_master.project_audit` — **PASS**: no consistency issues.
- v2 run verification — **PASS**.
- v2 lightweight structural audit — **PASS**.
- v2 deterministic twelve-lesson sample generation — **PASS**.

These automated results are consistency and contract checks only. They do not
establish prose quality, pedagogical quality, approval, release authority,
provider behavior, or learner outcomes.

## Limitations and next action

This was a bounded twelve-lesson direct inspection, not a review of all fifty
lessons. Because repeated `IMPORTANT` issues remain in the source/compiler
content policy, the appropriate repair is to replace the common lesson cards
with genuinely lesson-specific explanations, situations, exercises, roleplay
paths, and writing tasks; it should not be a series of packet-only edits.

All generated material remains `UNREVIEWED`. No human-review, release,
provider, live-AI, external-media, or public-distribution claim is made.

**A1 PRACTICAL CHECK: FAIL**
