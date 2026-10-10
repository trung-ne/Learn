import { describe, expect, it } from "vitest";
import {
  emptyListeningLabProgress,
  listeningLabProgressKey,
  parseListeningLabProgress,
  recordListeningLabStage,
} from "@/lib/listening-lab-progress";

const scope = { learnerId: "local-learner-001", language: "en" as const, course: "A1" as const };
const now = "2026-10-04T10:00:00.000Z";

describe("Listening Lab local progress", () => {
  it("isolates the browser-local state and accepts only ordered stage markers", () => {
    const empty = emptyListeningLabProgress(scope, "listening-test");
    expect(listeningLabProgressKey(scope)).toBe("english-master.listening-lab.v1.local-learner-001.en.A1");
    expect(recordListeningLabStage(empty, "listening-en-a1-001", "dictation_attempted", now)).toEqual(empty);
    const meaning = recordListeningLabStage(empty, "listening-en-a1-001", "meaning_attempted", now);
    expect(meaning.sessions["listening-en-a1-001"]).toMatchObject({ completedStages: ["meaning_attempted"], meaningAttempts: 1, dictationAttempts: 0 });
  });

  it("does not retain malformed or stale-inventory state", () => {
    expect(parseListeningLabProgress("{", scope, "listening-test")).toEqual(emptyListeningLabProgress(scope, "listening-test"));
    const stale = emptyListeningLabProgress(scope, "old-inventory");
    expect(parseListeningLabProgress(JSON.stringify(stale), scope, "listening-test")).toEqual(emptyListeningLabProgress(scope, "listening-test"));
  });
});
