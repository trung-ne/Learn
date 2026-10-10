import { describe, expect, it } from "vitest";
import {
  emptyVocabularyProgress,
  parseVocabularyProgress,
  recordWordSenseResult,
  selectVocabularyReviewQueue,
  startWordSense,
  vocabularyProgressKey,
  type VocabularyScope,
} from "@/lib/vocabulary-progress";

const scope: VocabularyScope = { learnerId: "local-learner-001", language: "en" };
const startedAt = "2026-10-02T12:00:00.000Z";
const senseId = "web-vocab-en-a1-u01-hello-001";

function started() {
  return startWordSense(emptyVocabularyProgress(scope, "v1"), senseId, startedAt);
}

describe("WordSense local learning lifecycle", () => {
  it("isolates state by learner and language without changing course progress keys", () => {
    expect(vocabularyProgressKey(scope)).toBe("english-master.vocabulary.v1.local-learner-001.en");
    expect(vocabularyProgressKey({ ...scope, language: "de" })).not.toBe(vocabularyProgressKey(scope));
    expect(vocabularyProgressKey({ ...scope, learnerId: "local-learner-002" })).not.toBe(vocabularyProgressKey(scope));
  });

  it("starts an explicit new sense without creating an attempt", () => {
    const progress = started();
    expect(progress.senses[senseId]).toMatchObject({
      state: "learning", attempts: 0, correctAttempts: 0, mistakes: 0, masteryScore: 0,
      intervalIndex: 0, introducedAt: startedAt, nextReviewAt: startedAt,
    });
  });

  it("uses the 1/3/7/14/30/60 day schedule and only masters after its final successful interval", () => {
    let progress = started();
    const days = [1, 3, 7, 14, 30, 60];
    for (let index = 0; index < days.length; index += 1) {
      const now = `2026-10-${String(2 + index).padStart(2, "0")}T12:00:00.000Z`;
      progress = recordWordSenseResult(progress, senseId, true, now);
      const result = progress.senses[senseId]!;
      expect(result.nextReviewAt).toBe(new Date(Date.UTC(2026, 9, 2 + index + days[index]!, 12)).toISOString());
      expect(result.state).toBe(index === 5 ? "mastered" : "reviewing");
      expect(result.intervalIndex).toBe(Math.min(index + 1, 5));
    }
  });

  it("records mistakes, recalculates mastery, and resets interval state", () => {
    const afterCorrect = recordWordSenseResult(started(), senseId, true, startedAt);
    const afterMistake = recordWordSenseResult(afterCorrect, senseId, false, "2026-10-03T12:00:00.000Z");
    expect(afterMistake.senses[senseId]).toMatchObject({
      state: "learning", attempts: 2, correctAttempts: 1, mistakes: 1, masteryScore: 50,
      intervalIndex: 0, lastMistakeAt: "2026-10-03T12:00:00.000Z", nextReviewAt: "2026-10-04T12:00:00.000Z",
    });
  });

  it("rejects malformed state and chooses recent mistakes before other due senses", () => {
    expect(parseVocabularyProgress("not json", scope, "v1")).toEqual(emptyVocabularyProgress(scope, "v1"));
    const malformed = { ...started(), senses: { "../bad": started().senses[senseId] } };
    expect(parseVocabularyProgress(JSON.stringify(malformed), scope, "v1")).toEqual(emptyVocabularyProgress(scope, "v1"));

    let progress = recordWordSenseResult(started(), senseId, false, startedAt);
    progress = recordWordSenseResult(progress, "web-vocab-en-a1-u01-goodbye-001", true, startedAt);
    const queue = selectVocabularyReviewQueue(progress, [
      { senseId: "web-vocab-en-a1-u01-goodbye-001", introductionOrder: 1 },
      { senseId, introductionOrder: 0 },
    ], "2026-10-04T12:00:00.000Z");
    expect(queue).toEqual([senseId, "web-vocab-en-a1-u01-goodbye-001"]);
  });
});
