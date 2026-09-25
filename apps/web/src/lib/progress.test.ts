import { describe, expect, it } from "vitest";
import {
  emptyProgress,
  loadProgress,
  parseProgress,
  progressKey,
  resetProgress,
  saveProgress,
  updateLessonProgress,
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

describe("language-scoped local progress", () => {
  it("keeps English and German state in separate keys", () => {
    const storage = memoryStorage();
    const english = updateLessonProgress(emptyProgress("en"), "m16a1-v1-a1-u01-l01", { completed: true });
    expect(saveProgress(english, storage)).toBe(true);
    expect(loadProgress("en", storage).lessons["m16a1-v1-a1-u01-l01"]?.completed).toBe(true);
    expect(loadProgress("de", storage).lessons).toEqual({});
    expect(progressKey("en")).not.toBe(progressKey("de"));
  });

  it("discards malformed, cross-language, and unsupported stored records", () => {
    expect(parseProgress("not json", "en")).toEqual(emptyProgress("en"));
    expect(parseProgress(JSON.stringify({ version: 1, language: "de", lessons: {} }), "en")).toEqual(emptyProgress("en"));
    expect(parseProgress(JSON.stringify({
      version: 1,
      language: "en",
      lessons: { "../bad": { completed: true, attempts: {}, protocols: {}, drafts: {} } },
    }), "en")).toEqual(emptyProgress("en"));
  });

  it("resets only the selected language", () => {
    const storage = memoryStorage();
    saveProgress(updateLessonProgress(emptyProgress("en"), "m16a1-v1-a1-u01-l01", { completed: true }), storage);
    saveProgress(updateLessonProgress(emptyProgress("de"), "de-a1-v1-u01-l01", { completed: true }), storage);
    expect(resetProgress("en", storage)).toBe(true);
    expect(loadProgress("en", storage).lessons).toEqual({});
    expect(loadProgress("de", storage).lessons["de-a1-v1-u01-l01"]?.completed).toBe(true);
  });
});
