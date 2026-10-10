import { render, screen } from "@testing-library/react";
import { beforeEach, describe, expect, it } from "vitest";
import { ProgressDashboard } from "@/components/progress-dashboard";
import { learnerProfileKey } from "@/lib/progress";

const learner = { version: 2 as const, learnerId: "local-learner-001", activeLanguage: "en" as const };
const englishCourses = [
  { language: "en" as const, level: "A1" as const, lessons: [{ lessonId: "a1-lesson", unitId: "a1-unit" }] },
  { language: "en" as const, level: "A2" as const, lessons: [{ lessonId: "a2-lesson", unitId: "a2-unit" }] },
];

beforeEach(() => {
  window.localStorage.clear();
  window.localStorage.setItem(learnerProfileKey(), JSON.stringify(learner));
});

describe("progress dashboard", () => {
  it("renders local boundaries, course activity, and unavailable measures after hydration", async () => {
    render(<ProgressDashboard language="en" courses={englishCourses} />);

    expect(await screen.findByRole("heading", { name: "Progress dashboard" })).toBeInTheDocument();
    expect(screen.getByText(/not a proficiency record, CEFR result, diagnosis, certification, or course unlock/i)).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Open A1" })).toHaveAttribute("href", "/learn/en/A1");
    expect(screen.getByText("NOT_MEASURED")).toBeInTheDocument();
    expect(screen.getByText("NOT_RECORDED")).toBeInTheDocument();
    expect(screen.getByText("NOT_TRACKED")).toBeInTheDocument();
    expect(screen.getAllByText("NOT_ASSESSED").length).toBeGreaterThanOrEqual(2);
  });

  it("keeps German separate from English-only grammar and assessment evidence", async () => {
    render(<ProgressDashboard language="de" courses={[{ language: "de", level: "A1", lessons: [{ lessonId: "de-lesson", unitId: "de-unit" }] }]} />);

    expect(await screen.findByRole("heading", { name: "Progress dashboard" })).toBeInTheDocument();
    expect(screen.getByText("No supplied browser-local grammar inventory is available for this language.")).toBeInTheDocument();
    expect(screen.queryByRole("link", { name: "Open grammar" })).not.toBeInTheDocument();
    expect(screen.queryByRole("link", { name: "Open assessment" })).not.toBeInTheDocument();
  });
});
