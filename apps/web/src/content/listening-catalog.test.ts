import { describe, expect, it } from "vitest";
import { getListeningSessions, listeningSnapshot, validateListeningSnapshot } from "@/content/listening-catalog";

describe("Listening Lab catalog", () => {
  it("exposes only the checked no-authorized-media sentinel", () => {
    expect(listeningSnapshot.availability).toBe("NO_AUTHORIZED_MEDIA");
    expect(getListeningSessions("en")).toEqual([]);
  });

  it("rejects unknown fields and sessions in the no-media state", () => {
    expect(() => validateListeningSnapshot({ ...listeningSnapshot, sourceUrl: "https://example.invalid" })).toThrow(/unsupported/i);
    expect(() => validateListeningSnapshot({ ...listeningSnapshot, sessions: [{ id: "unsafe" }] })).toThrow(/availability/i);
  });
});
