import { describe, expect, it } from "vitest";
import { buildGrammarSnapshot } from "../../scripts/build-grammar-snapshot.mjs";

describe("grammar snapshot builder", () => {
  it("creates a deterministic learner-safe English grammar projection", async () => {
    const first = await buildGrammarSnapshot();
    const second = await buildGrammarSnapshot();

    expect(first).toEqual(second);
    expect(first.targets).toHaveLength(20);
    expect(first.targets.every((target) => target.language === "en" && target.contentStatus === "UNREVIEWED")).toBe(true);
    expect(first.targets.every((target) => Array.isArray(target.exerciseBindings) && target.exerciseBindings.length > 0)).toBe(true);
    expect(JSON.stringify(first)).not.toContain("kg_");
    expect(JSON.stringify(first)).not.toContain("packetSha256");
    expect(JSON.stringify(first)).not.toContain("source_target_id");
  });
});
