import { render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import type { HomeCourse } from "@/components/home-learning";
import { TodayRecommendations } from "@/components/today-recommendations";
import { emptyProgress } from "@/lib/progress";

vi.mock("@/lib/assessment-progress", async (importOriginal) => {
  const actual = await importOriginal<typeof import("@/lib/assessment-progress")>();
  return { ...actual, loadAssessmentProgress: vi.fn(actual.emptyAssessmentProgress) };
});
vi.mock("@/lib/grammar-progress", async (importOriginal) => {
  const actual = await importOriginal<typeof import("@/lib/grammar-progress")>();
  return { ...actual, loadGrammarProgress: vi.fn(actual.emptyGrammarProgress) };
});
vi.mock("@/lib/vocabulary-progress", async (importOriginal) => {
  const actual = await importOriginal<typeof import("@/lib/vocabulary-progress")>();
  return { ...actual, loadVocabularyProgress: vi.fn(actual.emptyVocabularyProgress) };
});

const learner = { version: 2 as const, learnerId: "local-learner-001", activeLanguage: "en" as const };
const course: HomeCourse = {
  language: "en",
  level: "A1",
  lessonCount: 2,
  availability: "AVAILABLE",
  firstLessonHref: "/learn/en/A1/unit/lesson-1",
  lessons: [
    { lessonId: "lesson-1", unitId: "unit-1", title: "First lesson", sequence: 1, href: "/learn/en/A1/unit/lesson-1", hasListeningPractice: true, hasPronunciationPractice: true, durationMinutes: 15 },
    { lessonId: "lesson-2", unitId: "unit-1", title: "Second lesson", sequence: 2, href: "/learn/en/A1/unit/lesson-2", hasListeningPractice: true, hasPronunciationPractice: true, durationMinutes: 15 },
  ],
  lessonHrefs: { "lesson-1": "/learn/en/A1/unit/lesson-1", "lesson-2": "/learn/en/A1/unit/lesson-2" },
};
const progress = emptyProgress({ learnerId: learner.learnerId, language: "en", course: "A1" });

describe("TODAY recommendations", () => {
  it("hydrates a local-only boundary and a safe next-lesson action", async () => {
    render(<TodayRecommendations learner={learner} course={course} courseProgress={progress} />);

    expect(await screen.findByRole("heading", { name: "TODAY" })).toBeInTheDocument();
    expect(screen.getByText("Suggestions use activity saved in this browser. They are not proficiency or mastery ratings.")).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Start lesson" })).toHaveAttribute("href", "/learn/en/A1/unit/lesson-1");
    expect(screen.queryByText(/speaking score|writing score|audio-listening score/i)).not.toBeInTheDocument();
  });

  it("does not display categories without supplied local evidence", async () => {
    render(<TodayRecommendations learner={learner} course={course} courseProgress={progress} />);

    await screen.findByRole("heading", { name: "TODAY" });
    expect(screen.queryByText("Vocabulary review")).not.toBeInTheDocument();
    expect(screen.queryByText("Grammar review")).not.toBeInTheDocument();
    expect(screen.queryByText("Listening practice")).not.toBeInTheDocument();
    expect(screen.queryByText("Pronunciation practice")).not.toBeInTheDocument();
  });

  it("does not use English review stores for German courses", async () => {
    const germanCourse: HomeCourse = { ...course, language: "de", firstLessonHref: "/learn/de/A1/unit/lesson-1", lessons: course.lessons.map((lesson) => ({ ...lesson, href: lesson.href.replace("/en/", "/de/") })) };
    const germanProgress = emptyProgress({ learnerId: learner.learnerId, language: "de", course: "A1" });

    render(<TodayRecommendations learner={{ ...learner, activeLanguage: "de" }} course={germanCourse} courseProgress={germanProgress} />);

    expect(await screen.findByRole("heading", { name: "TODAY" })).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Start lesson" })).toHaveAttribute("href", "/learn/de/A1/unit/lesson-1");
    expect(screen.queryByText("Vocabulary review")).not.toBeInTheDocument();
    expect(screen.queryByText("Grammar review")).not.toBeInTheDocument();
  });
});
