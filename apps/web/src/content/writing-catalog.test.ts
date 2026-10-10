import { describe, expect, it } from "vitest";
import {
  getWritingBands,
  getWritingProtocolForLesson,
  getWritingProtocols,
  getWritingTiers,
  validateWritingSnapshot,
  writingSnapshot,
} from "@/content/writing-catalog";

describe("writing catalog", () => {
  it("exposes the closed English A1-C2 supplied inventory", () => {
    expect(getWritingProtocols()).toHaveLength(300);
    expect(getWritingBands()).toEqual(["A1", "A2", "B1", "B2", "C1", "C2"]);
    expect(getWritingTiers("A1")).toEqual(["A1.1", "A1.2"]);
    expect(getWritingProtocols({ band: "C2" })).toHaveLength(50);
    const protocol = writingSnapshot.protocols[0]!;
    expect(getWritingProtocolForLesson(protocol.lessonId)).toEqual(protocol);
    expect(protocol.feedbackBoundary).toBe("FEEDBACK_ONLY_NO_REPLACEMENT");
  });

  it("rejects evaluator leakage, invalid boundaries, and broken lesson bindings", () => {
    const leaked = structuredClone(writingSnapshot) as unknown as { protocols: Array<Record<string, unknown>> };
    leaked.protocols[0]!.provider = "example";
    expect(() => validateWritingSnapshot(leaked)).toThrow(/unsupported learner-facing fields/i);

    const boundary = structuredClone(writingSnapshot) as unknown as { protocols: Array<Record<string, unknown>> };
    boundary.protocols[0]!.feedbackBoundary = "ALLOW_REPLACEMENT";
    expect(() => validateWritingSnapshot(boundary)).toThrow(/invalid protocol/i);

    const broken = structuredClone(writingSnapshot) as unknown as { protocols: Array<Record<string, unknown>> };
    broken.protocols[0]!.lessonId = "missing-lesson";
    expect(() => validateWritingSnapshot(broken)).toThrow(/does not resolve/i);
  });
});
