import { fireEvent, render, screen } from "@testing-library/react";
import { beforeEach, describe, expect, it } from "vitest";
import { PersonalStudyPlanWorkspace } from "@/components/personal-study-plan";
import { learnerProfileKey } from "@/lib/progress";

const learner = { version: 2 as const, learnerId: "local-learner-001", activeLanguage: "en" as const };
const courses = ["A2", "B1", "B2"].map((level, index) => ({
  language: "en" as const,
  level: level as "A2" | "B1" | "B2",
  lessons: [{
    lessonId: `${level.toLowerCase()}-lesson`,
    title: `${level} supplied lesson`,
    level: level as "A2" | "B1" | "B2",
    sequence: index + 1,
    durationMinutes: 20,
    href: `/learn/en/${level}/unit/${level.toLowerCase()}-lesson`,
    exerciseTypes: [],
    practiceModalities: [],
  }],
}));

beforeEach(() => {
  window.localStorage.clear();
  window.localStorage.setItem(learnerProfileKey(), JSON.stringify(learner));
});

describe("personal study plan workspace", () => {
  it("renders explicit planning boundaries and creates the requested A2 to B2 45-minute local projection", async () => {
    render(<PersonalStudyPlanWorkspace language="en" courses={courses} />);

    expect(await screen.findByRole("heading", { name: "Personal Study Plan" })).toBeInTheDocument();
    expect(screen.getByText(/not proficiency, placement, or CEFR-attainment results/i)).toBeInTheDocument();
    expect(screen.getByText("Plan unavailable")).toBeInTheDocument();

    fireEvent.change(screen.getByLabelText("Study plan current band"), { target: { value: "A2" } });
    fireEvent.change(screen.getByLabelText("Study plan target band"), { target: { value: "B2" } });
    fireEvent.change(screen.getByLabelText("Study plan daily allocation"), { target: { value: "45" } });

    expect(await screen.findByRole("heading", { name: "A2 remainder → B2" })).toBeInTheDocument();
    expect(screen.getByLabelText("Study plan daily allocation")).toHaveValue("45");
    expect(screen.getByRole("link", { name: "Open packet" })).toHaveAttribute("href", "/learn/en/A2/unit/a2-lesson");
  });

  it("does not invent an unavailable German path", async () => {
    render(<PersonalStudyPlanWorkspace language="de" courses={[{
      language: "de", level: "A1", lessons: [{ lessonId: "de-lesson", title: "German pilot", level: "A1", sequence: 1, durationMinutes: 20, href: "/learn/de/a1/unit/de-lesson", exerciseTypes: [], practiceModalities: [] }],
    }]} />);

    expect(await screen.findByRole("heading", { name: "Personal Study Plan" })).toBeInTheDocument();
    expect(screen.getByText("Plan unavailable")).toBeInTheDocument();
  });
});
