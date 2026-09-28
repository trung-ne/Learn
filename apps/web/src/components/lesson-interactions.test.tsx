import { fireEvent, render, screen } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { LessonInteractions } from "@/components/lesson-interactions";
import type { DisplayLesson } from "@/content/types";
import { loadProgress, saveProgress } from "@/lib/progress";

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

  it("exposes locally completed state as a pressed toggle", async () => {
    render(<LessonInteractions lesson={englishLesson} />);
    const completion = await screen.findByRole("button", { name: "Mark lesson complete" });
    expect(completion).toHaveAttribute("aria-pressed", "false");
    fireEvent.click(completion);
    expect(await screen.findByRole("button", { name: "Mark as not complete" })).toHaveAttribute("aria-pressed", "true");
  });
});
