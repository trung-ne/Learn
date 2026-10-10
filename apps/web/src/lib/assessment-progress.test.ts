import { describe, expect, it } from "vitest";
import { getAssessmentPackages, getPlacementPackage } from "@/content/assessment-catalog";
import type { AssessmentItem, AssessmentPackage } from "@/content/assessment-types";
import {
  aggregateAssessmentEvidence,
  assessmentDraft,
  assessmentProgressKey,
  emptyAssessmentProgress,
  latestAssessmentAttempt,
  loadAssessmentProgress,
  parseAssessmentProgress,
  resetAssessmentProgress,
  saveAssessmentDraft,
  saveAssessmentProgress,
  submitAssessment,
  type AssessmentProgressScope,
  type AssessmentResponse,
} from "@/lib/assessment-progress";
import type { StorageLike } from "@/lib/progress";

function memoryStorage(): StorageLike & { readonly values: Map<string, string> } {
  const values = new Map<string, string>();
  return {
    values,
    getItem: (key) => values.get(key) ?? null,
    setItem: (key, value) => { values.set(key, value); },
    removeItem: (key) => { values.delete(key); },
  };
}

const scope: AssessmentProgressScope = { learnerId: "local-learner-001", language: "en" };
const otherScope: AssessmentProgressScope = { learnerId: "local-learner-002", language: "en" };

function correctResponse(item: AssessmentItem): AssessmentResponse {
  if ("correctAnswer" in item.answerContract) return item.answerContract.correctAnswer;
  if ("acceptableAnswers" in item.answerContract) return item.answerContract.acceptableAnswers[0]!;
  if ("correctOrder" in item.answerContract) return item.answerContract.correctOrder;
  return Object.fromEntries(item.answerContract.pairs.map((pair) => [pair.left, pair.right]));
}

function answersFor(assessment: AssessmentPackage): Readonly<Record<string, AssessmentResponse>> {
  return Object.fromEntries(assessment.items.map((item) => [item.id, correctResponse(item)]));
}

describe("browser-local assessment progress", () => {
  it("isolates assessment records by learner and pinned assessment run", () => {
    const storage = memoryStorage();
    const assessment = getAssessmentPackages().find((item) => item.type === "LESSON_QUIZ")!;
    const submitted = submitAssessment(emptyAssessmentProgress(scope), assessment, answersFor(assessment), "2026-10-08T12:00:00.000Z");

    expect(saveAssessmentProgress(submitted, storage)).toBe(true);
    expect(loadAssessmentProgress(scope, storage)).toEqual(submitted);
    expect(loadAssessmentProgress(otherScope, storage)).toEqual(emptyAssessmentProgress(otherScope));
    expect(assessmentProgressKey(scope)).not.toBe(assessmentProgressKey(otherScope));
  });

  it("persists a partial matching draft but rejects an incomplete submission", () => {
    const assessment = getAssessmentPackages().find((item) => item.items.some((candidate) => candidate.type === "matching"))!;
    const item = assessment.items.find((candidate) => candidate.type === "matching")!;
    if (!("pairs" in item.answerContract)) throw new Error("Expected matching contract.");
    const draft = { [item.id]: { [item.answerContract.pairs[0]!.left]: item.answerContract.pairs[0]!.right } };
    const progress = saveAssessmentDraft(emptyAssessmentProgress(scope), assessment, draft);

    expect(assessmentDraft(progress, assessment)).toEqual(draft);
    expect(submitAssessment(progress, assessment, draft, "2026-10-08T12:00:00.000Z")).toEqual(progress);
  });

  it("scores all supplied contract types and retains no raw submitted answers", () => {
    const packages = getAssessmentPackages();
    let progress = emptyAssessmentProgress(scope);
    for (const type of ["multiple_choice", "fill_blank", "matching", "ordering", "reading", "listening"] as const) {
      const assessment = packages.find((item) => item.items.some((candidate) => candidate.type === type))!;
      progress = submitAssessment(progress, assessment, answersFor(assessment), "2026-10-08T12:00:00.000Z");
      const attempt = latestAssessmentAttempt(progress, assessment)!;
      expect(attempt.correctCount).toBe(assessment.items.length);
      expect(attempt).not.toHaveProperty("responses");
      expect(attempt).not.toHaveProperty("draftResponses");
    }
  });

  it("keeps previous attempts and calculates the fixed local placement suggestion", () => {
    const placement = getPlacementPackage();
    const answers = answersFor(placement);
    const first = submitAssessment(emptyAssessmentProgress(scope), placement, answers, "2026-10-08T12:00:00.000Z");
    const second = submitAssessment(first, placement, answers, "2026-10-08T12:01:00.000Z");

    expect(latestAssessmentAttempt(second, placement)?.suggestedStartTier).toBe("C2.2");
    expect(second.packages[placement.id]?.attempts).toHaveLength(2);
  });

  it("rejects malformed or scope-mismatched saved state and resets only assessment state", () => {
    const storage = memoryStorage();
    expect(parseAssessmentProgress("not json", scope)).toEqual(emptyAssessmentProgress(scope));
    expect(parseAssessmentProgress(JSON.stringify(emptyAssessmentProgress(otherScope)), scope)).toEqual(emptyAssessmentProgress(scope));
    expect(saveAssessmentProgress(emptyAssessmentProgress(scope), storage)).toBe(true);
    expect(resetAssessmentProgress(scope, storage)).toBe(true);
    expect(loadAssessmentProgress(scope, storage)).toEqual(emptyAssessmentProgress(scope));
  });

  it("counts each submitted package once per evidence label", () => {
    const assessment = getAssessmentPackages().find((item) => item.type === "LESSON_QUIZ")!;
    const progress = submitAssessment(emptyAssessmentProgress(scope), assessment, answersFor(assessment), "2026-10-08T12:00:00.000Z");
    const evidence = aggregateAssessmentEvidence(progress);
    const itemType = assessment.items[0]!.type;

    expect(evidence[`item:${itemType}`]?.completedPackages).toBe(1);
  });
});
