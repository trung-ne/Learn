import { describe, expect, it } from "vitest";
import { buildVocabularySnapshot } from "../../scripts/build-vocabulary-snapshot.mjs";

describe("vocabulary snapshot builder", () => {
  it("rebuilds the declared learner-facing inventory without source metadata", async () => {
    const snapshot = await buildVocabularySnapshot();

    expect(snapshot).toMatchObject({ schemaVersion: "1.0", inventoryVersion: "2026-10-a1-unit-01" });
    expect(snapshot.senses).toHaveLength(20);
    expect(snapshot.senses[0]).not.toHaveProperty("packetSha256");
    expect(snapshot.senses[0]).not.toHaveProperty("sourceTargetId");
    expect(snapshot.senses[0]).not.toHaveProperty("provenance");
  });
});
