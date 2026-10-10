import { fireEvent, render, screen } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { TutorContextWorkspace } from "@/components/tutor-context-workspace";
import { learnerProfileKey } from "@/lib/progress";
import { tutorPreferencesKey } from "@/lib/tutor-context";

const learnerId = "local-learner-001";

beforeEach(() => {
  localStorage.clear();
  localStorage.setItem(learnerProfileKey(), JSON.stringify({ version: 2, learnerId, activeLanguage: "en" }));
  Object.assign(navigator, { clipboard: { writeText: vi.fn().mockResolvedValue(undefined) } });
});

describe("TutorContextWorkspace", () => {
  it("requires a compatible self-reported band before it allows copying", async () => {
    render(<TutorContextWorkspace language="en" course="B2" />);
    expect(await screen.findByRole("heading", { name: "Tutor Context" })).toBeInTheDocument();
    const copy = screen.getByRole("button", { name: "Copy Tutor Context" });
    expect(copy).toBeDisabled();
    expect(screen.getByText(/does not establish what you know or diagnose a weakness/i)).toBeInTheDocument();

    fireEvent.change(screen.getByLabelText("Self-reported current band"), { target: { value: "B2" } });
    expect(copy).toBeEnabled();
  });

  it("preserves the study-plan allocation when it clears Tutor preferences", async () => {
    localStorage.setItem(tutorPreferencesKey({ learnerId, language: "en" }), JSON.stringify({
      version: 1,
      learnerId,
      language: "en",
      currentBand: "A1",
      targetBand: "B1",
      dailyAllocationMinutes: 45,
      goals: ["conversation"],
    }));
    render(<TutorContextWorkspace language="en" course="A1" />);
    await screen.findByRole("heading", { name: "Tutor Context" });
    fireEvent.click(screen.getByRole("button", { name: "Clear local Tutor Context preferences" }));

    expect(JSON.parse(localStorage.getItem(tutorPreferencesKey({ learnerId, language: "en" }))!)).toMatchObject({
      dailyAllocationMinutes: 45,
      goals: [],
    });
    expect(screen.getByLabelText("Self-reported current band")).toHaveValue("");
  });

  it("copies only after explicit action and can clear Tutor preferences", async () => {
    render(<TutorContextWorkspace language="en" course="A1" />);
    await screen.findByRole("heading", { name: "Tutor Context" });
    fireEvent.change(screen.getByLabelText("Self-reported current band"), { target: { value: "A1" } });
    fireEvent.click(screen.getByRole("checkbox", { name: "conversation" }));
    fireEvent.click(screen.getByRole("button", { name: "Copy Tutor Context" }));

    expect(navigator.clipboard.writeText).toHaveBeenCalledTimes(1);
    expect(await screen.findByText(/Copied\. Paste it into your chosen external AI tool/i)).toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: "Clear local Tutor Context preferences" }));
    expect(screen.getByLabelText("Self-reported current band")).toHaveValue("");
  });
});
