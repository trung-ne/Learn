import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { PracticePanels } from "@/components/practice-panels";

const practice = {
  listening: { instruction: "Answer first.", question: "Who?", transcript: "A transcript", answer: "Lan" },
  speaking: { instruction: "Speak briefly." },
  pronunciation: { instruction: "Read aloud.", without_audio: "NOT_ASSESSED" },
  writing: { instruction: "Write a draft.", feedback_boundary: "FEEDBACK_ONLY_NO_REPLACEMENT" },
};

describe("practice protocol boundaries", () => {
  it("keeps transcript private until an attempt and does not expose audio or AI controls", () => {
    const { container } = render(<PracticePanels practice={practice} completed={{}} writingDraft="" onProtocolComplete={() => {}} onDraftChange={() => {}} />);
    expect(screen.queryByText("A transcript")).not.toBeInTheDocument();
    expect(screen.getByText("NOT_ASSESSED")).toBeInTheDocument();
    expect(container.querySelector("audio")).toBeNull();
    expect(screen.queryByText(/AI feedback/i)).not.toBeInTheDocument();

    fireEvent.change(screen.getByLabelText("Who?"), { target: { value: "Lan" } });
    fireEvent.click(screen.getByRole("button", { name: /reveal transcript/i }));
    expect(screen.getByText("A transcript")).toBeInTheDocument();
  });
});
