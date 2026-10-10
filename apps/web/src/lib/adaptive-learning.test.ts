import { describe, expect, it } from "vitest";
import { getAssessmentPackage } from "@/content/assessment-catalog";
import { getGrammarTargets, grammarSnapshot } from "@/content/grammar-catalog";
import { getVocabularySenses, vocabularySnapshot } from "@/content/vocabulary-catalog";
import { buildTodayRecommendations, type AdaptiveCourseInventory } from "@/lib/adaptive-learning";
import { emptyAssessmentProgress } from "@/lib/assessment-progress";
import { emptyGrammarProgress, recordGrammarTargetResult } from "@/lib/grammar-progress";
import { emptyProgress } from "@/lib/progress";
import { emptyVocabularyProgress, recordWordSenseResult } from "@/lib/vocabulary-progress";

const course: AdaptiveCourseInventory = {
  language: "en",
  level: "A1",
  lessons: [
    { lessonId: "m16a1-v1-a1-u01-l01", title: "First lesson", sequence: 1, href: "/learn/en/A1/m16a1-v1-a1-u01/m16a1-v1-a1-u01-l01", hasListeningPractice: true, hasPronunciationPractice: true, durationMinutes: 15 },
    { lessonId: "m16a1-v1-a1-u01-l02", title: "Second lesson", sequence: 2, href: "/learn/en/A1/m16a1-v1-a1-u01/m16a1-v1-a1-u01-l02", hasListeningPractice: true, hasPronunciationPractice: true, durationMinutes: 15 },
  ],
};

const scope = { learnerId: "local-learner-001", language: "en" as const, course: "A1" as const };
const now = "2026-10-09T12:00:00.000Z";

describe("browser-local adaptive learning recommendations", () => {
  it("suggests the first incomplete supplied lesson without claiming a learner score", () => {
    const recommendations = buildTodayRecommendations({ course, courseProgress: emptyProgress(scope), now });

    expect(recommendations).toEqual([expect.objectContaining({
      category: "new_lesson",
      title: "New lesson",
      href: course.lessons[0]!.href,
      durationMinutes: 15,
    })]);
  });

  it("orders due vocabulary and grammar activities before the next lesson", () => {
    const sense = getVocabularySenses("en").find((candidate) => candidate.band === "A1")!;
    const target = getGrammarTargets("en").find((candidate) => candidate.band === "A1")!;
    const vocabulary = recordWordSenseResult(
      emptyVocabularyProgress({ learnerId: scope.learnerId, language: "en" }, vocabularySnapshot.inventoryVersion),
      sense.id,
      false,
      "2026-10-08T12:00:00.000Z",
    );
    const grammar = recordGrammarTargetResult(
      emptyGrammarProgress({ learnerId: scope.learnerId, language: "en" }, grammarSnapshot.inventoryVersion),
      target.id,
      false,
      "2026-10-08T12:00:00.000Z",
    );
    const recommendations = buildTodayRecommendations({
      course,
      courseProgress: emptyProgress(scope),
      now,
      vocabularyProgress: vocabulary,
      grammarProgress: grammar,
    });

    expect(recommendations.map((item) => item.category)).toEqual(["vocabulary", "grammar", "new_lesson"]);
    expect(recommendations[0]?.detail).toContain("saved vocabulary");
    expect(recommendations[1]?.detail).toContain(target.title);
  });

  it("links an incorrect bound listening result only to supplied transcript-based practice", () => {
    const assessment = getAssessmentPackage("lesson-quiz-m16a1-v1-a1-u01-l04")!;
    const listeningCourse: AdaptiveCourseInventory = {
      ...course,
      lessons: [{ lessonId: "m16a1-v1-a1-u01-l04", title: "Alphabet and spelling", sequence: 4, href: "/learn/en/A1/m16a1-v1-a1-u01/m16a1-v1-a1-u01-l04", hasListeningPractice: true, hasPronunciationPractice: false, durationMinutes: 15 }],
    };
    const progress = {
      ...emptyAssessmentProgress({ learnerId: scope.learnerId, language: "en" }),
      packages: {
        [assessment.id]: {
          packageSha256: assessment.packageSha256,
          attempts: [{
            attemptId: "attempt-listening",
            packageSha256: assessment.packageSha256,
            submittedAt: now,
            correctCount: 0,
            itemCount: assessment.items.length,
            itemResults: assessment.items.map((item) => ({
              itemId: item.id,
              correct: false,
              type: item.type,
              targetDimensions: item.targetDimensions,
              conceptIds: item.conceptIds,
            })),
          }],
        },
      },
    };

    const recommendations = buildTodayRecommendations({
      course: listeningCourse,
      courseProgress: emptyProgress(scope),
      now,
      assessmentProgress: progress,
    });

    expect(recommendations).toEqual(expect.arrayContaining([expect.objectContaining({
      category: "listening",
      href: listeningCourse.lessons[0]!.href,
      detail: expect.stringContaining("transcript-based"),
    })]));
  });

    const recommendations = buildTodayRecommendations({ course, courseProgress: emptyProgress(scope), now });

    expect(recommendations.some((item) => item.category === "pronunciation")).toBe(false);
    expect(JSON.stringify(recommendations)).not.toMatch(/weak|mastery|proficien/i);
  });

  it("suggests an unfinished supplied pronunciation prompt only after course activity", () => {
    const progress = { ...emptyProgress(scope), lastLessonId: course.lessons[0]!.lessonId };
    const recommendations = buildTodayRecommendations({ course, courseProgress: progress, now });

    expect(recommendations).toEqual(expect.arrayContaining([expect.objectContaining({
      category: "pronunciation",
      href: course.lessons[0]!.href,
    })]));
  });

  it("omits pronunciation when the last accessed lesson is no longer supplied", () => {
    const progress = { ...emptyProgress(scope), lastLessonId: "removed-lesson" };

    const recommendations = buildTodayRecommendations({ course, courseProgress: progress, now });

    expect(recommendations.some((item) => item.category === "pronunciation")).toBe(false);
  });

    expect(buildTodayRecommendations({
      course,
      courseProgress: { ...emptyProgress(scope), course: "A2" },
      now,
    })).toEqual([]);
    expect(buildTodayRecommendations({ course, courseProgress: emptyProgress(scope), now: "not-a-time" })).toEqual([]);
  });

  it("does not mix local review activity from another learner", () => {
    const sense = getVocabularySenses("en").find((candidate) => candidate.band === "A1")!;
    const otherLearnerProgress = recordWordSenseResult(
      emptyVocabularyProgress({ learnerId: "another-learner-001", language: "en" }, vocabularySnapshot.inventoryVersion),
      sense.id,
      false,
      "2026-10-08T12:00:00.000Z",
    );

    const recommendations = buildTodayRecommendations({
      course,
      courseProgress: emptyProgress(scope),
      now,
      vocabularyProgress: otherLearnerProgress,
    });

    expect(recommendations.map((item) => item.category)).toEqual(["new_lesson"]);
  });
});
