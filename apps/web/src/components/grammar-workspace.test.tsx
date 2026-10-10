import { render, screen } from "@testing-library/react";
import { beforeEach, describe, expect, it } from "vitest";
import { GrammarWorkspace } from "@/components/grammar-workspace";
import { grammarSnapshot } from "@/content/grammar-catalog";
import { grammarProgressKey, recordGrammarTargetResult } from "@/lib/grammar-progress";
import { learnerProfileKey } from "@/lib/progress";

const learnerId = "local-learner-001";

beforeEach(() => {
  localStorage.clear();
  localStorage.setItem(learnerProfileKey(), JSON.stringify({ version: 2, learnerId, activeLanguage: "en" }));
});

describe("GrammarWorkspace", () => {
  it("shows only factual local practice boundaries before an outcome", async () => {
    render(<GrammarWorkspace />);
    expect(await screen.findByText("Grammar practice progress")).toBeInTheDocument();
    expect(screen.getByText(/do not diagnose grammar/i)).toBeInTheDocument();
    expect(screen.queryByText(/proficiency result/i)).not.toBeInTheDocument();
    expect(screen.getByText(/No explicitly linked objective activity has been checked/i)).toBeInTheDocument();
  });

  it("renders an explicitly linked local target outcome and supplied lesson link", async () => {
    const target = grammarSnapshot.targets[0]!;
    const progress = recordGrammarTargetResult(
      { version: 1, learnerId, language: "en", inventoryVersion: grammarSnapshot.inventoryVersion, targets: {} },
      target.id,
      false,
      "2026-10-04T10:00:00.000Z",
    );
    localStorage.setItem(grammarProgressKey({ learnerId, language: "en" }), JSON.stringify(progress));

    render(<GrammarWorkspace />);
    expect(await screen.findByText(/Local activity outcomes:/i)).toBeInTheDocument();
    expect(screen.getByText(/0 correct and 1 incorrect of 1/i)).toBeInTheDocument();
    expect(screen.getByText(/which target caused an incorrect outcome/i)).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Linked supplied activities (2)" })).toBeInTheDocument();
  });
});
