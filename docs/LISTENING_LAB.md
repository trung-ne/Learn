# Listening Lab

## Purpose and current availability

The Listening Lab is the future audio-first practice space for the sequence below:

1. listen without a transcript;
2. answer meaning;
3. listen again;
4. complete a dictation attempt;
5. reveal the supplied transcript and compare it locally;
6. replay supplied sentence ranges;
7. shadow without recording or scoring; and
8. complete a final local listen marker.

The committed inventory deliberately contains `NO_AUTHORIZED_MEDIA` and no sessions. No audio, video, caption, M12 payload, M13 transcript, M14 metric result, or synthetic playback is included. Therefore the route displays an availability notice and no learner can complete this sequence in the current static application.

Existing lesson listening protocols remain separate **transcript-only** practice. They are not playable media and cannot be presented as Listening Lab completion.

## Authorization boundary

A future session requires a separately requested, explicit browser-delivery handoff. M12 `storage`, transcript, and timestamp permissions do not establish browser delivery or redistribution authority. M13 transcript artifacts and M14 profiles are not placed in the web snapshot: browser concealment is a user-interface convention, not a confidentiality boundary.

A future source inventory must have explicit authorization for both browser audio delivery and browser transcript disclosure. The deterministic builder currently accepts only the empty `UNREVIEWED` sentinel; it fails closed for a purported media inventory until the source-handoff contract is deliberately added and validated. This prevents an M12/M13 fixture or local media file from becoming web content by implication.

## Metadata and privacy

A future browser record may show only supplied metadata: accent label, anonymous within-session speaker labels, pace label, lesson-target CEFR band, topic, grammar/vocabulary labels, and phonetic-feature labels. The application must not infer those fields from transcript text, titles, M15 data, M14 proxy metrics, or media bytes.

Speaker labels are restricted to anonymous `SPEAKER_NN` values. The app retains no names, demographics, biometric inferences, or cross-session identities.

## Local learner state

When an authorized session exists, state is local to the browser under:

```text
english-master.listening-lab.v1.<learnerId>.en.<course>
```

Only ordered workflow markers, counts, and timestamps are eligible for persistence. Typed meaning answers, dictation text, transcript copies, media data, microphone data, recordings, and external-provider data remain in component memory or are not collected at all.

A local final marker is not evidence of listening ability, pronunciation, CEFR attainment, proficiency, completion authority, human review, release approval, or provider behavior. Listening Lab activity does not update review, grammar, vocabulary, or Mistake/Weakness records.

## Validation

Use the deterministic check for the committed availability snapshot:

```bash
cd apps/web
node scripts/check-listening-snapshot.mjs
```

The general web build runs that check in `prebuild`. Full npm validation remains blocked until a complete local dependency installation is available; see [Web Validation Blockers](WEB_VALIDATION_BLOCKERS.md).
