import { describe, expect, it } from "vitest";
import type { CourseLevel } from "@/content/types";
import { emptyProgress } from "@/lib/progress";
import { emptyReviewProgress, recordObjectiveReviewOutcome } from "@/lib/review-progress";
import { buildPersonalStudyPlan, type StudyPlanCourse } from "@/lib/personal-study-plan";
import type { TutorPreferences } from "@/lib/tutor-context";

const learnerId = "local-learner-001";
const now = "2026-10-09T12:00:00.000Z";
const levels: readonly CourseLevel[] = ["A1", "A2", "B1", "B2", "C1", "C2"];

function course(level: CourseLevel, minutes: readonly number[]): StudyPlanCourse {
  return {
    language: "en",
    level,
    lessons: minutes.map((durationMinutes, index) => ({
      lessonId: `${level.toLowerCase()}-lesson-${index + 1}`,
      title: `${level} lesson ${index + 1}`,
      level,
      sequence: index + 1,
      durationMinutes,
      href: `/learn/en/${level.toLowerCase()}/unit/${level.toLowerCase()}-lesson-${index + 1}`,
      exerciseTypes: index === 0 ? ["reading", "listening"] : [],
      objectiveExerciseIds: index === 0 ? [`${level.toLowerCase()}-exercise-1`] : [],
      practiceModalities: index === 0 ? ["listening", "speaking", "writing", "pronunciation"] : [],
    })),
  };
}

function preferences(overrides: Partial<TutorPreferences> = {}): TutorPreferences {
  return { version: 1, learnerId, language: "en", currentBand: "A2", targetBand: "B2", dailyAllocationMinutes: 45, goals: [], ...overrides };
}

function input(overrides: Partial<Parameters<typeof buildPersonalStudyPlan>[0]> = {}) {
  const courses = [course("A2", [20, 20]), course("B1", [25]), course("B2", [30])];
  return {
    language: "en" as const,
    learnerId,
    preferences: preferences(),
    courses,
    courseProgress: Object.fromEntries(levels.map((level) => [level, emptyProgress({ learnerId, language: "en", course: level })])) as Record<CourseLevel, ReturnType<typeof emptyProgress>>,
    reviewProgress: Object.fromEntries(levels.map((level) => [level, emptyReviewProgress({ learnerId, language: "en", course: level })])) as Record<CourseLevel, ReturnType<typeof emptyReviewProgress>>,
    reviewHref: (level: CourseLevel) => `/learn/en/${level.toLowerCase()}/review`,
    vocabularyHref: "/learn/en/vocabulary",
    grammarHref: "/learn/en/grammar",
    now,
    ...overrides,
  };
}

describe("personal study plan", () => {
  it("orders the A2 remainder through B1 and B2 with a 45-minute allocation", () => {
    const plan = buildPersonalStudyPlan(input());
    expect(plan.status).toBe("READY");
    if (plan.status !== "READY") return;
    expect(plan.remainingLessons.map((lesson) => lesson.level)).toEqual(["A2", "A2", "B1", "B2"]);
    expect(plan.remainingSuppliedDisplayMinutes).toBe(95);
    expect(plan.reviewAllocationMinutes).toBe(15);
    expect(plan.lessonAllocationMinutes).toBe(30);
    expect(plan.dailyLessons.map((lesson) => lesson.lessonId)).toEqual(["a2-lesson-1"]);
    expect(plan.plannedDailyBlocks).toBe(4);
    expect(plan.weeklyBlocks).toHaveLength(1);
    expect(plan.availablePracticeFocus).toEqual(["Vocabulary", "Grammar", "Reading", "Transcript-based listening", "Speaking", "Writing", "Pronunciation"]);
  });

  it("removes only completed current supplied packets from the corridor", () => {
    const base = input();
    const completedA2 = {
      ...base.courseProgress.A2,
      lessons: { "a2-lesson-1": { completed: true, attempts: {}, protocols: {}, drafts: {} }, "stale-lesson": { completed: true, attempts: {}, protocols: {}, drafts: {} } },
    };
    const plan = buildPersonalStudyPlan({ ...base, courseProgress: { ...base.courseProgress, A2: completedA2 } });
    expect(plan.status).toBe("READY");
    if (plan.status !== "READY") return;
    expect(plan.remainingLessons.map((lesson) => lesson.lessonId)).toEqual(["a2-lesson-2", "b1-lesson-1", "b2-lesson-1"]);
  });

  it("keeps packet allocation truthful when the first packet exceeds the lesson share", () => {
    const plan = buildPersonalStudyPlan(input({ preferences: preferences({ dailyAllocationMinutes: 15 }) }));
    expect(plan.status).toBe("READY");
    if (plan.status !== "READY") return;
    expect(plan.lessonAllocationMinutes).toBe(10);
    expect(plan.dailyLessons).toEqual([]);
    expect(plan.plannedDailyBlocks).toBe(4);
  });

  it("caps valid review items and routes objective review to the matching course", () => {
    const base = input();
    const b1Review = recordObjectiveReviewOutcome(base.reviewProgress.B1, {
      lessonId: "b1-lesson-1",
      exerciseId: "b1-exercise-1",
      result: "incorrect",
      reviewedAt: "2026-10-01T12:00:00.000Z",
    });
    const staleReview = recordObjectiveReviewOutcome(base.reviewProgress.A2, {
      lessonId: "a2-lesson-1",
      exerciseId: "removed-exercise",
      result: "incorrect",
      reviewedAt: "2026-10-01T12:00:00.000Z",
    });
    const plan = buildPersonalStudyPlan({ ...base, reviewProgress: { ...base.reviewProgress, A2: staleReview, B1: b1Review } });
    expect(plan.status).toBe("READY");
    if (plan.status !== "READY") return;
    expect(plan.reviewQuota).toEqual([{ source: "Objective review (B1)", itemCount: 1, href: "/learn/en/b1/review" }]);
  });

  it("fails closed for missing choices, foreign preferences, and incomplete corridors", () => {
    expect(buildPersonalStudyPlan(input({ preferences: preferences({ dailyAllocationMinutes: undefined }) })).status).toBe("UNAVAILABLE");
    expect(buildPersonalStudyPlan(input({ preferences: preferences({ learnerId: "another-learner-001" }) })).status).toBe("UNAVAILABLE");
    expect(buildPersonalStudyPlan(input({ courses: [course("A2", [20]), course("B2", [30])] })).status).toBe("UNAVAILABLE");
  });

  it("does not project a German A2 to B2 path from an A1-only inventory", () => {
    const plan = buildPersonalStudyPlan({
      ...input(),
      language: "de",
      preferences: { version: 1, learnerId, language: "de", currentBand: "A2", targetBand: "B2", dailyAllocationMinutes: 45, goals: [] },
      courses: [{ ...course("A1", [20]), language: "de" }],
    });
    expect(plan.status).toBe("UNAVAILABLE");
  });
});
