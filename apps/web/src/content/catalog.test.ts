import { describe, expect, it } from "vitest";
import { asEnglishLesson, asGermanLesson } from "@/content/adapters";
import {
  getAvailableCourses,
  getLanguages,
  getLesson,
  getLessonsForLanguage,
  getLessonsForLanguageLevel,
  groupLessonsByTierAndUnit,
  snapshot,
  validateSnapshot,
} from "@/content/catalog";
import { languages } from "@/content/languages";
import { lessonHref } from "@/lib/routes";

describe("curriculum catalog", () => {
  it("contains the closed English and German learner inventory", () => {
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

  it("derives navigable courses only from the current packet inventory", () => {
    expect(getAvailableCourses("en").map((course) => course.level)).toEqual(["A1", "A2", "B1", "B2", "C1", "C2"]);
    expect(getAvailableCourses("de").map((course) => course.level)).toEqual(["A1"]);
    expect(getAvailableCourses("de")[0]?.availability).toBe("PILOT");
    expect(getAvailableCourses().map((course) => `${course.language}:${course.level}`)).toEqual([
      "en:A1", "en:A2", "en:B1", "en:B2", "en:C1", "en:C2", "de:A1",
    ]);
  });

  it("keeps language-specific packet families and route tuples separated", () => {
    const english = getLesson("en", "A1", "m16a1-v1-a1-u01", "m16a1-v1-a1-u01-l01");
    const german = getLesson("de", "A1", "de-a1-v1-u01", "de-a1-v1-u01-l01");
    expect(english && asEnglishLesson(english).language).toBe("en");
    expect(german && asGermanLesson(german).language).toBe("de");
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

  it("rejects malformed learner-facing snapshot fields and hidden source metadata", () => {
    const malformedObjective = structuredClone(snapshot) as { lessons: Array<Record<string, unknown>> };
    malformedObjective.lessons[0]!.objectives = ["Valid", 4];
    expect(() => validateSnapshot(malformedObjective)).toThrow(/objectives/i);

    const leakedMetadata = structuredClone(snapshot) as typeof snapshot & {
      lessons: Array<Record<string, unknown>>;
    };
    leakedMetadata.lessons[0]!.target_ids = ["internal-target"];
    expect(() => validateSnapshot(leakedMetadata)).toThrow(/unsupported learner-facing fields/i);
  });

  it("rejects blank values, duplicate local IDs, and unusable objective exercises", () => {
    const blankTitle = structuredClone(snapshot) as { lessons: Array<Record<string, unknown>> };
    blankTitle.lessons[0]!.title = "   ";
    expect(() => validateSnapshot(blankTitle)).toThrow(/unsupported lesson/i);

    const duplicateExercise = structuredClone(snapshot) as {
      lessons: Array<Record<string, unknown>>;
    };
    const exercises = duplicateExercise.lessons[0]!.exercises as Array<Record<string, unknown>>;
    exercises[1]!.id = exercises[0]!.id;
    expect(() => validateSnapshot(duplicateExercise)).toThrow(/duplicate.*exercise/i);

    const missingChoiceAnswer = structuredClone(snapshot) as {
      lessons: Array<Record<string, unknown>>;
    };
    const choice = (missingChoiceAnswer.lessons[0]!.exercises as Array<Record<string, unknown>>)
      .find((exercise) => exercise.type === "multiple_choice")!;
    delete choice.correct_answer;
    delete choice.acceptable_answers;
    delete choice.answer;
    expect(() => validateSnapshot(missingChoiceAnswer)).toThrow(/answer data/i);
  });

  it("groups lessons by their internal tier and unit", () => {
    const groups = groupLessonsByTierAndUnit(getLessonsForLanguage("de"));
    expect(groups.get("A1.1")?.size).toBe(2);
    expect(groups.get("A1.1")?.get("de-a1-v1-u01")).toHaveLength(5);
  });
});
