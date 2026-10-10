import { describe, expect, it } from "vitest";
import {
  emptyReviewProgress,
  isObjectiveExerciseType,
  parseReviewProgress,
  recordObjectiveReviewOutcome,
  reviewItemId,
  reviewProgressKey,
  selectReviewCandidates,
  type ReviewScope,
} from "@/lib/review-progress";

const scope: ReviewScope = { learnerId: "local-learner-001", language: "en", course: "A1" };
const lessonId = "a1-u01-l01";
const exerciseId = "a1-u01-l01-ex-01";
const firstSeenAt = "2026-10-02T12:00:00.000Z";

function outcome(result: "correct" | "incorrect", reviewedAt = firstSeenAt) {
  return { lessonId, exerciseId, result, reviewedAt } as const;
}

describe("unified objective review progress", () => {
  it("isolates its key by learner, language, and course", () => {
    expect(reviewProgressKey(scope)).toBe("english-master.review.v1.local-learner-001.en.A1");
    expect(reviewProgressKey({ ...scope, course: "A2" })).not.toBe(reviewProgressKey(scope));
    expect(reviewProgressKey({ ...scope, language: "de" })).not.toBe(reviewProgressKey(scope));
  });

  it("uses the 10-minute, 1/3/7/14/30/60-day ladder for consecutive correct outcomes", () => {
    let progress = emptyReviewProgress(scope);
    const timestamps = [
      "2026-10-02T12:00:00.000Z",
      "2026-10-02T12:10:00.000Z",
      "2026-10-03T12:10:00.000Z",
      "2026-10-06T12:10:00.000Z",
      "2026-10-13T12:10:00.000Z",
      "2026-10-27T12:10:00.000Z",
      "2026-11-26T12:10:00.000Z",
    ];
    const intervals = [10 * 60_000, 24 * 60 * 60_000, 3 * 24 * 60 * 60_000, 7 * 24 * 60 * 60_000, 14 * 24 * 60 * 60_000, 30 * 24 * 60 * 60_000, 60 * 24 * 60 * 60_000];

    timestamps.forEach((reviewedAt, index) => {
      progress = recordObjectiveReviewOutcome(progress, outcome("correct", reviewedAt));
      const item = progress.items[reviewItemId(lessonId, exerciseId)]!;
      expect(item.intervalIndex).toBe(index);
      expect(item.nextReviewAt).toBe(new Date(Date.parse(reviewedAt) + intervals[index]!).toISOString());
    });

    const final = progress.items[reviewItemId(lessonId, exerciseId)]!;
    expect(final).toMatchObject({ reviewCount: 7, correctCount: 7, incorrectCount: 0, mastery: 100, ease: 3 });
  });

  it("resets the interval on an incorrect factual outcome and retains only aggregate evidence", () => {
    const afterCorrect = recordObjectiveReviewOutcome(emptyReviewProgress(scope), outcome("correct"));
    const afterIncorrect = recordObjectiveReviewOutcome(afterCorrect, outcome("incorrect", "2026-10-03T12:00:00.000Z"));
    expect(afterIncorrect.items[reviewItemId(lessonId, exerciseId)]).toEqual({
      lessonId,
      exerciseId,
      firstSeenAt,
      lastReviewedAt: "2026-10-03T12:00:00.000Z",
      reviewCount: 2,
      correctCount: 1,
      incorrectCount: 1,
      ease: 2.4,
      intervalIndex: 0,
      mastery: 50,
      nextReviewAt: "2026-10-03T12:10:00.000Z",
      lastResult: "incorrect",
    });
  });

  it("rejects malformed, scope-mismatched, and future-overwritten records", () => {
    expect(parseReviewProgress("not json", scope)).toEqual(emptyReviewProgress(scope));
    const malformed = { ...emptyReviewProgress(scope), items: { bad: {} } };
    expect(parseReviewProgress(JSON.stringify(malformed), scope)).toEqual(emptyReviewProgress(scope));
    const valid = recordObjectiveReviewOutcome(emptyReviewProgress(scope), outcome("correct"));
    expect(parseReviewProgress(JSON.stringify(valid), { ...scope, course: "A2" })).toEqual(emptyReviewProgress({ ...scope, course: "A2" }));
    expect(recordObjectiveReviewOutcome(valid, outcome("correct", "2026-10-01T12:00:00.000Z"))).toEqual(valid);
  });

  it("selects recent incorrect candidates before due candidates with stable tie-breaking", () => {
    const candidates = selectReviewCandidates([
      { source: "vocabulary_sense", id: "vocab-two", dueAt: "2026-10-02T11:00:00.000Z", priority: "due", order: 2 },
      { source: "objective_exercise", id: "exercise-one", dueAt: "2026-10-02T11:00:00.000Z", priority: "recent_incorrect", order: 1 },
      { source: "vocabulary_sense", id: "vocab-one", dueAt: "2026-10-02T11:00:00.000Z", priority: "recent_incorrect", order: 0 },
      { source: "objective_exercise", id: "not-due", dueAt: "2026-10-02T12:10:00.000Z", priority: "recent_incorrect", order: 0 },
    ], firstSeenAt);
    expect(candidates.map((candidate) => candidate.id)).toEqual(["vocab-one", "exercise-one", "vocab-two"]);
  });

  it("identifies only exercise types with deterministic local answer checks", () => {
    expect(isObjectiveExerciseType("multiple_choice")).toBe(true);
    expect(isObjectiveExerciseType("listening")).toBe(true);
    expect(isObjectiveExerciseType("writing")).toBe(false);
    expect(isObjectiveExerciseType("speaking")).toBe(false);
  });
});
