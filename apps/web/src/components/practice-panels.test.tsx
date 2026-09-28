import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { PracticePanels } from "@/components/practice-panels";
import { getLesson } from "@/content/catalog";

const practice = {
  listening: {
    instruction: "Answer first.",
    question: "Who?",
    transcript: "A transcript",
    answer: "Lan",
  },
  speaking: {
    instruction: "Speak briefly.",
    goal: "Exchange a greeting.",
    constraints: ["Take two turns."],
  },
  pronunciation: {
    instruction: "Read aloud.",
    target: "word stress in hello",
    goal: "Use clear stress.",
    constraints: ["Say the phrase twice."],
    without_audio: "NOT_ASSESSED",
  },
  writing: { instruction: "Write a draft.", feedback_boundary: "FEEDBACK_ONLY_NO_REPLACEMENT" },
};

describe("practice protocol boundaries", () => {
  it("renders only supplied practice modalities", () => {
    render(
      <PracticePanels
        practice={{ pronunciation: practice.pronunciation }}
        completed={{}}
        writingDraft=""
        onProtocolComplete={() => {}}
        onDraftChange={() => {}}
      />,
    );

    expect(screen.getByText("Pronunciation")).toBeInTheDocument();
    expect(screen.queryByText("Listening")).not.toBeInTheDocument();
    expect(screen.queryByText("Writing")).not.toBeInTheDocument();
  });

  it("copies the exact stored instruction without copying transcript or answer data", async () => {
    const writeText = vi.fn().mockResolvedValue(undefined);
    Object.assign(navigator, { clipboard: { writeText } });
    render(
      <PracticePanels
        practice={{ listening: practice.listening }}
        completed={{}}
        writingDraft=""
        onProtocolComplete={() => {}}
        onDraftChange={() => {}}
      />,
    );

    expect(screen.getByText("Lesson-specific prompt")).toBeInTheDocument();
    expect(screen.getByText("Answer first.")).toBeInTheDocument();
    expect(screen.queryByText("A transcript")).not.toBeInTheDocument();
    expect(screen.queryByText("Lan")).not.toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Copy prompt" }));

    expect(writeText).toHaveBeenCalledWith("Answer first.");
    expect(await screen.findByText("Copied.")).toBeInTheDocument();
  });

  it("keeps listening transcript-only and concealed until an attempt", () => {
    const { container } = render(
      <PracticePanels
        practice={practice}
        completed={{}}
        writingDraft=""
        onProtocolComplete={() => {}}
        onDraftChange={() => {}}
      />,
    );
    expect(screen.getByText(/no permitted audio asset/i)).toBeInTheDocument();
    expect(screen.queryByText("A transcript")).not.toBeInTheDocument();
    expect(screen.getByText("NOT_ASSESSED")).toBeInTheDocument();
    expect(container.querySelector("audio")).toBeNull();
    expect(container.querySelector('input[type="file"]')).toBeNull();
    expect(screen.queryByText(/AI feedback/i)).not.toBeInTheDocument();

    expect(screen.getByRole("button", { name: /reveal transcript/i })).toHaveAttribute("aria-expanded", "false");
    fireEvent.change(screen.getByLabelText("Who?"), { target: { value: "Lan" } });
    fireEvent.click(screen.getByRole("button", { name: /reveal transcript/i }));
    expect(screen.getByRole("button", { name: /reveal transcript/i })).toHaveAttribute("aria-expanded", "true");
    expect(screen.getByRole("status")).toHaveAttribute("id", "listening-transcript");
    expect(screen.getByText("A transcript")).toBeInTheDocument();
  });

  it("keeps writing task requirements source-backed and drafts local", () => {
    const onDraftChange = vi.fn();
    render(
      <PracticePanels
        practice={{ writing: { instruction: "Write three sentences about your day.", goal: "Describe a routine." } }}
        targetLevel="A1"
        completed={{}}
        writingDraft="A local draft"
        onProtocolComplete={() => {}}
        onDraftChange={onDraftChange}
      />,
    );

    expect(screen.getByText("Target level:")).toBeInTheDocument();
    expect(screen.getByText("A1")).toBeInTheDocument();
    expect(screen.getByText("Task:")).toBeInTheDocument();
    expect(screen.getAllByText("Write three sentences about your day.")).toHaveLength(2);
    expect(screen.getByText("AI writing tutor prompt")).toBeInTheDocument();
    expect(screen.queryByText("Expected output", { selector: "strong" })).not.toBeInTheDocument();
    expect(screen.queryByText("Useful language", { selector: "strong" })).not.toBeInTheDocument();
    fireEvent.change(screen.getByLabelText("Your local draft"), { target: { value: "Changed local draft" } });
    expect(onDraftChange).toHaveBeenCalledWith("Changed local draft");
  });

  it("renders English speaking and pronunciation details only when explicitly supplied", () => {
    const { container } = render(
      <PracticePanels
        practice={{
          speaking: {
            ...practice.speaking,
            situation: "Meeting a classmate",
            learner_role: "New student",
            ai_role: "Classmate",
            useful_language: ["Hello", "Nice to meet you"],
          },
          pronunciation: {
            ...practice.pronunciation,
            examples: ["hello", "goodbye"],
            explanation: "Stress the first syllable.",
          },
        }}
        completed={{}}
        writingDraft=""
        onProtocolComplete={() => {}}
        onDraftChange={() => {}}
      />,
    );

    expect(screen.getByText("Meeting a classmate")).toBeInTheDocument();
    expect(screen.getByText("New student")).toBeInTheDocument();
    expect(screen.getByText("Classmate")).toBeInTheDocument();
    expect(screen.getByText("Nice to meet you")).toBeInTheDocument();
    expect(screen.getByText("word stress in hello")).toBeInTheDocument();
    expect(screen.getByText("Stress the first syllable.")).toBeInTheDocument();
    expect(screen.getByText("goodbye")).toBeInTheDocument();

    const prompt = screen.getByText("Speak briefly.");
    const goal = screen.getByText("Exchange a greeting.");
    expect(prompt.compareDocumentPosition(goal) & Node.DOCUMENT_POSITION_FOLLOWING).toBeTruthy();
    expect(container.querySelector("audio")).toBeNull();
  });

  it("preserves German source text without inventing speaking or pronunciation fields", () => {
    render(
      <PracticePanels
        practice={{
          speaking: { instruction: "Spiele Situation 1 mit wechselnden Rollen.", checklist: ["Nutze Modell 1."] },
          pronunciation: { instruction: "Sprich Guten Morgen deutlich.", checklist: ["Achte auf den Rhythmus."], assessment: "NOT_ASSESSED" },
        }}
        completed={{}}
        writingDraft=""
        onProtocolComplete={() => {}}
        onDraftChange={() => {}}
      />,
    );

    expect(screen.getByText("Spiele Situation 1 mit wechselnden Rollen.")).toBeInTheDocument();
    expect(screen.getByText("Sprich Guten Morgen deutlich.")).toBeInTheDocument();
    expect(screen.getByText("NOT_ASSESSED")).toBeInTheDocument();
    expect(screen.queryByText("Situation", { selector: "strong" })).not.toBeInTheDocument();
    expect(screen.queryByText("Target sound or feature", { selector: "strong" })).not.toBeInTheDocument();
    expect(screen.queryByText("Examples", { selector: "strong" })).not.toBeInTheDocument();
  });

  it("copies exact stored English and German prompt instructions from the snapshot", async () => {
    const english = getLesson("en", "A1", "m16a1-v1-a1-u01", "m16a1-v1-a1-u01-l01")!;
    const german = getLesson("de", "A1", "de-a1-v1-u01", "de-a1-v1-u01-l01")!;
    const writeText = vi.fn().mockResolvedValue(undefined);
    Object.assign(navigator, { clipboard: { writeText } });
    const { rerender } = render(
      <PracticePanels
        practice={{ speaking: english.practice!.speaking! }}
        completed={{}}
        writingDraft=""
        onProtocolComplete={() => {}}
        onDraftChange={() => {}}
      />,
    );
    fireEvent.click(screen.getByRole("button", { name: "Copy prompt" }));
    expect(writeText).toHaveBeenLastCalledWith(english.practice!.speaking!.instruction);

    rerender(
      <PracticePanels
        practice={{ speaking: german.practice!.speaking! }}
        completed={{}}
        writingDraft=""
        onProtocolComplete={() => {}}
        onDraftChange={() => {}}
      />,
    );
    fireEvent.click(screen.getByRole("button", { name: "Copy prompt" }));
    expect(writeText).toHaveBeenLastCalledWith(german.practice!.speaking!.instruction);
  });
});
