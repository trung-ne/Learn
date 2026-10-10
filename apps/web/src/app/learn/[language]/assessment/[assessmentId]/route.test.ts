import { describe, expect, it } from "vitest";
import { getAssessmentPackages } from "@/content/assessment-catalog";
import { assessmentHref, assessmentPackageHref } from "@/lib/routes";
import { generateStaticParams as packageParams } from "./page";

describe("English assessment package route", () => {
  it("generates one English-only static path for every verified package", () => {
    const expected = getAssessmentPackages().map((assessment) => ({ language: "en", assessmentId: assessment.id }));

    expect(packageParams()).toEqual(expected);
    expect(new Set(packageParams().map((item) => `${item.language}/${item.assessmentId}`)).size).toBe(expected.length);
  });

  it("uses canonical English assessment paths", () => {
    const assessment = getAssessmentPackages()[0]!;
    expect(assessmentHref()).toBe("/learn/en/assessment");
    expect(assessmentPackageHref(assessment.id)).toBe(`/learn/en/assessment/${assessment.id}`);
  });
});
