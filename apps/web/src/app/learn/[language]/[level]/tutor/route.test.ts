import { describe, expect, it } from "vitest";
import { tutorHref } from "@/lib/routes";
import { generateStaticParams } from "./page";

describe("static Tutor Context routes", () => {
  it("generates a Tutor Context route for every available course", () => {
    expect(generateStaticParams()).toContainEqual({ language: "en", level: "A1" });
    expect(generateStaticParams()).toContainEqual({ language: "de", level: "A1" });
    expect(tutorHref("en", "B2")).toBe("/learn/en/B2/tutor");
  });
});
