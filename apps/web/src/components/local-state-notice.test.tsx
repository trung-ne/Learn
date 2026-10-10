import { act, render, screen } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it } from "vitest";
import { LocalStateNotice } from "@/components/local-state-notice";
import { reportLocalStateAvailable, reportLocalStateIssue } from "@/lib/local-state";

beforeEach(() => {
  reportLocalStateAvailable();
});

afterEach(() => {
  reportLocalStateAvailable();
});

describe("local storage notice", () => {
  it("announces a storage failure and directs the learner to local recovery tools", () => {
    render(<LocalStateNotice />);
    act(() => reportLocalStateIssue("quota"));

    expect(screen.getByRole("status")).toHaveTextContent("has no room to save");
    expect(screen.getByRole("link", { name: "Open local data and backup tools" })).toHaveAttribute("href", "/data/");
  });
});
