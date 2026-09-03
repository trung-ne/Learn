# Source research, quarantine, and review protocol

**Research reviewed:** 2026-08-30; amended 2026-09-03 for ERIC EJ527841. All links named here are official sources and are also recorded per source in [registry.yaml](registry.yaml). This is a conservative operational assessment, not legal advice.

## Why items are not automatically approved

| Candidate | Decision | Evidence-based restriction |
| --- | --- | --- |
| Council of Europe CEFR Companion Volume | Reference only | Official publishing and permissions material does not make the content an open corpus. Use for CEFR taxonomy and coverage review, not extraction or copying. |
| ERIC EJ527841 / Osburne (1996) | Reference only | The exact bibliographic locator supports a narrow citation to a single-participant case study. No article payload may be copied, stored, adapted, ingested, redistributed, or used in exercises; the registered query-specific locator does not authorize other ERIC records. |
| English Profile EVP | Quarantined | The site is publicly available, but no official bulk/API/reuse permission was verified in this review. |
| Cambridge specifications | Reference only | Official public specifications, regulations, and sample resources remain controlled educational materials. |
| British Council learning resources | Reference only | Rights can vary at item level; a site-wide, redistributable ingestion license was not established. |
| VOA Learning English | Quarantined | VOA's own policy distinguishes exclusively VOA-produced material from third-party components. Page-level clearance is insufficient for text, image, audio, video, transcript, clip, or redistribution decisions. |
| Tatoeba audio without affirmative offsite license | Quarantined | Record-level attribution does not supply a license; blank/unknown/offsite-prohibited fields fail closed. |

## VOA asset-review protocol

No VOA page is approved as a general corpus. A future request requires a new asset-level record and evidence proving all of the following:

1. The exact text, audio, video, image, music, graphic, caption, and embedded component is produced exclusively by VOA or separately licensed for the intended use.
2. The asset's original, derivative, and distribution rights are individually entered for its medium.
3. Agency content (including AP, Reuters, AFP), stock media, third-party photographs, music, and unclear credits are excluded unless separately approved.
4. Any VOA usage-request or U.S. distribution restriction is satisfied and documented.
5. Transcript generation and audio extraction receive their own affirmative rights decision.

Absent any one item, retain `QUARANTINED` and do not download or process the asset.

## Quarantine review workflow

1. Open a review record with the source/asset ID, intended operation, official evidence URL, evidence date, reviewer, and the exact unresolved question.
2. Confirm the asset's license and terms directly with the rights holder or authoritative terms page.
3. Evaluate text, audio, video, original redistribution, derived redistribution, clips, transcripts, timestamps, and extraction independently.
4. Verify technical access is authorized: no login bypass, paywall bypass, robots violation, or rate-limit bypass.
5. If every required right is affirmative, update the registry evidence and review notes, then permit only the specific operation.
6. Otherwise keep the asset quarantined. Rejected sources require a documented incompatible or prohibited right; no artificial rejected source was created merely to fill a category.

## Evidence refresh triggers

Re-review before a future operation if the terms page changes, the access path changes, a source releases a new version, an item has third-party components, or the intended use is broader than the current record. Do not rely on an old approval to authorize a different medium or derivative use.
