import { describe, expect, it } from "vitest";
import { snapshot } from "@/content/catalog";
import { lessonHref } from "@/lib/routes";
import { generateStaticParams } from "./page";

describe("static lesson routes", () => {
  it("generates the exact validated English and German lesson inventory", () => {
    const params = generateStaticParams();
    expect(params).toHaveLength(snapshot.lessons.length);
    const paths = params.map((item) => `/learn/${item.language}/${item.level}/${item.unit}/${item.lesson}`);
    expect(new Set(paths).size).toBe(snapshot.lessons.length);
    expect(paths).toContain("/learn/en/A1/m16a1-v1-a1-u01/m16a1-v1-a1-u01-l01");
    expect(paths).toContain("/learn/de/A1/de-a1-v1-u01/de-a1-v1-u01-l01");
    expect(paths).toEqual(snapshot.lessons.map(lessonHref));
  });
});
