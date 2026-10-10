import { describe, expect, it } from "vitest";
import { buildPronunciationSnapshot } from "../../scripts/build-pronunciation-snapshot.mjs";

describe("pronunciation snapshot builder", () => {
  it("creates a deterministic, learner-safe protocol projection", async () => {
    const first = await buildPronunciationSnapshot();
    const second = await buildPronunciationSnapshot();

    expect(first).toEqual(second);
    expect(first.protocols).toHaveLength(310);
    expect(first.protocols.every((protocol) => protocol.assessmentAvailability === "NOT_ASSESSED" && protocol.contentStatus === "UNREVIEWED")).toBe(true);
    expect(first.protocols.filter((protocol) => protocol.language === "en")).toHaveLength(300);
    expect(first.protocols.filter((protocol) => protocol.language === "de")).toHaveLength(10);
    expect(JSON.stringify(first)).not.toContain("packet_sha256");
    expect(JSON.stringify(first)).not.toContain("target_ids");
    expect(JSON.stringify(first)).not.toContain("source_record_id");
  });
});
