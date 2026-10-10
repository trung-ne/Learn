import { describe, expect, it } from "vitest";
import { getLanguages } from "@/content/catalog";
import { personalStudyPlanHref } from "@/lib/routes";
import { generateStaticParams } from "./page";

describe("static personal study plan routes", () => {
  it("generates one route for every supported target language", () => {
    const params = generateStaticParams();
    const languages = getLanguages().map((language) => language.code);

    expect(params).toEqual(languages.map((language) => ({ language })));
    expect(params.map((item) => personalStudyPlanHref(item.language))).toEqual(languages.map(personalStudyPlanHref));
  });
});
