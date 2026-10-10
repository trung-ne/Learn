import { describe, expect, it } from "vitest";
import { buildReadingSnapshot } from "../../scripts/build-reading-snapshot.mjs";

describe("reading snapshot builder", () => {
  it("creates the deterministic approved English-only reading projection", async () => {
    const first = await buildReadingSnapshot();
    const second = await buildReadingSnapshot();

    expect(first).toEqual(second);
    expect(first.readers).toHaveLength(212);
    expect(first.readers.filter((reader) => reader.mode === "GRADED_OBJECTIVE")).toHaveLength(112);
    expect(first.readers.filter((reader) => reader.mode === "SUPPLIED_TEXT")).toHaveLength(100);
    expect(new Set(first.readers.map((reader) => reader.band))).toEqual(new Set(["A1", "A2", "B1", "C1", "C2"]));
    expect(first.readers.every((reader) => reader.contentStatus === "UNREVIEWED")).toBe(true);
  });

  it("omits source authority and authored mapping surfaces from browser data", async () => {
    const serialized = JSON.stringify(await buildReadingSnapshot());

    expect(serialized).not.toContain("packet_sha256");
    expect(serialized).not.toContain("packetSha256");
    expect(serialized).not.toContain("source_kind");
    expect(serialized).not.toContain("sourceId");
    expect(serialized).not.toContain("source_id");
    expect(serialized).not.toContain("surface");
    expect(serialized).not.toContain("path");
    expect(serialized).not.toContain("B2.1");
    expect(serialized).not.toContain("B2.2");
  });
});
