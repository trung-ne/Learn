import { render, screen } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { CatalogProgress } from "@/components/catalog-progress";
import { loadLearner, loadProgress, summarizeCourseProgress } from "@/lib/progress";

vi.mock("@/lib/progress", () => ({
  emptyProgress: vi.fn(() => ({ version: 2, learnerId: "local-unavailable", language: "en", course: "A1", lessons: {}, concepts: {} })),
  loadLearner: vi.fn(),
  loadProgress: vi.fn(),
  resetProgress: vi.fn(),
  summarizeCourseProgress: vi.fn(),
}));

describe("catalog progress", () => {
  beforeEach(() => {
    vi.mocked(loadLearner).mockReturnValue({ version: 2, learnerId: "local-learner-001", activeLanguage: "en" });
    vi.mocked(loadProgress).mockReturnValue({ version: 2, learnerId: "local-learner-001", language: "en", course: "A1", lessons: {}, concepts: {} });
    vi.mocked(summarizeCourseProgress).mockReturnValue({
      completedLessons: 1,
      totalLessons: 3,
      units: [
        { unitId: "course-u01", completedLessons: 1, totalLessons: 2 },
        { unitId: "course-u02", completedLessons: 0, totalLessons: 1 },
      ],
    });
  });

  it("renders inventory-bounded course and unit counts", async () => {
    render(
      <CatalogProgress
        language="en"
        course="A1"
        languageName="English"
        lessons={[
          { lessonId: "lesson-1", unitId: "course-u01" },
          { lessonId: "lesson-2", unitId: "course-u01" },
          { lessonId: "lesson-3", unitId: "course-u02" },
        ]}
      />,
    );

    expect(await screen.findByText("1 / 3")).toBeInTheDocument();
    expect(screen.getByText("Unit 1: 1 / 2")).toBeInTheDocument();
    expect(screen.getByText("Unit 2: 0 / 1")).toBeInTheDocument();
  });
});
