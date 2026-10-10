import { describe, expect, it } from "vitest";
import {
  getDictionaryEntry,
  getDictionaryRelations,
  searchDictionaryEntries,
} from "@/content/dictionary-catalog";

describe("dictionary catalog", () => {
  it("finds the explicit take family through supplied searchable fields", () => {
    expect(searchDictionaryEntries("en", "take")).toHaveLength(9);
    expect(searchDictionaryEntries("en", "trách nhiệm").map((entry) => entry.id)).toEqual(["dict-en-take-003"]);
  });

  it("returns only explicit stable relationship records", () => {
    const entry = getDictionaryEntry("dict-en-take-001");
    expect(entry).toBeDefined();
    if (!entry) return;
    expect(getDictionaryRelations(entry, "senseIds").map((item) => item.senseNumber)).toEqual([1, 2, 3, 4]);
    expect(getDictionaryRelations(entry, "phrasalVerbIds").map((item) => item.headword)).toEqual(["take off", "take over", "take up"]);
    expect(getDictionaryRelations(entry, "wordFamilyIds").map((item) => item.headword)).toEqual(["take", "taken", "taking"]);
  });
});
