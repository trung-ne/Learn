import { render, screen } from "@testing-library/react";
import { beforeEach, describe, expect, it } from "vitest";
import { MistakeWeaknessWorkspace } from "@/components/mistake-weakness-workspace";
import { learnerProfileKey } from "@/lib/progress";
import { emptyReviewProgress, recordObjectiveReviewOutcome, reviewProgressKey } from "@/lib/review-progress";

const scope = { learnerId: "local-learner-001", language: "en" as const, course: "A1" as const };

beforeEach(() => {
  localStorage.clear();
  localStorage.setItem(learnerProfileKey(), JSON.stringify({ version: 2, learnerId: scope.learnerId, activeLanguage: "en" }));
});

describe("MistakeWeaknessWorkspace", () => {
  it("renders aggregate repeated outcomes with supplied lesson links", async () => {
    const first = recordObjectiveReviewOutcome(emptyReviewProgress(scope), {
      lessonId: "m16a1-v1-a1-u01-l01", exerciseId: "meaning-check", result: "incorrect", reviewedAt: "2026-10-02T12:00:00.000Z",
    });
    const progress = recordObjectiveReviewOutcome(first, {
      lessonId: "m16a1-v1-a1-u01-l01", exerciseId: "meaning-check", result: "incorrect", reviewedAt: "2026-10-03T12:00:00.000Z",
    });
    localStorage.setItem(reviewProgressKey(scope), JSON.stringify(progress));

    render(<MistakeWeaknessWorkspace language="en" course="A1" />);
    expect(await screen.findByText("Repeated incorrect outcomes")).toBeInTheDocument();
    expect(screen.getByText(/2 of 2 \(100%\)/)).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Open lesson" })).toHaveAttribute("href", "/learn/en/A1/m16a1-v1-a1-u01/m16a1-v1-a1-u01-l01");
  });

  it("uses a factual, non-diagnostic empty state", async () => {
    render(<MistakeWeaknessWorkspace language="en" course="A1" />);
    expect(await screen.findByText(/No incorrect objective outcomes are recorded/i)).toBeInTheDocument();
    expect(screen.getByText(/local aggregate outcome may appear here/i)).toBeInTheDocument();
    expect(screen.queryByText(/grammar weakness/i)).not.toBeInTheDocument();
    expect(screen.queryByText(/mastery/i)).not.toBeInTheDocument();
    expect(screen.queryByText(/proficiency/i)).not.toBeInTheDocument();
  });
});
