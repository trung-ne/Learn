import { render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { HomeLearning, type HomeCourse } from "@/components/home-learning";
import { loadLearner, loadProgress, setActiveLanguage, summarizeCourseProgress } from "@/lib/progress";

vi.mock("@/lib/progress", () => ({
  loadLearner: vi.fn(),
  loadProgress: vi.fn(),
  setActiveLanguage: vi.fn(),
  summarizeCourseProgress: vi.fn(),
}));

const courses: readonly HomeCourse[] = [
  {
    language: "en",
    level: "A1",
    lessonCount: 50,
    availability: "AVAILABLE",
    firstLessonHref: "/learn/en/A1/unit/lesson-1",
    lessons: [{ lessonId: "lesson-1", unitId: "unit-1" }],
    lessonHrefs: { "lesson-1": "/learn/en/A1/unit/lesson-1" },
  },
  {
    language: "de",
    level: "A1",
    lessonCount: 10,
    availability: "PILOT",
    firstLessonHref: "/learn/de/A1/unit/lesson-1",
    lessons: [{ lessonId: "lesson-1", unitId: "unit-1" }],
    lessonHrefs: { "lesson-1": "/learn/de/A1/unit/lesson-1" },
  },
];

const localLearner = { version: 2 as const, learnerId: "local-learner-001", activeLanguage: "en" as const };
const emptyProgress = { version: 2 as const, learnerId: localLearner.learnerId, language: "en" as const, course: "A1" as const, lessons: {}, concepts: {} };
const emptySummary = { completedLessons: 0, totalLessons: 1, units: [] };

describe("home learner dashboard", () => {
  beforeEach(() => {
    vi.mocked(loadLearner).mockReturnValue(localLearner);
    vi.mocked(loadProgress).mockReturnValue(emptyProgress);
    vi.mocked(summarizeCourseProgress).mockReturnValue(emptySummary);
    vi.mocked(setActiveLanguage).mockImplementation((learner, activeLanguage) => ({ ...learner, activeLanguage }));
  });

  it("shows only the supplied actual courses and a clear empty resume state", async () => {
    render(<HomeLearning courses={courses} />);

    expect(await screen.findByText("Choose a course to begin.")).toBeInTheDocument();
    expect(screen.getByText("English A1")).toBeInTheDocument();
    expect(screen.getByText("German A1")).toBeInTheDocument();
    expect(screen.getAllByText("0 / 1 lessons locally complete.")).toHaveLength(2);
    expect(screen.queryByText("English A2")).not.toBeInTheDocument();
  });

  it("loads independent language scopes and continues the most recently accessed course", async () => {
    vi.mocked(loadProgress).mockImplementation(({ language, course }) => ({
      ...emptyProgress,
      language,
      course,
      lastLessonId: "lesson-1",
    }));
    vi.mocked(summarizeCourseProgress).mockImplementation((progress) => ({
      completedLessons: progress.language === "en" ? 4 : 2,
      totalLessons: progress.language === "en" ? 50 : 10,
      currentLessonId: "lesson-1",
      lastAccessedLessonId: "lesson-1",
      lastAccessedAt: progress.language === "en" ? "2026-09-26T12:00:00.000Z" : "2026-09-26T13:00:00.000Z",
      units: [],
    }));

    render(<HomeLearning courses={courses} />);

    const continueLinks = await screen.findAllByRole("link", { name: "Continue learning" });
    expect(continueLinks).toHaveLength(3);
    expect(continueLinks[0]).toHaveAttribute("href", "/learn/de/A1/unit/lesson-1");
    expect(continueLinks).toEqual(expect.arrayContaining([
      expect.objectContaining({ href: expect.stringContaining("/learn/en/A1/") }),
      expect.objectContaining({ href: expect.stringContaining("/learn/de/A1/") }),
    ]));
    await waitFor(() => {
      expect(loadProgress).toHaveBeenCalledWith({ learnerId: "local-learner-001", language: "en", course: "A1" });
      expect(loadProgress).toHaveBeenCalledWith({ learnerId: "local-learner-001", language: "de", course: "A1" });
    });
  });
});
