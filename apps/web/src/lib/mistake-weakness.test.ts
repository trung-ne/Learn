import { describe, expect, it } from "vitest";
import {
  emptyReviewProgress,
  recordObjectiveReviewOutcome,
  reviewItemId,
  type ReviewProgress,
  type ReviewScope,
} from "@/lib/review-progress";
import { deriveActivityOutcomePatterns } from "@/lib/mistake-weakness";

const scope: ReviewScope = { learnerId: "local-learner-001", language: "en", course: "A1" };
const lessonId = "m16a1-v1-a1-u01-l01";
const firstExerciseId = "meaning-check";
const secondExerciseId = "form-match";
const now = "2026-10-02T12:00:00.000Z";

function record(
  progress: ReviewProgress,
  exerciseId: string,
  result: "correct" | "incorrect",
  reviewedAt = now,
): ReviewProgress {
  return recordObjectiveReviewOutcome(progress, { lessonId, exerciseId, result, reviewedAt });
}

describe("activity outcome pattern projection", () => {
  it("projects valid objective outcomes with supplied lesson context and no learner answer data", () => {
    const progress = record(emptyReviewProgress(scope), firstExerciseId, "incorrect");
    const patterns = deriveActivityOutcomePatterns(progress, "en", "A1", now);

    expect(patterns).toHaveLength(1);
    expect(patterns[0]).toMatchObject({
      id: reviewItemId(lessonId, firstExerciseId),
      lessonId,
      exerciseId: firstExerciseId,
      lessonTitle: "Hello and goodbye",
      lessonTopic: "social greetings",
      reviewCount: 1,
      correctCount: 0,
      incorrectCount: 1,
      incorrectOutcomePercent: 100,
      hasIncorrectOutcome: true,
      hasRepeatedIncorrectOutcomes: false,
      isRecentIncorrect: true,
    });
    expect(patterns[0]).not.toHaveProperty("prompt");
    expect(patterns[0]).not.toHaveProperty("answer");
    expect(patterns[0]).not.toHaveProperty("targetIds");
    expect(patterns[0]).not.toHaveProperty("grammarId");
  });

  it("uses two incorrect outcomes as a factual repeated-result threshold", () => {
    const first = record(emptyReviewProgress(scope), firstExerciseId, "incorrect");
    const progress = record(first, firstExerciseId, "incorrect", "2026-10-03T12:00:00.000Z");
    const pattern = deriveActivityOutcomePatterns(progress, "en", "A1", "2026-10-03T12:00:00.000Z")[0]!;

    expect(pattern).toMatchObject({
      reviewCount: 2,
      incorrectCount: 2,
      incorrectOutcomePercent: 100,
      hasRepeatedIncorrectOutcomes: true,
    });
  });

  it("excludes correct-only, stale, and course-mismatched records", () => {
    const correctOnly = record(emptyReviewProgress(scope), firstExerciseId, "correct");
    expect(deriveActivityOutcomePatterns(correctOnly, "en", "A1", now)).toEqual([]);

    const stale = record(emptyReviewProgress(scope), "removed-exercise", "incorrect");
    expect(deriveActivityOutcomePatterns(stale, "en", "A1", now)).toEqual([]);

    const valid = record(emptyReviewProgress(scope), firstExerciseId, "incorrect");
    expect(deriveActivityOutcomePatterns(valid, "en", "A2", now)).toEqual([]);
  });

  it("orders current incorrect results, recurrence, and timestamps deterministically", () => {
    let progress = record(emptyReviewProgress(scope), firstExerciseId, "incorrect", "2026-10-02T09:00:00.000Z");
    progress = record(progress, firstExerciseId, "correct", "2026-10-03T09:00:00.000Z");
    progress = record(progress, secondExerciseId, "incorrect", "2026-10-02T10:00:00.000Z");
    progress = record(progress, secondExerciseId, "incorrect", "2026-10-03T10:00:00.000Z");

    const patterns = deriveActivityOutcomePatterns(progress, "en", "A1", "2026-10-03T12:00:00.000Z");
    expect(patterns.map((pattern) => pattern.exerciseId)).toEqual([secondExerciseId, firstExerciseId]);
  });
});
