import { render, screen } from "@testing-library/react";
import { beforeEach, describe, expect, it } from "vitest";
import { SpeakingWorkspace } from "@/components/speaking-workspace";
import { speakingSnapshot } from "@/content/speaking-catalog";
import { learnerProfileKey, progressKey } from "@/lib/progress";

const learnerId = "local-learner-001";

beforeEach(() => {
  localStorage.clear();
  localStorage.setItem(learnerProfileKey(), JSON.stringify({ version: 2, learnerId, activeLanguage: "en" }));
});

describe("SpeakingWorkspace", () => {
  it("shows source-backed protocols and explicitly unavailable assessment dimensions", async () => {
    const { container } = render(<SpeakingWorkspace language="en" />);

    expect(await screen.findByText("Speaking self-practice")).toBeInTheDocument();
    expect(screen.getByText(/No recording, chat simulation, provider, generated feedback/i)).toBeInTheDocument();
    expect(screen.getByText(/does not update Review, grammar, vocabulary/i)).toBeInTheDocument();
    expect(screen.getAllByText("NOT ASSESSED").length).toBeGreaterThanOrEqual(7);
    expect(screen.getByText("Repeat")).toBeInTheDocument();
    expect(screen.getByText("Free speaking")).toBeInTheDocument();
    expect(screen.getByText(/Discuss nuanced abstract topics/i)).toBeInTheDocument();
    expect(container.querySelector("audio")).toBeNull();
    expect(container.querySelector('input[type="file"]')).toBeNull();
    expect(screen.queryByText(/Score:/i)).not.toBeInTheDocument();
  });

  it("counts only the existing lesson-local speaking marker", async () => {
    const protocol = speakingSnapshot.protocols.find((item) => item.language === "en")!;
    localStorage.setItem(progressKey({ learnerId, language: "en", course: protocol.band }), JSON.stringify({
      version: 2,
      learnerId,
      language: "en",
      course: protocol.band,
      lessons: { [protocol.lessonId]: { completed: false, attempts: {}, protocols: { speaking: true }, drafts: {} } },
      concepts: {},
    }));

    render(<SpeakingWorkspace language="en" />);
    expect(await screen.findByText("marked in this browser")).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Open supplied lesson" })).toBeInTheDocument();
  });
});
