# M8.2 AI Practice Prompt Pilot

## Boundary

M8.2 creates a development-only, lesson-bound pilot of learner-practice protocols. It uses the verified M6 development batch and produces exactly ten lessons × four modalities = forty immutable prompt artifacts. It is an M8 extension, not M9 independent QA.

Each artifact remains `UNREVIEWED`. The pilot manifest may state only `MACHINE_VALIDATED`; it never claims human review, release approval, provider authentication, a native-speaker review, live-model behavior validation, external media/text use, or an Internet-wide originality search.

## Authority and scope

The builder independently reloads the M5 development snapshot, source registry, M6 development batch, all bound lesson/audit files, and their canonical hashes. It derives every request from that authority, including the lesson ID/hash, CEFR, known/target vocabulary and grammar, functions, pronunciation references, prerequisite context, source sections, and prompt version. Caller data and authored prompt payloads cannot declare these values.

All artifact text is `PROJECT_AUTHORED`. No corpus, audio asset, video, external text payload, or external media is downloaded or embedded. Provider/model/run facts are `UNKNOWN`; `provider_authenticated` is false.

## Protocols

- **Listening:** a private transcript and answer stay hidden from the opening; delivery needs audio or speech; transcript release occurs only after an attempt or allowed explicit request; exactly one queued question is exposed per turn. Text-only completion is `NOT_COMPLETED`.
- **Speaking:** roles, scenario, learner goal, success/stop conditions, bounded turns, and feedback timing are explicit. The assistant asks/invites one thing at a time.
- **Pronunciation:** practice binds M6 pronunciation references. Acoustic assessment needs audio; text-only, unavailable, or inaccessible audio returns `NOT_ASSESSED`, with no score or inferred phonetic judgment.
- **Writing:** the learner supplies a draft before feedback; the protocol moves through `AWAIT_DRAFT`, feedback, and revision. Feedback is bounded, preserves meaning, and forbids a full replacement answer.

The audit verifies the immutable instruction contract, not a future provider's unobserved execution.

## Build and verification

```bash
python -m english_master.ai_practice build-pilot \
  --output-dir <new-immutable-pilot-directory>

python -m english_master.ai_practice verify-pilot \
  --pilot-dir curriculum/ai-practice/pilot-batches/20260905-v13
```

Publication stages authorization, forty requests, forty prompts, forty audits, and a closed manifest before independently verifying the staged directory and atomically renaming it. Existing output is never overwritten, and a new output cannot be nested inside immutable M5/M6 authority evidence or an existing published pilot.

The verifier rebuilds authority, requests, prompt identities/hashes/renderings, audits, the exact 10×4 matrix, and the closed file inventory. It rejects hash and scope drift, cross-lesson substitution, stale audits, status escalation, symlinks, unsafe paths, extra/missing files, and disallowed provenance claims.

## Limits

Passing verification means only that the stored development evidence is internally consistent with the independently reloaded M6 authority. It does not authorize M9, make content approved, or substitute for later independent human linguistic, pedagogical, copyright, or release workflows.
