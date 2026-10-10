import { describe, expect, it } from "vitest";
import { getAssessmentPackages } from "@/content/assessment-catalog";
import { grammarSnapshot, getGrammarTargets } from "@/content/grammar-catalog";
import { vocabularySnapshot, getVocabularySenses } from "@/content/vocabulary-catalog";
import { buildProgressDashboard, type ProgressDashboardCourse } from "@/lib/progress-dashboard";
import { emptyGrammarProgress, recordGrammarTargetResult } from "@/lib/grammar-progress";
import { emptyProgress } from "@/lib/progress";
import { emptyAssessmentProgress } from "@/lib/assessment-progress";
import { emptyReviewProgress, recordObjectiveReviewOutcome } from "@/lib/review-progress";
import { emptyVocabularyProgress, recordWordSenseResult } from "@/lib/vocabulary-progress";

const learnerId = "local-learner-001";
const now = "2026-10-09T12:00:00.000Z";
const courses: readonly ProgressDashboardCourse[] = [
  { language: "en", level: "A2", lessons: [{ lessonId: "a2-lesson", unitId: "a2-unit" }] },
  { language: "en", level: "A1", lessons: [{ lessonId: "a1-lesson", unitId: "a1-unit" }, { lessonId: "a1-second", unitId: "a1-unit" }] },
];

function input() {
  return {
    learnerId,
    language: "en" as const,
    courses,
    courseProgress: {
      A1: emptyProgress({ learnerId, language: "en", course: "A1" }),
      A2: emptyProgress({ learnerId, language: "en", course: "A2" }),
    },
    reviewProgress: {
      A1: emptyReviewProgress({ learnerId, language: "en", course: "A1" }),
      A2: emptyReviewProgress({ learnerId, language: "en", course: "A2" }),
    },
    vocabularyProgress: emptyVocabularyProgress({ learnerId, language: "en" }, vocabularySnapshot.inventoryVersion),
    grammarProgress: emptyGrammarProgress({ learnerId, language: "en" }, grammarSnapshot.inventoryVersion),
    now,
  };
}

describe("progress dashboard summary", () => {
  it("orders supplied course rows and ignores stale locally completed lessons", () => {
    const base = input();
    const a1 = {
      ...base.courseProgress.A1!,
      lessons: {
        "a1-lesson": { completed: true, attempts: {}, protocols: {}, drafts: {} },
        "removed-lesson": { completed: true, attempts: {}, protocols: {}, drafts: {} },
      },
    };
    const summary = buildProgressDashboard({ ...base, courseProgress: { ...base.courseProgress, A1: a1 } });

    expect(summary.courses).toEqual([
      { level: "A1", completedLessons: 1, suppliedLessons: 2, completionPercent: 50 },
      { level: "A2", completedLessons: 0, suppliedLessons: 1, completionPercent: 0 },
    ]);
  });

  it("reports locally tracked vocabulary and grammar states without proficiency labels", () => {
    const base = input();
    const sense = getVocabularySenses("en")[0]!;
    const target = getGrammarTargets("en")[0]!;
    const vocabularyProgress = recordWordSenseResult(base.vocabularyProgress, sense.id, false, "2026-10-08T12:00:00.000Z");
    const grammarProgress = recordGrammarTargetResult(base.grammarProgress, target.id, false, "2026-10-08T12:00:00.000Z");
    const summary = buildProgressDashboard({ ...base, vocabularyProgress, grammarProgress });

    expect(summary.vocabulary).toEqual(expect.objectContaining({ availability: "AVAILABLE", activeSenses: 1, sensesWithRecordedMistakes: 1, dueSenses: 1 }));
    expect(summary.grammar).toEqual(expect.objectContaining({ availability: "AVAILABLE", activeTargets: 1, targetsWithRecordedIncorrectOutcomes: 1, dueTargets: 1 }));
    expect(JSON.stringify(summary)).not.toMatch(/proficien|CEFR/i);
  });

  it("omits foreign vocabulary state and reports unavailable measures explicitly", () => {
    const base = input();
    const foreignVocabulary = emptyVocabularyProgress({ learnerId: "another-learner-001", language: "en" }, vocabularySnapshot.inventoryVersion);
    const summary = buildProgressDashboard({ ...base, vocabularyProgress: foreignVocabulary });

    expect(summary.vocabulary.availability).toBe("NOT_AVAILABLE");
    expect(summary.retentionStatus).toBe("NOT_MEASURED");
    expect(summary.studyTimeStatus).toBe("NOT_RECORDED");
    expect(summary.mistakeTrendStatus).toBe("NOT_TRACKED");
  });

  it("aggregates local review outcomes only for current supplied lessons", () => {
    const base = input();
    const reviewProgress = recordObjectiveReviewOutcome(
      base.reviewProgress.A1!,
      { lessonId: "a1-lesson", exerciseId: "objective-one", result: "incorrect", reviewedAt: "2026-10-08T12:00:00.000Z" },
    );
    const staleProgress = recordObjectiveReviewOutcome(
      reviewProgress,
      { lessonId: "removed-lesson", exerciseId: "objective-two", result: "incorrect", reviewedAt: "2026-10-08T12:00:00.000Z" },
    );
    const summary = buildProgressDashboard({ ...base, reviewProgress: { ...base.reviewProgress, A1: staleProgress } });

    expect(summary.review).toEqual({ reviewedActivities: 1, reviewOutcomes: 1, correctOutcomes: 0, incorrectOutcomes: 1, dueActivities: 1, recentIncorrectActivities: 1 });
  });

  it("excludes assessment state that is not bound to the current supplied package", () => {
    const base = input();
    const assessment = getAssessmentPackages()[0]!;
    const assessmentProgress = {
      ...emptyAssessmentProgress({ learnerId, language: "en" }),
      packages: {
        [assessment.id]: {
          packageSha256: "0".repeat(64),
          attempts: [],
        },
      },
    };
    const summary = buildProgressDashboard({ ...base, assessmentProgress });

    expect(summary.directSkillEvidence.map((row) => row.status))
      .toEqual(["NOT_ASSESSED", "NOT_ASSESSED", "NOT_ASSESSED", "NOT_ASSESSED", "NOT_ASSESSED", "NOT_ASSESSED"]);
  });

  it("does not expose English direct assessment evidence for German", () => {
    const summary = buildProgressDashboard({
      learnerId,
      language: "de",
      courses: [{ language: "de", level: "A1", lessons: [{ lessonId: "de-lesson", unitId: "de-unit" }] }],
      courseProgress: { A1: emptyProgress({ learnerId, language: "de", course: "A1" }) },
      reviewProgress: { A1: emptyReviewProgress({ learnerId, language: "de", course: "A1" }) },
      vocabularyProgress: emptyVocabularyProgress({ learnerId, language: "de" }, vocabularySnapshot.inventoryVersion),
      now,
    });

    expect(summary.directSkillEvidence.map((row) => row.status)).toEqual(["NOT_AVAILABLE", "NOT_AVAILABLE", "NOT_AVAILABLE", "NOT_AVAILABLE", "NOT_ASSESSED", "NOT_ASSESSED"]);
    expect(summary.grammar.availability).toBe("NOT_AVAILABLE");
  });
});
