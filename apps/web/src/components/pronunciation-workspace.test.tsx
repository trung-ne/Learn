import { render, screen } from "@testing-library/react";
import { beforeEach, describe, expect, it } from "vitest";
import { PronunciationWorkspace } from "@/components/pronunciation-workspace";
import { pronunciationSnapshot } from "@/content/pronunciation-catalog";
import { learnerProfileKey, progressKey } from "@/lib/progress";

const learnerId = "local-learner-001";

beforeEach(() => {
  localStorage.clear();
  localStorage.setItem(learnerProfileKey(), JSON.stringify({ version: 2, learnerId, activeLanguage: "en" }));
});

describe("PronunciationWorkspace", () => {
  it("shows supplied protocols with an explicit audio-free assessment boundary", async () => {
    render(<PronunciationWorkspace language="en" />);

    expect(await screen.findByText("Pronunciation self-practice")).toBeInTheDocument();
    expect(screen.getByText(/No model audio, recording, upload/i)).toBeInTheDocument();
    expect(screen.getByText(/does not update Review, grammar or vocabulary progress/i)).toBeInTheDocument();
    expect(screen.getByText("NOT ASSESSED")).toBeInTheDocument();
    expect(screen.queryByText(/Score:/i)).not.toBeInTheDocument();
  });

  it("counts only the existing lesson-local pronunciation marker", async () => {
    const protocol = pronunciationSnapshot.protocols.find((item) => item.language === "en")!;
    localStorage.setItem(progressKey({ learnerId, language: "en", course: protocol.band }), JSON.stringify({
      version: 2,
      learnerId,
      language: "en",
      course: protocol.band,
      lessons: { [protocol.lessonId]: { completed: false, attempts: {}, protocols: { pronunciation: true }, drafts: {} } },
      concepts: {},
    }));

    render(<PronunciationWorkspace language="en" />);
    expect(await screen.findByText("marked in this browser")).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Open supplied lesson" })).toBeInTheDocument();
  });
});
