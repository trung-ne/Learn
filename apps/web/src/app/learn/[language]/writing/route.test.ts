import { describe, expect, it } from "vitest";
import { writingHref } from "@/lib/routes";
import { generateStaticParams } from "./page";

describe("static writing routes", () => {
  it("generates the supplied English-only writing route", () => {
    expect(generateStaticParams()).toEqual([{ language: "en" }]);
    expect(writingHref("en")).toBe("/learn/en/writing");
  });
});
