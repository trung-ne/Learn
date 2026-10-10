import { fireEvent, render, screen } from "@testing-library/react";
import { beforeEach, describe, expect, it } from "vitest";
import { DictionaryWorkspace } from "@/components/dictionary-workspace";
import { learnerProfileKey } from "@/lib/progress";

beforeEach(() => {
  localStorage.clear();
  localStorage.setItem(learnerProfileKey(), JSON.stringify({ version: 2, learnerId: "local-learner-001", activeLanguage: "en" }));
});

describe("DictionaryWorkspace", () => {
  it("searches supplied take records and exposes exact linked lexical material", async () => {
    render(<DictionaryWorkspace />);
    expect(await screen.findByRole("heading", { name: "Dictionary / Language Library" })).toBeInTheDocument();
    expect(screen.getAllByText("○ not learned")).not.toHaveLength(0);
    fireEvent.change(screen.getByLabelText(/Search a supplied word/i), { target: { value: "take" } });
    expect(screen.getAllByRole("button", { name: /○ not learned/i })).toHaveLength(10);
    fireEvent.click(screen.getByRole("button", { name: /Sense 1/i }));
    expect(screen.getByRole("heading", { name: "take" })).toBeInTheDocument();
    expect(screen.getByText("take off (A2)")).toBeInTheDocument();
    expect(screen.getByText("take responsibility")).toBeInTheDocument();
    expect(screen.getByText("take action")).toBeInTheDocument();
    expect(screen.getByText("take a break")).toBeInTheDocument();
    expect(screen.getByText("taking (A1)")).toBeInTheDocument();
  });

  it("does not write on search and changes local status only after explicit actions", async () => {
    render(<DictionaryWorkspace />);
    await screen.findByRole("heading", { name: "Dictionary / Language Library" });
    fireEvent.change(screen.getByLabelText(/Search a supplied word/i), { target: { value: "take off" } });
    const before = localStorage.length;
    fireEvent.click(screen.getByRole("button", { name: /take off/i }));
    expect(localStorage.length).toBe(before);
    fireEvent.click(screen.getByRole("button", { name: "Start local study" }));
    expect(screen.getAllByText("◉ learning")).not.toHaveLength(0);
    fireEvent.click(screen.getByRole("button", { name: "I need to review it" }));
    expect(screen.getAllByText("! weak")).not.toHaveLength(0);
  });
});
