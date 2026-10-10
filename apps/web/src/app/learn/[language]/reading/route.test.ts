import { describe, expect, it } from "vitest";
import { readingHref } from "@/lib/routes";
import { generateStaticParams } from "./page";

describe("static reading routes", () => {
  it("generates the supplied English-only reading route", () => {
    expect(generateStaticParams()).toEqual([{ language: "en" }]);
    expect(readingHref("en")).toBe("/learn/en/reading");
  });
});
