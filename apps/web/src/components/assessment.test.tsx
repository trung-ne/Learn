import { fireEvent, render, screen } from "@testing-library/react";
import { beforeEach, describe, expect, it } from "vitest";
import { AssessmentHub } from "@/components/assessment-hub";
import { AssessmentRunner } from "@/components/assessment-runner";
import type { AssessmentPackage } from "@/content/assessment-types";
import { learnerProfileKey } from "@/lib/progress";

const assessment: AssessmentPackage = {
  id: "assessment-test-001",
  type: "LESSON_QUIZ",
  packageSha256: "a".repeat(64),
  scope: { levels: ["A1"], tiers: ["A1.1"], unitIds: ["m16a1-v1-a1-u01"], lessonIds: ["m16a1-v1-a1-u01-l01"] },
  contentStatus: "UNREVIEWED",
  items: [{
    id: "assessment-item-001",
    type: "multiple_choice",
    prompt: "Choose the greeting.",
    options: ["Hello", "Goodbye"],
    source: {
      level: "A1", tier: "A1.1", unitId: "m16a1-v1-a1-u01", lessonId: "m16a1-v1-a1-u01-l01",
      packetId: "m16a1-v1-a1-u01-l01", packetSha256: "b".repeat(64), exerciseId: "exercise-001",
    },
    targetIds: ["target-001"], targetDimensions: ["vocabulary_senses"], conceptIds: ["kg-en-a1-vocabulary"],
    answerContract: { correctAnswer: "Hello" },
  }],
};

beforeEach(() => {
  localStorage.clear();
  localStorage.setItem(learnerProfileKey(), JSON.stringify({ version: 2, learnerId: "local-learner-001", activeLanguage: "en" }));
});

describe("assessment learner interfaces", () => {
  it("shows the truthful assessment hierarchy and unavailable skills", () => {
    render(<AssessmentHub />);

    expect(screen.getByRole("heading", { name: "Assessment" })).toBeInTheDocument();
    expect(screen.getByText(/Skill checkpoint/i)).toBeInTheDocument();
    expect(screen.getAllByText(/Unavailable: no immutable package/i)).toHaveLength(1);
    expect(screen.getAllByText(/German has no language-scoped assessment package/i)).toHaveLength(1);
    expect(screen.getAllByText(/not CEFR certification/i).length).toBeGreaterThan(0);
  });

  it("scores a supplied objective item locally and preserves result-only display before a retake", async () => {
    render(<AssessmentRunner assessment={assessment} />);
    const submit = await screen.findByRole("button", { name: "Submit local assessment" });
    expect(submit).toBeDisabled();

    fireEvent.click(screen.getByRole("radio", { name: "Hello" }));
    expect(submit).toBeEnabled();
    fireEvent.click(submit);

    expect(await screen.findByText("1 / 1")).toBeInTheDocument();
    expect(screen.getByText(/does not certify proficiency or CEFR attainment/i)).toBeInTheDocument();
    expect(screen.queryByDisplayValue("Hello")).not.toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: "Start a new local attempt" }));
    expect(screen.getByRole("button", { name: "Submit local assessment" })).toBeDisabled();
  });
});
