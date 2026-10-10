import { describe, expect, it } from "vitest";
import { buildListeningSnapshot } from "../../scripts/build-listening-snapshot.mjs";

describe("Listening snapshot builder", () => {
  it("builds the deterministic no-authorized-media sentinel", async () => {
    const snapshot = await buildListeningSnapshot();
    expect(snapshot).toMatchObject({ schemaVersion: "1.0", availability: "NO_AUTHORIZED_MEDIA", sessions: [] });
    expect(snapshot.inventoryVersion).toMatch(/^listening-[a-f0-9]{16}$/u);
  });
});
