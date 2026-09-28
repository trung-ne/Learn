import { describe, expect, it } from "vitest";
import { switchDestination } from "@/lib/language-switching";

const courses = [
  { language: "en" as const, level: "A1" as const },
  { language: "en" as const, level: "A2" as const },
  { language: "de" as const, level: "A1" as const },
];

describe("switchDestination", () => {
  it("retains an available course but never reuses a lesson path", () => {
    expect(switchDestination("/learn/en/A1/m16a1-v1-a1-u01/m16a1-v1-a1-u01-l01", "de", courses)).toBe("/learn/de/A1");
  });

  it("uses the language landing page when that target course is unavailable", () => {
    expect(switchDestination("/learn/en/A2/m16a2-v1-a2-u01/m16a2-v1-a2-u01-l01", "de", courses)).toBe("/learn/de");
  });

  it("uses the language landing page outside a course route", () => {
    expect(switchDestination("/learn", "de", courses)).toBe("/learn/de");
  });
});
