import { fireEvent, render, screen } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { LessonInteractions } from "@/components/lesson-interactions";
import type { DisplayLesson } from "@/content/types";
import { loadProgress, saveProgress } from "@/lib/progress";
import { recordGrammarTargetResult, saveGrammarProgress } from "@/lib/grammar-progress";
import { recordObjectiveReviewOutcome, saveReviewProgress } from "@/lib/review-progress";

vi.mock("@/lib/progress", () => ({
  emptyProgress: vi.fn((scope) => ({ version: 2, ...scope, lessons: {}, concepts: {} })),
  loadLearner: vi.fn(() => ({ version: 2, learnerId: "local-learner-001", activeLanguage: "en" })),
  loadProgress: vi.fn((scope) => ({ version: 2, ...scope, lessons: {}, concepts: {} })),
  resetExerciseRunner: vi.fn((progress) => progress),
  saveProgress: vi.fn(),
  setActiveLanguage: vi.fn(),
  updateLessonProgress: vi.fn((progress, lessonId, patch) => ({
    ...progress,
    lessons: {
      ...progress.lessons,
      [lessonId]: { completed: false, attempts: {}, protocols: {}, drafts: {}, ...progress.lessons[lessonId], ...patch },
    },
  })),
}));

vi.mock("@/lib/review-progress", () => ({
  emptyReviewProgress: vi.fn((scope) => ({ version: 1, ...scope, items: {} })),
  isObjectiveExerciseType: vi.fn((type) => type === "multiple_choice"),
  loadReviewProgress: vi.fn((scope) => ({ version: 1, ...scope, items: {} })),
  recordObjectiveReviewOutcome: vi.fn((progress) => progress),
  saveReviewProgress: vi.fn(),
}));

vi.mock("@/content/grammar-catalog", () => ({
  grammarSnapshot: { inventoryVersion: "grammar-test" },
  getGrammarTargetIdsForExercise: vi.fn((language, _lessonId, exerciseId) =>
    language === "en" && exerciseId === "exercise-one" ? ["grammar-en-test"] : [],
  ),
}));

vi.mock("@/lib/grammar-progress", () => ({
  emptyGrammarProgress: vi.fn((scope, inventoryVersion) => ({ version: 1, ...scope, inventoryVersion, targets: {} })),
  loadGrammarProgress: vi.fn((scope, inventoryVersion) => ({ version: 1, ...scope, inventoryVersion, targets: {} })),
  recordGrammarTargetResult: vi.fn((progress) => progress),
  saveGrammarProgress: vi.fn(),
}));

const englishLesson: DisplayLesson = {
  language: "en",
  band: "A1",
  courseAvailability: "AVAILABLE",
  tier: "A1.1",
  unitId: "unit-1",
  lessonId: "lesson-en",
  sequence: 1,
  title: "English lesson",
  topic: "Greetings",
  durationMinutes: 20,
};
const germanLesson: DisplayLesson = { ...englishLesson, language: "de", courseAvailability: "PILOT", lessonId: "lesson-de", title: "Deutschlektion" };

describe("lesson interaction scope", () => {
  beforeEach(() => vi.clearAllMocks());

  it("loads and saves each lesson in its target-language course scope", async () => {
    const { rerender } = render(<LessonInteractions lesson={englishLesson} />);
    await screen.findByRole("button", { name: "Mark lesson complete" });
    expect(loadProgress).toHaveBeenLastCalledWith({ learnerId: "local-learner-001", language: "en", course: "A1" });

    rerender(<LessonInteractions lesson={germanLesson} />);
    await screen.findByText("Saved only in this browser for German.");
    expect(loadProgress).toHaveBeenLastCalledWith({ learnerId: "local-learner-001", language: "de", course: "A1" });
    expect(saveProgress).toHaveBeenCalled();
  });

  it("records only objectively checked exercise outcomes for the shared review store", async () => {
    const lesson: DisplayLesson = {
      ...englishLesson,
      exercises: [{ id: "exercise-one", type: "multiple_choice", prompt: "Choose A", options: ["A", "B"], correct_answer: "A" }],
    };
    render(<LessonInteractions lesson={lesson} />);
    fireEvent.click(await screen.findByRole("radio", { name: "A" }));
    fireEvent.click(screen.getByRole("button", { name: "Check answer" }));
    expect(recordObjectiveReviewOutcome).toHaveBeenCalledWith(expect.anything(), expect.objectContaining({
      lessonId: "lesson-en", exerciseId: "exercise-one", result: "correct",
    }));
    expect(saveReviewProgress).toHaveBeenCalled();
    expect(recordGrammarTargetResult).toHaveBeenCalledWith(expect.anything(), "grammar-en-test", true, expect.any(String));
    expect(saveGrammarProgress).toHaveBeenCalled();

    vi.clearAllMocks();
    render(<LessonInteractions lesson={{ ...englishLesson, exercises: [{ id: "self-practice", type: "writing", prompt: "Write", rubric: "Use clear sentences." }] }} />);
    fireEvent.click(await screen.findByRole("button", { name: "Finish practice" }));
    expect(recordObjectiveReviewOutcome).not.toHaveBeenCalled();
    expect(recordGrammarTargetResult).not.toHaveBeenCalled();
  });

  it("exposes locally completed state as a pressed toggle", async () => {
    render(<LessonInteractions lesson={englishLesson} />);
    const completion = await screen.findByRole("button", { name: "Mark lesson complete" });
    expect(completion).toHaveAttribute("aria-pressed", "false");
    fireEvent.click(completion);
    expect(await screen.findByRole("button", { name: "Mark as not complete" })).toHaveAttribute("aria-pressed", "true");
  });
});
