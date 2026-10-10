import { describe, expect, it } from "vitest";
import { buildSpeakingSnapshot } from "../../scripts/build-speaking-snapshot.mjs";

const notAssessed = {
  overall: "NOT_ASSESSED",
  grammar: "NOT_ASSESSED",
  vocabulary: "NOT_ASSESSED",
  fluency: "NOT_ASSESSED",
  pronunciation: "NOT_ASSESSED",
  coherence: "NOT_ASSESSED",
  appropriacy: "NOT_ASSESSED",
};

describe("speaking snapshot builder", () => {
  it("creates a deterministic, learner-safe protocol projection", async () => {
    const first = await buildSpeakingSnapshot();
    const second = await buildSpeakingSnapshot();

    expect(first).toEqual(second);
    expect(first.protocols).toHaveLength(310);
    expect(first.protocols.every((protocol) => protocol.contentStatus === "UNREVIEWED" &&
      JSON.stringify(protocol.assessment) === JSON.stringify(notAssessed))).toBe(true);
    expect(first.protocols.filter((protocol) => protocol.language === "en")).toHaveLength(300);
    expect(first.protocols.filter((protocol) => protocol.language === "de")).toHaveLength(10);
    expect(first.protocols.filter((protocol) => protocol.language === "en").every((protocol) => protocol.goal && protocol.constraints && !protocol.checklist)).toBe(true);
    expect(first.protocols.filter((protocol) => protocol.language === "de").every((protocol) => protocol.checklist && !protocol.goal && !protocol.constraints)).toBe(true);
    for (const forbidden of ["packet_sha256", "target_ids", "source_record_id", "provenance", "provider", "feedback", "score"]) {
      expect(JSON.stringify(first)).not.toContain(`\"${forbidden}\"`);
    }
  });
});
