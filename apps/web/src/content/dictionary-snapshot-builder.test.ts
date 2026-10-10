import { describe, expect, it } from "vitest";
import { buildDictionarySnapshot } from "../../scripts/build-dictionary-snapshot.mjs";

describe("dictionary snapshot builder", () => {
  it("rebuilds the bounded original-authored take family without source governance fields", async () => {
    const snapshot = await buildDictionarySnapshot();
    expect(snapshot).toMatchObject({ schemaVersion: "1.0", inventoryVersion: "2026-10-take-family-01" });
    expect(snapshot.entries).toHaveLength(9);
    expect(snapshot.entries.find((entry) => entry.id === "dict-en-take-001")).toMatchObject({
      headword: "take",
      senseNumber: 1,
      contentStatus: "UNREVIEWED",
    });
    expect(snapshot.entries[0]).not.toHaveProperty("authorship");
  });
});
