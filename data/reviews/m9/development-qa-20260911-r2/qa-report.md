# M9 Lightweight Development QA Report — Fresh Follow-up

**Reviewed at:** 2026-09-11T12:49:47Z  
**Review mode:** direct current-coding-agent development review  
**Live external AI review:** `NOT_RUN` — no free external runner was used. This report makes no provider, model, human-review, release, provider-authentication, or runtime-behavior claim.  
**Scope:** five representative lesson packets: five M6 lessons, five M7 exercise sets, and twenty M8.2 v10 prompt artifacts.

## M10 successor binding

This is a fresh review rather than a modification of the failed report at `data/reviews/m9/development-qa-20260911/qa-report.md`.

- A1-U01-L01 uses the new M7 successor `curriculum/exercises/development-20260911-m10-r2/A1-U01-L01/`. Its independently verified M10 run is `data/reviews/m10/successor-runs/20260911-a1-u01-l01-m7-r2-v3/` (`READY_FOR_FRESH_M9`).
- All prompt packets use the new complete M8.2 v10 pilot `curriculum/ai-practice/pilot-batches/20260911-v14-m10/`. The B1-U05-L02 speaking successor is bound by `data/reviews/m10/successor-runs/20260911-b1-u05-l02-m8-2-speaking-r2-v3/` (`READY_FOR_FRESH_M9`).
- Both M10 terminal states mean only that their static successor evidence passed and a fresh M9 was required. They do not approve content. All reviewed content remains `UNREVIEWED`.

## Required automated checks

| Command | Result |
|---|---|
| `python -m pytest` | PASS — 333 passed in 396.47 s |
| `python -m compileall src` | PASS |
| `git diff --check` | PASS — no whitespace errors; Git emitted existing LF→CRLF working-copy warnings |
| `python -m english_master.ai_practice verify-pilot --pilot-dir curriculum/ai-practice/pilot-batches/20260911-v14-m10` | PASS — 40 artifacts, 10 lessons, `MACHINE_VALIDATED`, `UNREVIEWED` |
| `python -m english_master.revision_cycle verify-run data/reviews/m10/successor-runs/20260911-a1-u01-l01-m7-r2-v3` | PASS — six receipts; dereferenced M7 artifact and audit evidence |
| `python -m english_master.revision_cycle verify-run data/reviews/m10/successor-runs/20260911-b1-u05-l02-m8-2-speaking-r2-v3` | PASS — six receipts; independently reverified full 40-artifact M8.2 pilot and selected member |

No automated check was waived.

## Direct representative inspection

The direct review checked English correctness and naturalness, CEFR suitability, teaching clarity, objective-answer quality, duplicate concerns, scope/prerequisite/provenance consistency, and static prompt protocol boundaries. For every packet, the four modalities were checked for hidden transcript/one-question listening behavior, bounded speaking turns, audio-only pronunciation fallback, and draft-first writing boundaries.

| Lesson packet | Lesson SHA-256 | Exercise-set SHA-256 | Prompt SHA-256s (listening / speaking / pronunciation / writing) | Result |
|---|---|---|---|---|
| `A1-U01-L01` | `a09a20b10fd36cbfdfd05a12debfebf4e5fd83dfe38e1f2448a38f5a6ae79770` | `453e2c78fbf891dcd49e55de5da22340e34c63f0c6b5e908d8c568636b2eb1f6` | `ab0e2d317b5b29dbcdb3ed411e58d8731dac2646bcf36bca5040f44932b81011` / `6b43e86761ea5cbd25ba393c6df0b6af436f17ea76cb3fca236c5f2e55036548` / `b727f96ffe6c274caa2a40a3ca99aae699872981a456d2dc552fdb11ec87eff7` / `372c9aaebc5b04c28d667025ef2b96a1d925fab552eae88bf2cb8830deed72b6` | PASS |
| `A1-U02-L02` | `20326bacfa8989b614ddff53eda46a8103ee118ad8460e59a4553c5f10d5206c` | `b47b259e94eb182d56b6aa47374b0ec4a26bb1dc0199f227b6935faf32166ce0` | `4696e3b3714f27f088380cf1ea9ddd58f7bab917c388879243ae9cb35f28fb8a` / `71cdfb44707d7aab28ffb80cd8d9116013126a8b20ae36c4062db5a9aa8dcbc3` / `29dd2a5e9aee13188afb4c4d593e0f37826cfb956f0353152a0dd1dc81b86caf` / `8f2a0e25780656bd4e0eaed2d89a437597388a0496dafd8ba3525a05083ade2f` | PASS |
| `A2-U03-L01` | `57bb8713d795194e2ec59c422f7507e5c16651cd83627f7f99dafa3df15f0549` | `76de7997629a097ff09f9bf9ecc4a86c7d0fd03f80e598a78ce3bd93eb471bda` | `af76b8b8c016bf5cabc71287ab526148e5bb2db6fc35e358a318aa52aa14e6cd` / `06bf90270adf781de09134a7fe946a9a6597c0772ae68b4555c351ebaff7e7ac` / `57778358d664477ad9c0f6cb2fffc56f9731519c12eddb48fac22793bead8ca4` / `a3b102f885f7677fb2f021e6daecfd4b1c8ba6f0b9eb794baec480bf64ba4191` | PASS |
| `A2-U04-L02` | `c517aa8dc82a1c9fdd8ea7a0c475c3bcdb4d4f10f2b0655d8be9bbf1621d6381` | `7d4f534557d860a44c3a546f9493a13f47e549c6098c36057350905844ae5fc5` | `7dec99c4a50530c0abccdd2495f4afc2d983c5e0c0207716f9f97b10eeacb4ca` / `a5d5b2de7842aaa81712dca5ebf492decab338080dd7176a06525a2b189ee18f` / `7eb9a88314536ca77ec0bd623a360c6d1961c0027c5d4aefbf3b0a6ae52d8954` / `78b6ddc8f4a78fae2b43a912b68fe3cf915debea84a0f15e9654d828dcbf0422` | PASS |
| `B1-U05-L02` | `9e6b0d0cac4a38c62e6f1a91d57c03ac23bdd0055a2b3ff29ed013d21cbb71de` | `cea10fcb880534feba6afa9f0c854fa3809d223b31de61ea695eab4b81953f8e` | `4b1ac841c77c0f304f711be4e501f938374860045f0d5814ba29affbfd6ebd9c` / `49d282aecff1621cb7769b227e69cb830917d7ae3a6a652ac60708d6342231af` / `01277b3098535d48b899a8c6a6d1a4a6d18fcffe3ec4bf20f65fab8a197ab05d` / `f523c7f50ffde314777383c410857e42fd37c890429830b3184fd4837c207048` | PASS |

### Confirmed repair checks

- The A1-U01-L01 matching explanation now says: “Use read with we. Use reads with Minh because Minh is third-person singular.” The mapping is still correct and the wording is grammatical, direct, and suitable for A1.1.
- The B1-U05-L02 speaking feedback now retains `vocab_en_run_002`, `concept_past_perfect`, `concept_pronunciation_linking`, and `concept_pronunciation_weak_forms`. Its new pronunciation-feedback policy requires audio; without audio it returns `NOT_ASSESSED` and prohibits score, phonetic-correctness, and accent claims.
- The previous A1 title clarity lead remains a non-blocking observation. It is not represented as repaired because the M6 predecessor is immutable and the active lightweight M9 pass does not turn a non-blocking lead into a new required M10 scope.

## Remaining limitations

- Live external AI review is `NOT_RUN`; direct coding-agent inspection is neither independent AI evidence nor human review.
- The review is limited to its declared five-packet sample. It does not establish full-population quality, provider runtime behavior, learner outcomes, public distribution, human review, or release approval.
- M8.2 evidence remains static protocol validation only; it does not establish audio delivery, turn handling, pronunciation scoring, writing-feedback execution, or learner outcomes.

## Decision

```text
M9 DEVELOPMENT: PASS
```

All prescribed automated checks passed, all five fresh packet bindings were inspected, and no blocking sampled defect remains. The result remains development-only: every content artifact is `UNREVIEWED`; it does not begin M11 or establish human or release approval.
