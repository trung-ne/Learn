import { describe, expect, it } from "vitest";
import {
  getVocabularyForLesson,
  getVocabularySense,
  getVocabularySenseIdsForExercise,
  getVocabularySenses,
  validateVocabularySnapshot,
} from "@/content/vocabulary-catalog";

describe("learner-facing vocabulary catalog", () => {
  it("exposes the English inventory without upstream target or packet metadata", () => {
    const senses = getVocabularySenses("en");
    expect(senses).toHaveLength(20);
    expect(getVocabularySenses("de")).toEqual([]);
    expect(JSON.stringify(senses)).not.toContain("source_target_id");
    expect(JSON.stringify(senses)).not.toContain("packet_sha256");
    expect(getVocabularySense("vocab-en-hello-001")?.lemma).toBe("hello");
  });

  it("resolves only explicit lesson and exercise mappings", () => {
    expect(getVocabularyForLesson("en", "m16a1-v1-a1-u01-l01").map((sense) => sense.lemma)).toEqual([
      "goodbye", "greeting", "hello", "hi",
    ]);
    expect(getVocabularySenseIdsForExercise("en", "m16a1-v1-a1-u01-l01", "meaning-check")).toEqual([
      "vocab-en-goodbye-001", "vocab-en-hello-001",
    ]);
    expect(getVocabularySenseIdsForExercise("en", "m16a1-v1-a1-u01-l01", "personal-response")).toEqual([]);
  });

  it("rejects unsupported learner-facing fields and duplicate identities", () => {
    expect(() => validateVocabularySnapshot({
      schemaVersion: "1.0", inventoryVersion: "test", senses: [{
        id: "vocab-en-test-001", language: "en", band: "A1", tier: "A1.1", lemma: "test", senseNumber: 1,
        partOfSpeech: "noun", definition: "a test", examples: ["A test."], collocations: ["a test"],
        introductionLessonId: "lesson-one", recallPrompt: "Test?", acceptedAnswers: ["test"], distractors: ["word", "name"],
        exerciseBindings: [{ lessonId: "lesson-one", exerciseId: "check-one" }], contentStatus: "UNREVIEWED", packetHash: "leaked",
      }],
    })).toThrow(/unsupported learner-facing fields/u);
  });
});
