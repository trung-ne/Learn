import { describe, expect, it } from "vitest";
import { localDiagnosticExport, parseLocalDiagnostics, recordLocalDiagnostic } from "@/lib/local-diagnostics";

class MemoryStorage {
  private readonly values = new Map<string, string>();
  getItem(key: string) { return this.values.get(key) ?? null; }
  setItem(key: string, value: string) { this.values.set(key, value); }
}

describe("local diagnostics", () => {
  it("keeps only sanitized route facts in a bounded local log", () => {
    const storage = new MemoryStorage();
    expect(recordLocalDiagnostic({ category: "render", occurredAt: "2026-10-10T00:00:00.000Z", buildId: "static", pathname: "/learn/en/A1/" }, storage)).toBe(true);
    expect(localDiagnosticExport(storage)).toEqual({ version: 1, records: [{ category: "render", occurredAt: "2026-10-10T00:00:00.000Z", buildId: "static", pathname: "/learn/en/A1/" }] });
    expect(recordLocalDiagnostic({ category: "render", occurredAt: "2026-10-10T00:00:00.000Z", buildId: "static", pathname: "/learn/?secret=value" }, storage)).toBe(false);
  });

  it("caps the local diagnostic buffer at twenty records", () => {
    const storage = new MemoryStorage();
    for (let index = 0; index < 21; index += 1) {
      expect(recordLocalDiagnostic({ category: "offline", occurredAt: `2026-10-10T00:00:${String(index).padStart(2, "0")}.000Z`, buildId: "static", pathname: "/offline/" }, storage)).toBe(true);
    }
    const records = localDiagnosticExport(storage).records;
    expect(records).toHaveLength(20);
    expect(records[0]?.occurredAt).toBe("2026-10-10T00:00:01.000Z");
  });

  it("rejects malformed local diagnostic records", () => {
    expect(parseLocalDiagnostics(JSON.stringify({ version: 1, records: [{ category: "render", occurredAt: "bad", buildId: "static", pathname: "/" }] }))).toEqual({ version: 1, records: [] });
  });
});
