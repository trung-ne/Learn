# M9 Lightweight Development Review Prompt

The active M9 procedure is [M9 Lightweight Development QA](M9_LIGHTWEIGHT_DEVELOPMENT_QA.md).

Use existing deterministic validators and a direct current-coding-agent inspection of five representative lesson packets. Do not require a live external AI runner. If none is available, record live AI review as `NOT_RUN`; do not fabricate AI provider/model/execution evidence and do not call this review independent or human review.

The five packets must cover one lesson, its exercise set, and all four AI-practice modalities for each selected lesson. Review English correctness, naturalness, CEFR suitability, teaching clarity, deterministic answer quality, duplicate concerns, provenance/scope, and static prompt protocol safety.

`M9 DEVELOPMENT: PASS` requires passing pytest, a recorded five-packet inspection, no blocking sampled defect, and no human/release claim. Any blocking defect is `M9 DEVELOPMENT: FAIL`. A pass allows the next explicitly requested development step.

The historical provider-neutral M9 independent-AI framework remains retained but is not the active personal-development gate.
