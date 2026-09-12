# A2 pilot

The bounded A2 pilot builds the first ten A2.1 lesson outlines (units 1–2) into original learner packets. Each packet contains short lesson sections, four exercises, and listening, speaking, pronunciation, and writing protocols.

Validation is offline and deterministic: M15/A2 references, packet hashes, closed inventory, outline targets and prerequisites, exercise answer/rubric contracts, four protocol boundaries, and duplicate learner-facing text. Listening is transcript-only and private before the first answer; pronunciation returns `NOT_ASSESSED` without learner audio; writing is draft-first feedback only. No network, live provider, external media, human/release claim, or public-distribution claim is made. Content remains `UNREVIEWED`.

Commands:

```text
python -m english_master.a2_pilot.cli build ...
python -m english_master.a2_pilot.cli verify RUN_DIR --population ... --blueprint ...
python -m english_master.a2_pilot.cli audit RUN_DIR --population ... --blueprint ... --output REPORT
python -m english_master.a2_pilot.cli sample RUN_DIR --population ... --blueprint ... --audit-report REPORT --seed SEED --output SAMPLE
```

The deterministic sample is an inspection aid, not a release or comprehensive quality claim.
