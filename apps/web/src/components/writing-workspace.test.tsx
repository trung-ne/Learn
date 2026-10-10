import { fireEvent, render, screen } from "@testing-library/react";
import { beforeEach, describe, expect, it } from "vitest";
import { learnerProfileKey } from "@/lib/progress";
import { writingProgressKey } from "@/lib/writing-progress";
import { WritingWorkspace } from "@/components/writing-workspace";

const learnerId = "local-learner-001";

beforeEach(() => {
  localStorage.clear();
  localStorage.setItem(learnerProfileKey(), JSON.stringify({ version: 2, learnerId, activeLanguage: "en" }));
});

describe("WritingWorkspace", () => {
  it("renders supplied tasks and an explicit unavailable evaluator boundary", async () => {
    render(<WritingWorkspace />);
    expect(await screen.findByText("Writing")).toBeInTheDocument();
    expect(screen.getByText(/No provider, AI correction, score/i)).toBeInTheDocument();
    expect(screen.getAllByText("Feedback unavailable").length).toBeGreaterThan(1);
    expect(screen.getByText("Correction workspace")).toBeInTheDocument();
    expect(screen.getByText(/No evaluator is connected, so no feedback exists/i)).toBeInTheDocument();
    expect(screen.queryByText(/Grammar weakness/i)).not.toBeInTheDocument();
  });

  it("stores learner-authored drafts and forks a revision without writing review data", async () => {
    render(<WritingWorkspace />);
    const revision = await screen.findByLabelText("Your revision");
    fireEvent.change(revision, { target: { value: "My original learner draft." } });
    expect(localStorage.getItem(writingProgressKey({ learnerId, language: "en" }))).toContain("My original learner draft.");
    fireEvent.click(screen.getAllByRole("button", { name: "Try again with a linked revision" })[0]!);
    expect(localStorage.getItem(writingProgressKey({ learnerId, language: "en" }))).toContain("REVISED");
    expect(localStorage.getItem("english-master.review.v1.local-learner-001.en.A1")).toBeNull();
  });
});
