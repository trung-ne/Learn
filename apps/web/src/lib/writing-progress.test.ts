import { describe, expect, it } from "vitest";
import {
  WRITING_DRAFT_LIMIT,
  emptyWritingProgress,
  forkWritingRevision,
  getLatestWritingAttempt,
  importLegacyWritingDraft,
  parseWritingProgress,
  saveWritingDraft,
  writingProgressKey,
} from "@/lib/writing-progress";

const scope = { learnerId: "local-learner-001", language: "en" as const };
const protocol = { id: "writing-en-1234567890abcdef", lessonId: "a1-u01-l01", band: "A1" as const };
const timestamp = "2026-10-07T10:00:00.000Z";

describe("writing progress", () => {
  it("isolates local writing state and preserves a linked learner revision", () => {
    expect(writingProgressKey(scope)).toBe("english-master.writing.v1.local-learner-001.en");
    const draft = saveWritingDraft(emptyWritingProgress(scope, "writing-test"), protocol, "First draft.", timestamp);
    const revision = forkWritingRevision(draft, getLatestWritingAttempt(draft, protocol.id)!.id, "2026-10-07T10:01:00.000Z");
    const latest = getLatestWritingAttempt(revision, protocol.id)!;
    expect(Object.keys(revision.attempts)).toHaveLength(2);
    expect(latest.status).toBe("REVISED");
    expect(latest.parentAttemptId).toBeDefined();
    expect(latest.draft).toBe("First draft.");
  });

  it("imports a legacy draft once and rejects malformed, stale, or oversized state", () => {
    const empty = emptyWritingProgress(scope, "writing-test");
    const imported = importLegacyWritingDraft(empty, protocol, "Existing lesson draft.", timestamp);
    expect(getLatestWritingAttempt(imported, protocol.id)?.draft).toBe("Existing lesson draft.");
    expect(importLegacyWritingDraft(imported, protocol, "Different legacy draft.", timestamp)).toEqual(imported);

    const serialized = JSON.stringify(imported);
    expect(parseWritingProgress(serialized, scope, "writing-test", [protocol])).toEqual(imported);
    expect(parseWritingProgress(serialized, scope, "writing-new", [protocol])).toBeUndefined();
    expect(parseWritingProgress(JSON.stringify({ ...imported, attempts: { bad: { draft: "x" } } }), scope, "writing-test", [protocol])).toBeUndefined();
    expect(saveWritingDraft(empty, protocol, "x".repeat(WRITING_DRAFT_LIMIT + 1), timestamp)).toEqual(empty);
  });
});
