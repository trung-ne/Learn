import { describe, expect, it } from "vitest";
import { asEnglishLesson, asGermanLesson } from "@/content/adapters";
import {
  getLanguages,
  getLesson,
  getLessonsForLanguage,
  getLessonsForLanguageLevel,
  groupLessonsByTierAndUnit,
  snapshot,
} from "@/content/catalog";
import { languages } from "@/content/languages";
import { lessonHref } from "@/lib/routes";

describe("curriculum catalog", () => {
  it("contains the closed English and German learner inventory", () => {
    expect(snapshot.contentStatus).toBe("UNREVIEWED");
    expect(snapshot.lessons).toHaveLength(310);
    expect(getLessonsForLanguage("en")).toHaveLength(300);
    expect(getLessonsForLanguage("de")).toHaveLength(10);
    expect(getLanguages().map((language) => language.code)).toEqual(["en", "de"]);
    expect(Object.keys(languages)).toEqual(getLanguages().map((language) => language.code));
    expect(new Set(snapshot.lessons.map((lesson) => `${lesson.language}:${lesson.lessonId}`)).size).toBe(310);
  });

  it("filters available lesson levels by configured language", () => {
    expect(getLessonsForLanguageLevel("en", "A1")).toHaveLength(50);
    expect(getLessonsForLanguageLevel("en", "C2")).toHaveLength(50);
    expect(getLessonsForLanguageLevel("de", "A1")).toHaveLength(10);
    expect(languages.de.availableLevels).toEqual(["A1"]);
  });

  it("keeps language-specific packet families and route tuples separated", () => {
    const english = getLesson("en", "A1", "m16a1-v1-a1-u01", "m16a1-v1-a1-u01-l01");
    const german = getLesson("de", "A1", "de-a1-v1-u01", "de-a1-v1-u01-l01");
    expect(english && asEnglishLesson(english).packetFamily).toBe("english-full");
    expect(german && asGermanLesson(german).packetFamily).toBe("german-pilot");
    expect(german?.exercises.find((exercise) => exercise.type === "ordering")?.correct_order).toEqual([
      "Begrüßung",
      "Angabe",
      "Frage",
    ]);
    expect(getLesson("de", "A1", "de-a1-v1-u01", "m16a1-v1-a1-u01-l01")).toBeUndefined();
    expect(getLesson("en", "A2", "m16a1-v1-a1-u01", "m16a1-v1-a1-u01-l01")).toBeUndefined();
    expect(getLesson("en", "A1", "wrong-unit", "m16a1-v1-a1-u01-l01")).toBeUndefined();
  });

  it("creates one canonical course path for every lesson", () => {
    const paths = snapshot.lessons.map(lessonHref);
    expect(new Set(paths).size).toBe(310);
    expect(paths).toContain("/learn/en/A1/m16a1-v1-a1-u01/m16a1-v1-a1-u01-l01");
    expect(paths).toContain("/learn/de/A1/de-a1-v1-u01/de-a1-v1-u01-l01");
  });

  it("groups lessons by their internal tier and unit", () => {
    const groups = groupLessonsByTierAndUnit(getLessonsForLanguage("de"));
    expect(groups.get("A1.1")?.size).toBe(2);
    expect(groups.get("A1.1")?.get("de-a1-v1-u01")).toHaveLength(5);
  });
});
