import { describe, expect, it } from "vitest";
import {
  getSpeakingLanguages,
  getSpeakingProtocolForLesson,
  getSpeakingProtocols,
  speakingSnapshot,
  validateSpeakingSnapshot,
} from "@/content/speaking-catalog";

describe("speaking catalog", () => {
  it("exposes lesson-bound protocols with explicitly unavailable assessment dimensions", () => {
    const protocol = speakingSnapshot.protocols[0]!;

    expect(getSpeakingProtocols("en")).toHaveLength(300);
    expect(getSpeakingProtocols("de")).toHaveLength(10);
    expect(getSpeakingLanguages()).toEqual(["de", "en"]);
    expect(getSpeakingProtocolForLesson(protocol.language, protocol.lessonId)).toEqual(protocol);
    expect(Object.values(protocol.assessment).every((value) => value === "NOT_ASSESSED")).toBe(true);
  });

  it("rejects score fields, assessment drift, and broken lesson bindings", () => {
    const leaked = structuredClone(speakingSnapshot) as unknown as { protocols: Array<Record<string, unknown>> };
    leaked.protocols[0]!.score = 82;
    expect(() => validateSpeakingSnapshot(leaked)).toThrow(/unsupported learner-facing fields/i);

    const assessed = structuredClone(speakingSnapshot) as unknown as { protocols: Array<{ assessment: Record<string, unknown> }> };
    assessed.protocols[0]!.assessment.fluency = "GOOD";
    expect(() => validateSpeakingSnapshot(assessed)).toThrow(/assessment is invalid/i);

    const broken = structuredClone(speakingSnapshot) as unknown as { protocols: Array<Record<string, unknown>> };
    broken.protocols[0]!.lessonId = "missing-lesson";
    expect(() => validateSpeakingSnapshot(broken)).toThrow(/does not resolve/i);
  });
});
