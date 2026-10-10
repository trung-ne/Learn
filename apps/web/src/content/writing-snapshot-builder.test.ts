import { describe, expect, it } from "vitest";
import { buildWritingSnapshot } from "../../../scripts/build-writing-snapshot.mjs";

describe("writing snapshot builder", () => {
  it("builds a deterministic closed English 300-protocol inventory", async () => {
    const first = await buildWritingSnapshot();
    const second = await buildWritingSnapshot();
    expect(second).toEqual(first);
    expect(first.protocols).toHaveLength(300);
    expect(new Set(first.protocols.map((protocol) => protocol.id)).size).toBe(300);
    expect(new Set(first.protocols.map((protocol) => protocol.lessonId)).size).toBe(300);
    for (const band of ["A1", "A2", "B1", "B2", "C1", "C2"]) {
      expect(first.protocols.filter((protocol) => protocol.band === band)).toHaveLength(50);
    }
    expect(first.protocols.every((protocol) => protocol.language === "en" && protocol.feedbackBoundary === "FEEDBACK_ONLY_NO_REPLACEMENT" && protocol.contentStatus === "UNREVIEWED")).toBe(true);
    expect(Object.keys(first.protocols[0]!).sort()).toEqual([
      "band", "constraints", "contentStatus", "feedbackBoundary", "goal", "id", "instruction", "language",
      "lessonId", "tier", "title", "topic", "unitId",
    ]);
  });
});
