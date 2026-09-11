# M9 Lightweight Development QA Report

**Reviewed at:** 2026-09-11  
**Review mode:** direct current-coding-agent development review  
**Live external AI review:** `NOT_RUN` — no free external runner was available; no provider, model, execution, human-review, release, or provider-authentication evidence is claimed.  
**Scope:** five representative lesson packets (five lessons, five exercise sets, twenty M8.2 prompt artifacts).

## Required automated checks

| Command | Result |
|---|---|
| `python -m pytest` | PASS — 331 passed in 449.16 s |
| `python -m compileall src` | PASS — all source directories compiled without error |
| `git diff --check` | PASS — no whitespace error; Git emitted only LF→CRLF working-copy warnings |
| `python -m english_master.ai_practice verify-pilot --pilot-dir curriculum/ai-practice/pilot-batches/20260905-v13` | PASS — 40 artifacts, 10 lessons, `MACHINE_VALIDATED`; content remains `UNREVIEWED` |

The full test suite includes deterministic validation of schema, authority/reference bindings, CEFR/prerequisite constraints, answer contracts, duplicate/provenance handling, and M8.2 prompt structure. No automatic check was waived.

## Direct representative inspection

The direct review considered English correctness/naturalness, CEFR suitability, teaching clarity, deterministic answer quality, duplicate concerns, scope/prerequisite/provenance consistency, and static prompt-protocol boundaries. Every packet's four modalities were checked for transcript privacy/one-question listening behavior, bounded speaking turns, audio-only pronunciation fallback, and draft-first writing behavior.

| Lesson packet | Lesson SHA-256 | Exercise-set SHA-256 | Prompt SHA-256s (listening / speaking / pronunciation / writing) | Result |
|---|---|---|---|---|
| `A1-U01-L01` | `b30e5dad4d457b2fd2bd1921780330342102fb29e12de70890ced4973842cddc` | `e933e81c04130364969994df895bb4aeba09bb72ed1c679894478a91e81ea0d5` | `17632a3fb9da4dba8856d70224296d83381d087f711027c3b324f95c607869da` / `46d906e53458ce5412664b6cd7b0bf9ef72ab2e5dc7f0fb7ebc2df6b10161d1a` / `91a7fd2b4b26a6b7abc77ab23cdb81db718e78b27854541e167f513f951524fd` / `37691f583c76f959893c4c6091681d62d227f2fd4830447e640fe040c0ec145b` | BLOCKING FINDING |
| `A1-U02-L02` | `749e1aeef8e8c319fc548057bb0e3104c67ef39a8e8397a7cd5b1b8bb93f337a` | `d2a3c659f673879ce9a569e799e79e926486904e758fa84c5c7ff9bbf428e5a8` | `641ce7eded914cd6cc16fc566581be3f98835199da7e700a2a26ff1cd6211428` / `41f7805c2e9f234155d2c743b84b8f580eac1f2bc36e6d97aba0ca24de0eab37` / `ac5cd2f0eb91a973ed82a31396078f1fd5fd147b76244909b092f5b72a0550dc` / `5446371654916785bd3773044852ce05e834605880987bd2986ff13d90b18635` | No blocking issue found |
| `A2-U03-L01` | `34ab10caf897b600242ce639a96cda8eb8e02ecdd79898dca18b847db04bc79e` | `0b9441bf00cfe9b7a19f93fc9fdf7a33fb2bdbbdfdc88711d693d6e1c42fc003` | `f01648dd1bb2847a2e4ef344a009959a06d610d5eed463ff42635cec874a0cfd` / `deefbf44f78635e1a48aa13b284218e06fc1bb3d515f7411379bcadbc508d9f4` / `78cd18a6bde9f620ce35dbb455668ab42f3186e28e98961ef38e4b1e24122445` / `e127335ef34a4e6c6ed901c2925414cab29171aa0c0da616b02240650a9a1181` | No blocking issue found |
| `A2-U04-L02` | `8020beb7338dfc3673948c9c462c0dcd7f8ee9ca93a3e34cc7010d765df0f0ed` | `c87fe37d3449f2c2d4059b4f1ab88871f8f1fa9c847117be377a6f13ce0e1a27` | `c551595cffd408718007b79e3389714dd7ca3718e3874d95dd3d53d8b5be7694` / `08d7ad9901c9219fa070748b6cae0e56273f7656f813a9dadff1f4f182e607a1` / `7ced606f4bc5ca70cd3353784e85b78ca1152e7255b71ec0b6b0919e394931c1` / `f1b5fa9ad6ce0b251b3a2dd1aea0e9b64dafd0dbfb01d6fd5f8bda3d97c5c838` | No blocking issue found |
| `B1-U05-L02` | `a3c4117b3cd1f3bd0e76f57c0ca7e22cf8c7aa270ee99c1b69c9a76a5ea07fad` | `c6af57bcf18d1c7741cb950e3ab26e4c239b195d26a4de760deeb4e1d7cf4292` | `a831a88e0260ccad9ea9ffeeee1492921581bd0de66b28525c21966e88d5faf0` / `6cd7f8b61b6a058359ce1368c184566a62d5e3966c86ccb81bc2d2231a8c572e` / `9008fb3d4a9e6ad3bfe055bf0a06692bfc2ca605eff5143166252e44afb83aac` / `3868daf0e2790843f69545369a2c73441fa4ba0335524ba764915fb7d42cac5a` | BLOCKING FINDING |

The relative paths follow the declared sample layout:

- lessons: `data/generated/m6/development-candidates/20260903-v6-selected/bundles/<lesson-id>/lesson.json`;
- exercise sets: `curriculum/exercises/development-20260903-v2/<lesson-id>/exercise-set.json`, except the current bound `B1-U05-L02` v3 set; and
- prompts: `curriculum/ai-practice/pilot-batches/20260905-v13/prompts/<lowercase-lesson-id>--<modality>.json`.

## Findings

### Blocking — A1 exercise explanation is malformed

`curriculum/exercises/development-20260903-v2/A1-U01-L01/exercise-set.json`, `ex_A1-U01-L01_003`, explains the correct matching as:

> “We takes read; Minh takes reads.”

The mapping itself is correct (`We → read`, `Minh → reads`), but the learner-facing explanation is grammatically malformed and does not clearly explain the rule. At A1.1, this is a blocking English-correctness and teaching-clarity defect.

### Blocking — B1 speaking prompt does not retain its pronunciation target in feedback

`curriculum/ai-practice/pilot-batches/20260905-v13/prompts/b1-u05-l02--speaking.json` sets the communicative goal to “handle past relationships and connected speech” and the lesson declares `concept_pronunciation_linking` as its target. Its `feedback_policy.target_references`, however, contains only `vocab_en_run_002` and `concept_past_perfect`.

The static protocol can therefore complete feedback without addressing the stated connected-speech target. This is a blocking objective-alignment/protocol-clarity defect for the sampled B1 speaking artifact.

### Non-blocking clarity lead — A1 title

`A1-U01-L01` uses the title “Foundational exchange: foundations.” The repetition is awkward and reduces title clarity. It was recorded as a clarity lead, not needed to determine the gate because the two blocking findings already fail it.

## Issues fixed

None. The reviewed lesson, exercise, and prompt artifacts are immutable development artifacts and were not edited in place. M10 was not started.

## Remaining limitations

- Live external AI review is `NOT_RUN`; this direct review is neither independent AI review nor human review.
- The direct review is limited to the declared five-packet sample and does not establish full-population, provider-runtime, learner-outcome, release, or public-distribution evidence.
- Historical M9 v2 and M10 materials were retained and used only as leads; they were not modified.

## Decision

```text
M9 DEVELOPMENT: FAIL
```

Automated checks passed and the complete five-packet sample was inspected, but two blocking sampled content defects remain. Under the active lightweight M9 policy, no M9 pass, M10 start, M11 eligibility, release approval, or commit claim is permitted.
