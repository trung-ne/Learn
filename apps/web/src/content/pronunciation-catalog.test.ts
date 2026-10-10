import { describe, expect, it } from "vitest";
import {
  getPronunciationProtocolForLesson,
  getPronunciationProtocols,
  pronunciationSnapshot,
  validatePronunciationSnapshot,
} from "@/content/pronunciation-catalog";

describe("pronunciation catalog", () => {
  it("exposes lesson-bound protocols without inventing an assessment", () => {
    const protocol = pronunciationSnapshot.protocols[0]!;

    expect(getPronunciationProtocols("en")).toHaveLength(300);
    expect(getPronunciationProtocols("de")).toHaveLength(10);
    expect(getPronunciationProtocolForLesson(protocol.language, protocol.lessonId)).toEqual(protocol);
    expect(protocol.assessmentAvailability).toBe("NOT_ASSESSED");
  });

  it("rejects score fields and broken lesson bindings", () => {
    const leaked = structuredClone(pronunciationSnapshot) as unknown as { protocols: Array<Record<string, unknown>> };
    leaked.protocols[0]!.score = 82;
    expect(() => validatePronunciationSnapshot(leaked)).toThrow(/unsupported learner-facing fields/i);

    const broken = structuredClone(pronunciationSnapshot) as unknown as { protocols: Array<Record<string, unknown>> };
    broken.protocols[0]!.lessonId = "missing-lesson";
    expect(() => validatePronunciationSnapshot(broken)).toThrow(/does not resolve/i);
  });
});
