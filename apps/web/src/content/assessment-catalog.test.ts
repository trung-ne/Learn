import { describe, expect, it } from "vitest";
import {
  assessmentSnapshot,
  getAssessmentPackage,
  getAssessmentPackages,
  getLessonQuiz,
  getLevelTest,
  getPlacementPackage,
  getUnitTest,
  validateAssessmentSnapshot,
} from "@/content/assessment-catalog";

describe("assessment catalog", () => {
  it("exposes the exact verified English package inventory", () => {
    const packages = getAssessmentPackages();
    const counts = packages.reduce<Record<string, number>>((result, assessment) => ({
      ...result,
      [assessment.type]: (result[assessment.type] ?? 0) + 1,
    }), {});

    expect(packages).toHaveLength(367);
    expect(counts).toEqual({ LESSON_QUIZ: 300, UNIT_TEST: 60, LEVEL_TEST: 6, PLACEMENT: 1 });
    expect(new Set(packages.map((assessment) => assessment.id)).size).toBe(packages.length);
    expect(getPlacementPackage().contentStatus).toBe("UNREVIEWED");
  });

  it("finds lesson, unit, and level packages only through their bound scope", () => {
    const lesson = getAssessmentPackages().find((assessment) => assessment.type === "LESSON_QUIZ")!;
    const unit = getAssessmentPackages().find((assessment) => assessment.type === "UNIT_TEST")!;

    expect(getAssessmentPackage(lesson.id)).toBe(lesson);
    expect(getLessonQuiz(lesson.scope.lessonIds[0]!)).toBe(lesson);
    expect(getUnitTest(unit.scope.unitIds[0]!)).toBe(unit);
    expect(getLevelTest("A1")?.type).toBe("LEVEL_TEST");
    expect(getAssessmentPackage("unknown-package")).toBeUndefined();
  });

  it("fails closed for altered status, inventory, and answer contracts", () => {
    expect(() => validateAssessmentSnapshot({ ...assessmentSnapshot, contentStatus: "APPROVED" })).toThrow(/Unsupported assessment snapshot metadata/u);
    expect(() => validateAssessmentSnapshot({ ...assessmentSnapshot, packages: assessmentSnapshot.packages.slice(1) })).toThrow(/Unsupported assessment snapshot metadata/u);
    const invalid = structuredClone(assessmentSnapshot) as unknown as { packages: Array<{ items: Array<{ answerContract: unknown }> }> };
    invalid.packages[0]!.items[0]!.answerContract = { answer: "bad" };
    expect(() => validateAssessmentSnapshot(invalid)).toThrow(/answer contract/u);
  });
});
