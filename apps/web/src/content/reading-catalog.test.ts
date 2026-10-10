import { describe, expect, it } from "vitest";
import {
  getReadingBands,
  getReadingModes,
  getReadingReader,
  getReadingReaders,
  getReadingTiers,
  getReadingTopics,
  readingSnapshot,
  validateReadingSnapshot,
} from "@/content/reading-catalog";

describe("reading catalog", () => {
  it("supports stable UI selectors over the approved inventory", () => {
    expect(getReadingBands()).toEqual(["A1", "A2", "B1", "C1", "C2"]);
    expect(getReadingModes()).toEqual(["GRADED_OBJECTIVE", "SUPPLIED_TEXT"]);
    expect(getReadingReaders({ band: "A1", mode: "GRADED_OBJECTIVE" })).toHaveLength(12);
    expect(getReadingReaders({ band: "C1", mode: "SUPPLIED_TEXT" })).toHaveLength(50);
    expect(getReadingReaders({ band: "B2" })).toEqual([]);
    expect(getReadingTiers("A1")).toEqual(["A1.1", "A1.2"]);
    expect(getReadingTopics({ band: "C2" }).length).toBeGreaterThan(0);
    expect(getReadingReader(readingSnapshot.readers[0]!.id)).toEqual(readingSnapshot.readers[0]);
  });

  it("rejects unknown fields, invalid mode contracts, and invalid ranges", () => {
    const leaked = structuredClone(readingSnapshot) as { readers: Array<Record<string, unknown>> };
    leaked.readers[0]!.packetSha256 = "a".repeat(64);
    expect(() => validateReadingSnapshot(leaked)).toThrow(/unsupported learner-facing fields/i);

    const modeDrift = structuredClone(readingSnapshot) as { readers: Array<Record<string, unknown>> };
    const graded = modeDrift.readers.find((reader) => reader.mode === "GRADED_OBJECTIVE")!;
    delete graded.questions;
    expect(() => validateReadingSnapshot(modeDrift)).toThrow(/must contain supplied objective questions/i);

    const badRange = structuredClone(readingSnapshot) as { readers: Array<Record<string, unknown>> };
    const mapped = badRange.readers.find((reader) => Array.isArray(reader.wordSenseRanges))!;
    mapped.wordSenseRanges = [{ start: 0, end: 999999, senseId: "vocab-en-name-001" }];
    expect(() => validateReadingSnapshot(badRange)).toThrow(/invalid WordSense range/i);
  });
});
