import { describe, expect, it } from "vitest";
import {
  addUniqueIdentity,
  assertBytesHash,
  assertSafeInventoryPaths,
  assertUnreviewed,
  buildSnapshot,
} from "../../scripts/build-content-snapshot.mjs";

describe("content snapshot builder", () => {
  it("rebuilds the declared closed 310-packet inventory", async () => {
    const snapshot = await buildSnapshot();
    expect(snapshot.lessons).toHaveLength(310);
    expect(snapshot.sourceManifests).toHaveLength(7);
    expect(snapshot.sourceManifests.map((source) => source.packetCount)).toEqual([50, 50, 50, 50, 50, 50, 10]);
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
