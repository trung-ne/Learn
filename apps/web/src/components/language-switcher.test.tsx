import { fireEvent, render, screen } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { LanguageSwitcher } from "@/components/language-switcher";
import { loadLearner, setActiveLanguage } from "@/lib/progress";

let pathname = "/learn/en/A1/m16a1-v1-a1-u01/m16a1-v1-a1-u01-l01";

vi.mock("next/navigation", () => ({
  usePathname: () => pathname,
}));

vi.mock("@/lib/progress", () => ({
  loadLearner: vi.fn(),
  setActiveLanguage: vi.fn(),
}));

const courses = [
  { language: "en" as const, level: "A1" as const },
  { language: "de" as const, level: "A1" as const },
];
const learner = { version: 2 as const, learnerId: "local-learner-001", activeLanguage: "en" as const };

describe("language switcher", () => {
  beforeEach(() => {
    pathname = "/learn/en/A1/m16a1-v1-a1-u01/m16a1-v1-a1-u01-l01";
    vi.mocked(loadLearner).mockReturnValue(learner);
    vi.mocked(setActiveLanguage).mockImplementation((current, activeLanguage) => ({ ...current, activeLanguage }));
  });

  it("marks the routed language and moves to a valid target course namespace", () => {
    render(<LanguageSwitcher courses={courses} />);

    expect(screen.getByRole("link", { name: /English English/i })).toHaveAttribute("aria-current", "page");
    const german = screen.getByRole("link", { name: /German Deutsch/i });
    expect(german).toHaveAttribute("href", "/learn/de/A1");
    fireEvent.click(german);
    expect(setActiveLanguage).toHaveBeenCalledWith(learner, "de");
  });
});
