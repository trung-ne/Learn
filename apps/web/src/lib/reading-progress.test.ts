import { describe, expect, it } from "vitest";
import {
  emptyReadingProgress,
  parseReadingProgress,
  readingProgressKey,
  toggleReadingBookmark,
} from "@/lib/reading-progress";

const scope = { learnerId: "local-learner-001", language: "en" as const };
const version = "reading-inventory-v1";
const now = "2026-10-06T08:00:00.000Z";

describe("reading progress", () => {
  it("isolates local bookmarks by learner and language scope", () => {
    expect(readingProgressKey(scope)).toBe("english-master.reading.v1.local-learner-001.en");
    const progress = toggleReadingBookmark(emptyReadingProgress(scope, version), "reading-a1-001", now);
    expect(progress.bookmarks["reading-a1-001"]?.firstOpenedAt).toBe(now);
    expect(toggleReadingBookmark(progress, "reading-a1-001", now).bookmarks).toEqual({});
  });

  it("fails closed for malformed and stale inventory state", () => {
    const serialized = JSON.stringify({ version: 1, ...scope, inventoryVersion: "old", bookmarks: {} });
    expect(parseReadingProgress(serialized, scope, version)).toEqual(emptyReadingProgress(scope, version));
    expect(parseReadingProgress("not json", scope, version)).toEqual(emptyReadingProgress(scope, version));
  });
});
