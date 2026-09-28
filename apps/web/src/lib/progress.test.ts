import { describe, expect, it } from "vitest";
import {
  emptyProgress,
  learnerProfileKey,
  loadLearner,
  loadProgress,
  parseProgress,
  progressKey,
  resetExerciseRunner,
  resetProgress,
  resumeLessonId,
  saveProgress,
  setActiveLanguage,
  summarizeCourseProgress,
  updateConceptProgress,
  updateLessonProgress,
  type CourseScope,
  type StorageLike,
} from "@/lib/progress";

function memoryStorage(): StorageLike & { readonly values: Map<string, string> } {
  const values = new Map<string, string>();
  return {
    values,
    getItem: (key) => values.get(key) ?? null,
    setItem: (key, value) => { values.set(key, value); },
    removeItem: (key) => { values.delete(key); },
  };
}

const englishA1: CourseScope = { learnerId: "local-learner-001", language: "en", course: "A1" };
const englishA2: CourseScope = { learnerId: "local-learner-001", language: "en", course: "A2" };
const germanA1: CourseScope = { learnerId: "local-learner-001", language: "de", course: "A1" };

describe("learner and course-scoped local progress", () => {
  it("keeps profile state local and persists an active target language", () => {
    const storage = memoryStorage();
    storage.setItem(learnerProfileKey(), JSON.stringify({ version: 2, learnerId: "local-learner-001", activeLanguage: "en" }));

    const learner = setActiveLanguage(loadLearner(storage), "de", storage);

    expect(learner.activeLanguage).toBe("de");
    expect(loadLearner(storage)).toEqual(learner);
  });

  it("isolates course records by learner, language, and course", () => {
    const storage = memoryStorage();
    const english = updateLessonProgress(emptyProgress(englishA1), "m16a1-v1-a1-u01-l01", { completed: true });
    saveProgress(english, storage);

    expect(loadProgress(englishA1, storage).lessons["m16a1-v1-a1-u01-l01"]?.completed).toBe(true);
    expect(loadProgress(englishA2, storage).lessons).toEqual({});
    expect(loadProgress(germanA1, storage).lessons).toEqual({});
    expect(progressKey(englishA1)).not.toBe(progressKey(englishA2));
    expect(progressKey(englishA1)).not.toBe(progressKey(germanA1));
    expect(progressKey(englishA1)).not.toBe(progressKey({ ...englishA1, learnerId: "local-learner-002" }));
  });

  it("rejects malformed and scope-mismatched records", () => {
    expect(parseProgress("not json", englishA1)).toEqual(emptyProgress(englishA1));
    expect(parseProgress(JSON.stringify(emptyProgress(germanA1)), englishA1)).toEqual(emptyProgress(englishA1));
    expect(parseProgress(JSON.stringify({
      ...emptyProgress(englishA1),
      lessons: { "../bad": { completed: true, attempts: {}, protocols: {}, drafts: {} } },
    }), englishA1)).toEqual(emptyProgress(englishA1));
  });

  it("persists minimal exercise state without retaining learner responses", () => {
    const lessonId = "m16a1-v1-a1-u01-l01";
    const progress = updateLessonProgress(emptyProgress(englishA1), lessonId, {
      lastAccessedAt: "2026-09-26T12:00:00.000Z",
      attempts: { "meaning-check": 2 },
      exerciseRunner: {
        currentExerciseId: "meaning-check",
        finished: false,
        exercises: {
          "meaning-check": { lastResult: "incorrect", completed: false },
          "personal-response": { lastResult: "self_practice", completed: true },
        },
      },
    });

    const serialized = JSON.stringify(progress);
    expect(parseProgress(serialized, englishA1)).toEqual(progress);
    expect(serialized).not.toContain("learner answer");
    expect(progress.lessons[lessonId]?.lastAccessedAt).toBe("2026-09-26T12:00:00.000Z");
    expect(progress.lessons[lessonId]?.exerciseRunner?.exercises["meaning-check"]).toEqual({
      lastResult: "incorrect",
      completed: false,
    });
  });

  it("rejects malformed exercise state and clears only the exercise runner on restart", () => {
    const lessonId = "m16a1-v1-a1-u01-l01";
    const malformed = {
      ...emptyProgress(englishA1),
      lessons: {
        [lessonId]: {
          completed: false,
          attempts: {},
          protocols: {},
          drafts: {},
          lastAccessedAt: "not-a-timestamp",
        },
      },
    };
    expect(parseProgress(JSON.stringify(malformed), englishA1)).toEqual(emptyProgress(englishA1));

    const progress = updateLessonProgress(emptyProgress(englishA1), lessonId, {
      completed: true,
      attempts: { "meaning-check": 1 },
      exerciseRunner: {
        currentExerciseId: "meaning-check",
        finished: true,
        exercises: { "meaning-check": { lastResult: "correct", completed: true } },
      },
    });
    const restarted = resetExerciseRunner(progress, lessonId);

    expect(restarted.lessons[lessonId]).toEqual({
      completed: true,
      attempts: { "meaning-check": 1 },
      protocols: {},
      drafts: {},
    });
  });

  it("keeps lesson and concept progress in independent namespaces", () => {
    const withLesson = updateLessonProgress(emptyProgress(englishA1), "m16a1-v1-a1-u01-l01", { completed: true });
    const withConcept = updateConceptProgress(withLesson, "kg-en-a1-grammar", 3);

    expect(withConcept.lessons["m16a1-v1-a1-u01-l01"]?.completed).toBe(true);
    expect(withConcept.concepts["kg-en-a1-grammar"]?.reviews).toBe(3);
  });

  it("summarizes only the current inventory and orders last access by timestamp", () => {
    const progress = updateLessonProgress(
      updateLessonProgress(emptyProgress(englishA1), "m16a1-v1-a1-u01-l01", {
        completed: true,
        lastAccessedAt: "2026-09-26T12:00:00.000Z",
      }),
      "m16a1-v1-a1-u01-l02",
      { lastAccessedAt: "2026-09-26T13:00:00.000Z" },
    );
    const summary = summarizeCourseProgress(progress, [
      { lessonId: "m16a1-v1-a1-u01-l01", unitId: "m16a1-v1-a1-u01" },
      { lessonId: "m16a1-v1-a1-u01-l02", unitId: "m16a1-v1-a1-u01" },
      { lessonId: "m16a1-v1-a1-u02-l01", unitId: "m16a1-v1-a1-u02" },
    ]);

    expect(summary).toMatchObject({
      completedLessons: 1,
      totalLessons: 3,
      currentLessonId: "m16a1-v1-a1-u01-l02",
      lastAccessedLessonId: "m16a1-v1-a1-u01-l02",
      lastAccessedAt: "2026-09-26T13:00:00.000Z",
    });
    expect(summary.units).toEqual([
      { unitId: "m16a1-v1-a1-u01", completedLessons: 1, totalLessons: 2 },
      { unitId: "m16a1-v1-a1-u02", completedLessons: 0, totalLessons: 1 },
    ]);

    const stale = summarizeCourseProgress(
      updateLessonProgress(progress, "m16a1-v1-a1-u99-l01", { completed: true }),
      [{ lessonId: "m16a1-v1-a1-u01-l01", unitId: "m16a1-v1-a1-u01" }],
    );
    expect(stale).toMatchObject({ completedLessons: 1, totalLessons: 1, currentLessonId: undefined });
  });

  it("resets only the selected course and resumes only valid lesson IDs", () => {
    const storage = memoryStorage();
    const english = updateLessonProgress(emptyProgress(englishA1), "m16a1-v1-a1-u01-l01", { completed: true });
    const german = updateLessonProgress(emptyProgress(germanA1), "de-a1-v1-u01-l01", { completed: true });
    saveProgress(english, storage);
    saveProgress(german, storage);

    expect(resumeLessonId(english, ["m16a1-v1-a1-u01-l01", "m16a1-v1-a1-u01-l02"])).toBe("m16a1-v1-a1-u01-l01");
    expect(resumeLessonId({ ...english, lastLessonId: "missing-lesson" }, ["m16a1-v1-a1-u01-l01", "m16a1-v1-a1-u01-l02"])).toBe("m16a1-v1-a1-u01-l02");
    expect(resetProgress(englishA1, storage)).toBe(true);
    expect(loadProgress(englishA1, storage).lessons).toEqual({});
    expect(loadProgress(germanA1, storage).lessons["de-a1-v1-u01-l01"]?.completed).toBe(true);
  });
});
