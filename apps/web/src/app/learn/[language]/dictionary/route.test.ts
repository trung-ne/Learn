import { describe, expect, it } from "vitest";
import { generateStaticParams } from "./page";
import { dictionaryHref } from "@/lib/routes";

describe("dictionary route", () => {
  it("generates only the explicit English dictionary route", () => {
    expect(generateStaticParams()).toEqual([{ language: "en" }]);
    expect(dictionaryHref()).toBe("/learn/en/dictionary");
  });
});
