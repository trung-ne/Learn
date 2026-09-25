import { describe, expect, it } from "vitest";
import { arraysMatch, matchesAnyAnswer, normalizeAnswer } from "@/lib/answers";

describe("answer helpers", () => {
  it("normalizes Unicode, whitespace, and case conservatively", () => {
    expect(normalizeAnswer("  CAFÉ\nLAN  ")).toBe("café lan");
    expect(matchesAnyAnswer("café   lan", ["Café Lan"])).toBe(true);
  });

  it("compares ordering answers positionally", () => {
    expect(arraysMatch(["First", "Second"], ["first", "second"])).toBe(true);
    expect(arraysMatch(["Second", "First"], ["first", "second"])).toBe(false);
  });
});
