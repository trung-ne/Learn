import { describe, expect, it } from "vitest";
import { getLanguages } from "@/content/catalog";
import { progressDashboardHref } from "@/lib/routes";
import { generateStaticParams } from "./page";

describe("static progress dashboard routes", () => {
  it("generates one route for every supported target language", () => {
    const params = generateStaticParams();
    const languages = getLanguages().map((language) => language.code);

    expect(params).toEqual(languages.map((language) => ({ language })));
    expect(params.map((item) => progressDashboardHref(item.language))).toEqual(languages.map(progressDashboardHref));
  });
});
