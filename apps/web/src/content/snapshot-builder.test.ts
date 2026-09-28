import { describe, expect, it } from "vitest";
import {
  addUniqueIdentity,
  adaptGermanPacket,
  assertBytesHash,
  assertSafeInventoryPaths,
  assertUnreviewed,
  buildSnapshot,
  projectExercise,
  projectPracticeProtocol,
} from "../../scripts/build-content-snapshot.mjs";

describe("content snapshot builder", () => {
  it("rebuilds the declared closed 310-packet inventory", async () => {
    const snapshot = await buildSnapshot();
    expect(snapshot.lessons).toHaveLength(310);
    expect(snapshot.languages).toEqual([
      { code: "en", name: "English", lessonCount: 300, bands: ["A1", "A2", "B1", "B2", "C1", "C2"] },
      { code: "de", name: "German", lessonCount: 10, bands: ["A1"] },
    ]);
    expect(snapshot.lessons[0]).not.toHaveProperty("packetSha256");
    expect(snapshot.lessons[0]).not.toHaveProperty("provenance");
    expect(snapshot.lessons[0]).not.toHaveProperty("contentStatus");
  });

  it("projects only the supplied Vietnamese A1 v2 tips", async () => {
    const snapshot = await buildSnapshot();
    const tips = snapshot.lessons
      .flatMap((lesson) => lesson.sections ?? [])
      .filter((section) => section.vietnameseTip);

    expect(tips).toHaveLength(50);
    expect(tips[0]).toMatchObject({
      body: "Use this lesson language to communicate a simple real-life meaning: Use Hello, Hi, and Goodbye in short exchanges. Model: “Hello, I am Lan.” Notice the important words and the word order.",
      vietnameseTip:
        "hãy hiểu ý của cả câu trước, rồi nói theo cụm ngắn; không cần dịch từng từ.",
    });
    expect(tips.some((section) => section.body.includes("Mẹo tiếng Việt:"))).toBe(false);
    expect(
      snapshot.lessons
        .filter((lesson) => lesson.language !== "en" || lesson.band !== "A1")
        .flatMap((lesson) => lesson.sections ?? [])
        .some((section) => section.vietnameseTip),
    ).toBe(false);
  });

  it("projects only learner-facing practice fields", async () => {
    const snapshot = await buildSnapshot();
    const listening = snapshot.lessons
      .flatMap((lesson) =>
        Object.values(
          (lesson.practice ?? {}) as Record<
            string,
            { readonly instruction?: string; readonly transcript?: string }
          >,
        ),
      )
      .find((protocol) => protocol.instruction && protocol.transcript);

    expect(listening).toMatchObject({ instruction: expect.any(String), transcript: expect.any(String) });
    expect(listening).not.toHaveProperty("target_ids");
    expect(listening).not.toHaveProperty("media_required");
    expect(listening).not.toHaveProperty("modality");
    expect(listening).not.toHaveProperty("situation");
    expect(listening).not.toHaveProperty("learner_role");
    expect(listening).not.toHaveProperty("examples");
    const exercise = snapshot.lessons.flatMap((lesson) => lesson.exercises ?? [])[0];
    expect(exercise).not.toHaveProperty("target_ids");
    expect(exercise).not.toHaveProperty("media_required");
  });

  it("projects only learner-facing exercise and practice fields", () => {
    expect(projectExercise({
      id: "choice-1",
      type: "multiple_choice",
      prompt: "Choose.",
      options: ["A", "B"],
      correct_answer: "A",
      target_ids: ["private-target"],
      media_required: false,
    }, "fixture")).toEqual({
      id: "choice-1",
      type: "multiple_choice",
      prompt: "Choose.",
      options: ["A", "B"],
      correct_answer: "A",
    });
    expect(() => projectExercise({ id: "choice-1", type: "multiple_choice", prompt: "Choose.", options: ["A", "B"] }, "fixture")).toThrow(/answer data/);
    expect(() => projectExercise({ id: "order-1", type: "ordering", prompt: "Order.", items: ["A", "B"], correct_order: ["A", "C"] }, "fixture")).toThrow(/ordering items/);
    expect(() => projectPracticeProtocol({ instruction: "Practise.", checklist: ["Clear", 2] }, "fixture")).toThrow(/checklist\[1\]/);
    expect(() => adaptGermanPacket({
      language_code: "de",
      prompts: [
        { modality: "listening", instruction: "Listen." },
        { modality: "listening", instruction: "Listen again." },
      ],
    }, {})).toThrow(/duplicate listening practice/);
  });

  it("rejects unsafe or drifting source facts", () => {
    expect(() => assertUnreviewed("APPROVED", "fixture")).toThrow(/status drifted/);
    expect(() => assertSafeInventoryPaths([{ path: "../packet.json" }], "fixture")).toThrow(/unsafe/);
    expect(() => assertBytesHash(Buffer.from("content"), "0".repeat(64), "fixture")).toThrow(/hash mismatch/);
    const identities = new Set<string>();
    addUniqueIdentity(identities, "en", "lesson-1");
    expect(() => addUniqueIdentity(identities, "en", "lesson-1")).toThrow(/duplicate/);
  });
});
