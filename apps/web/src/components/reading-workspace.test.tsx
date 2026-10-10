import { fireEvent, render, screen } from "@testing-library/react";
import { beforeEach, describe, expect, it } from "vitest";
import { getReadingReaders, readingSnapshot } from "@/content/reading-catalog";
import { learnerProfileKey } from "@/lib/progress";
import { readingProgressKey } from "@/lib/reading-progress";
import { vocabularyProgressKey } from "@/lib/vocabulary-progress";
import { ReadingWorkspace } from "@/components/reading-workspace";

const learnerId = "local-learner-001";

beforeEach(() => {
  localStorage.clear();
  localStorage.setItem(learnerProfileKey(), JSON.stringify({ version: 2, learnerId, activeLanguage: "en" }));
});

describe("ReadingWorkspace", () => {
  it("renders only supplied reading availability and explicit gaps", async () => {
    render(<ReadingWorkspace />);

    expect(await screen.findByText("Reading")).toBeInTheDocument();
    expect(screen.getByText(/B2, source-authored intensive-reading activities, and an extensive-reading collection are not available/i)).toBeInTheDocument();
    expect(screen.getByText("Extensive reading unavailable")).toBeInTheDocument();
    expect(screen.getByText(/Supplied C1–C2 text only/i)).toBeInTheDocument();
    expect(screen.queryByText(/Reading score/i)).not.toBeInTheDocument();
  });

  it("checks objective answers only against supplied answers without review writes", async () => {
    const reader = getReadingReaders({ mode: "GRADED_OBJECTIVE" })[0]!;
    render(<ReadingWorkspace />);
    const answer = reader.questions![0]!.acceptedAnswers[0]!;

    fireEvent.change(screen.getByLabelText(reader.questions![0]!.prompt), { target: { value: answer } });
    fireEvent.click(screen.getByRole("button", { name: "Check supplied answer" }));
    expect(await screen.findByText(/matches the supplied answer data/i)).toBeInTheDocument();
    expect(localStorage.getItem(`english-master.review.v1.${learnerId}.en.${reader.band}`)).toBeNull();
  });

  it("opens and adds only an exact mapped WordSense", async () => {
    const reader = readingSnapshot.readers.find((item) => item.wordSenseRanges?.length)!;
    render(<ReadingWorkspace />);
    const range = reader.wordSenseRanges![0]!;
    const surface = reader.sourceText.slice(range.start, range.end);

    fireEvent.click(await screen.findByRole("button", { name: surface }));
    expect(screen.getByText("Exact supplied WordSense")).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Add to vocabulary" }));
    expect(await screen.findByRole("button", { name: "Added to vocabulary locally" })).toBeDisabled();

    const stored = localStorage.getItem(vocabularyProgressKey({ learnerId, language: "en" }));
    expect(stored).toContain(range.senseId);
    expect(localStorage.getItem(readingProgressKey({ learnerId, language: "en" }))).toBeNull();
  });

  it("keeps bookmarks in independent reading-local state", async () => {
    render(<ReadingWorkspace />);
    fireEvent.click(await screen.findAllByRole("button", { name: "Bookmark locally" }).then((buttons) => buttons[0]!));
    expect(localStorage.getItem(readingProgressKey({ learnerId, language: "en" }))).toContain("bookmarks");
  });
});
