import { describe, expect, it } from "vitest";
import {
  BAND_ORDER,
  compareBands,
  emptyTutorPreferences,
  isCourseCompatible,
  loadTutorPreferences,
  parseTutorPreferences,
  projectTutorContext,
  resetTutorPreferences,
  saveTutorPreferences,
  serializeTutorContext,
  tutorPreferencesKey,
  type TutorPreferenceScope,
} from "@/lib/tutor-context";
import type { StorageLike } from "@/lib/progress";

function memoryStorage(): StorageLike & { readonly values: Map<string, string> } {
  const values = new Map<string, string>();
  return {
    values,
    getItem: (key) => values.get(key) ?? null,
    setItem: (key, value) => { values.set(key, value); },
    removeItem: (key) => { values.delete(key); },
  };
}

const english: TutorPreferenceScope = { learnerId: "local-learner-001", language: "en" };
const german: TutorPreferenceScope = { learnerId: "local-learner-001", language: "de" };

describe("tutor preferences", () => {
  it("orders bands and checks current-course compatibility", () => {
    expect(BAND_ORDER).toEqual(["A1", "A2", "B1", "B2", "C1", "C2"]);
    expect(compareBands("A1", "C2")).toBeLessThan(0);
    expect(isCourseCompatible("B1", "A2")).toBe(true);
    expect(isCourseCompatible("A1", "A2")).toBe(false);
    expect(isCourseCompatible(undefined, "A1")).toBe(false);
  });

  it("parses only scoped preferences with fixed goals and a higher target", () => {
    const serialized = JSON.stringify({
      version: 1, ...english, currentBand: "A2", targetBand: "B2",
      goals: ["writing", "conversation"],
    });
    expect(parseTutorPreferences(serialized, english)).toEqual({
      version: 1, ...english, currentBand: "A2", targetBand: "B2",
      goals: ["conversation", "writing"],
    });
    expect(parseTutorPreferences(serialized, german)).toEqual(emptyTutorPreferences(german));
    expect(parseTutorPreferences(JSON.stringify({
      version: 1, ...english, currentBand: "B2", targetBand: "A2", goals: [],
    }), english)).toEqual(emptyTutorPreferences(english));
    expect(parseTutorPreferences(JSON.stringify({
      version: 1, ...german, currentBand: "A1", goals: ["grammar"],
    }), german)).toEqual(emptyTutorPreferences(german));
  });

  it("retains only supported daily planning allocations", () => {
    const preferences = {
      version: 1 as const, ...english, currentBand: "A2" as const,
      targetBand: "B2" as const, dailyAllocationMinutes: 45 as const, goals: [],
    };
    expect(parseTutorPreferences(JSON.stringify(preferences), english)).toEqual(preferences);
    expect(parseTutorPreferences(JSON.stringify({ ...preferences, dailyAllocationMinutes: 47 }), english))
      .toEqual(emptyTutorPreferences(english));
    const storage = memoryStorage();
    expect(saveTutorPreferences({ ...preferences, dailyAllocationMinutes: 47 as never }, storage)).toBe(false);
  });

  it("loads, saves, resets, and isolates learner-language records", () => {
    const storage = memoryStorage();
    const preferences = {
      version: 1 as const, ...english, currentBand: "A1" as const,
      targetBand: "A2" as const, goals: ["listening" as const],
    };
    expect(saveTutorPreferences(preferences, storage)).toBe(true);
    expect(loadTutorPreferences(english, storage)).toEqual(preferences);
    expect(loadTutorPreferences(german, storage)).toEqual(emptyTutorPreferences(german));
    expect(tutorPreferencesKey(english)).not.toBe(tutorPreferencesKey(german));
    expect(resetTutorPreferences(english, storage)).toBe(true);
    expect(storage.values.has(tutorPreferencesKey(english))).toBe(false);
  });
});

describe("learner-safe tutor context", () => {
  it("projects bounded, deterministic safe labels and exact local states", () => {
    const context = projectTutorContext(
      { version: 1, ...english, currentBand: "B1", targetBand: "B2", goals: ["vocabulary", "grammar"] },
      {
        language: "en",
        course: "A2",
        recentLessons: [
          { title: "Later lesson", recencyOrder: 2 },
          { title: "Most recent lesson", recencyOrder: 0 },
          { title: "Second lesson", recencyOrder: 1 },
          { title: "Third lesson", recencyOrder: 3 },
          { title: "Fourth lesson", recencyOrder: 4 },
          { title: "Excluded sixth lesson", recencyOrder: 5 },
        ],
        vocabulary: [
          { label: "book — printed work", state: "reviewing", order: 1 },
          { label: "hello — greeting", state: "learning", order: 0 },
        ],
        grammar: [{ label: "present simple", state: "locally_consolidated", order: 0 }],
        outcomePatterns: [{
          label: "Choosing a greeting", incorrectOutcomes: 2, reviewCount: 3,
          recentIncorrect: true, repeatedIncorrect: true, order: 0,
        }],
        reviewItems: [
          { label: "hello — greeting", source: "vocabulary", priority: "due", order: 1 },
          { label: "Choosing a greeting", source: "objective_activity", priority: "recent_incorrect", order: 0 },
        ],
      },
    );

    expect(context.course).toBe("A2");
    expect(context.recentLessonTitles).toEqual([
      "Most recent lesson", "Second lesson", "Later lesson", "Third lesson", "Fourth lesson",
    ]);
    expect(context.vocabulary).toEqual([
      { label: "hello — greeting", state: "learning" },
      { label: "book — printed work", state: "reviewing" },
    ]);
    expect(context.grammar).toEqual([{ label: "present simple", state: "locally_consolidated" }]);
    expect(context.objectiveActivityOutcomePatterns[0]).toMatchObject({
      label: "Choosing a greeting", incorrectOutcomes: 2, recentIncorrect: true,
    });
    expect(context.reviewItems.map((item) => item.label)).toEqual(["Choosing a greeting", "hello — greeting"]);
  });

  it("excludes incompatible or wrong-language sources and omits grammar for German", () => {
    const incompatible = projectTutorContext(
      { version: 1, ...english, currentBand: "A1", goals: [] },
      { language: "en", course: "A2", recentLessons: [{ title: "Hidden", recencyOrder: 0 }] },
    );
    expect(incompatible.course).toBeUndefined();
    expect(incompatible.recentLessonTitles).toEqual([]);

    const germanContext = projectTutorContext(
      { version: 1, ...german, currentBand: "A1", goals: ["conversation"] },
      {
        language: "de", course: "A1",
        grammar: [{ label: "German grammar must not project", state: "practising", order: 0 }],
      },
    );
    expect(germanContext.grammar).toBeUndefined();
    expect(serializeTutorContext(germanContext)).toContain("Target language: German");
  });

  it("serializes no learner IDs, raw IDs, timestamps, drafts, or answers", () => {
    const context = projectTutorContext(
      { version: 1, ...english, currentBand: "A1", goals: ["conversation"] },
      {
        language: "en", course: "A1",
        recentLessons: [{ title: "Greetings in the morning", recencyOrder: 0 }],
        reviewItems: [{ label: "Select a morning greeting", source: "objective_activity", priority: "due", order: 0 }],
      },
    );
    const output = `${JSON.stringify(context)}\n${serializeTutorContext(context)}`;
    expect(output).toContain("Greetings in the morning");
    expect(output).toContain("You are an external practice partner");
    expect(output).toContain("not proficiency or diagnostic results");
    expect(output).not.toContain(english.learnerId);
    expect(output).not.toMatch(/lessonId|exerciseId|senseId|targetId|timestamp|draft|answer/iu);
  });
});
