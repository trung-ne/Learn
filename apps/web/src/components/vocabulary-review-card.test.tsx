import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { VocabularyReviewCard } from "@/components/vocabulary-review-card";
import { getVocabularySense } from "@/content/vocabulary-catalog";

const hello = getVocabularySense("vocab-en-hello-001")!;

describe("VocabularyReviewCard", () => {
  it("keeps the answer concealed until recall begins and reports a correct answer once", () => {
    const onResult = vi.fn();
    render(<VocabularyReviewCard sense={hello} isNew={false} onStart={vi.fn()} onResult={onResult} />);

    expect(screen.queryByLabelText(hello.recallPrompt)).not.toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Try recall" }));
    fireEvent.change(screen.getByLabelText(hello.recallPrompt), { target: { value: "hello" } });
    fireEvent.click(screen.getByRole("button", { name: "Check answer" }));

    expect(onResult).toHaveBeenCalledWith(true);
    expect(screen.getByText("Correct — hello.")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Check answer" })).toBeDisabled();
  });

  it("shows a start action without logging an answer for a new word", () => {
    const onStart = vi.fn();
    render(<VocabularyReviewCard sense={hello} isNew onStart={onStart} onResult={vi.fn()} />);

    fireEvent.click(screen.getByRole("button", { name: "Start learning this word" }));
    expect(onStart).toHaveBeenCalledOnce();
    expect(screen.queryByRole("button", { name: "Check answer" })).not.toBeInTheDocument();
  });
});
