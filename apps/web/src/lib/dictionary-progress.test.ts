import { describe, expect, it } from "vitest";
import {
  dictionaryStatus,
  emptyDictionaryProgress,
  parseDictionaryProgress,
  recordDictionaryOutcome,
  startDictionaryEntry,
} from "@/lib/dictionary-progress";

const scope = { learnerId: "local-learner-001", language: "en" as const };
const version = "dictionary-v1";
const entryId = "dict-en-take-001";
const now = "2026-10-09T12:00:00.000Z";

describe("dictionary progress", () => {
  it("maps absent, started, incorrect, and repeated correct local records to the four markers", () => {
    const empty = emptyDictionaryProgress(scope, version);
    expect(dictionaryStatus(empty.entries[entryId])).toBe("not_learned");
    const started = startDictionaryEntry(empty, entryId, now);
    expect(dictionaryStatus(started.entries[entryId])).toBe("learning");
    const weak = recordDictionaryOutcome(started, entryId, false, now);
    expect(dictionaryStatus(weak.entries[entryId])).toBe("weak");
    let learned = started;
    for (let index = 0; index < 3; index += 1) learned = recordDictionaryOutcome(learned, entryId, true, now);
    expect(dictionaryStatus(learned.entries[entryId])).toBe("learned");
  });

  it("fails closed for a foreign, stale, or malformed record", () => {
    expect(parseDictionaryProgress(JSON.stringify({
      version: 1,
      learnerId: "other-learner-001",
      language: "en",
      inventoryVersion: version,
      entries: {},
    }), scope, version, [entryId])).toEqual(emptyDictionaryProgress(scope, version));
    const parsed = parseDictionaryProgress(JSON.stringify({
      version: 1,
      ...scope,
      inventoryVersion: version,
      entries: {
        [entryId]: { startedAt: now, correctCount: 0, incorrectCount: 0 },
        "not-current": { startedAt: now, correctCount: 3, incorrectCount: 0 },
      },
    }), scope, version, [entryId]);
    expect(Object.keys(parsed.entries)).toEqual([entryId]);
  });
});
