import { describe, expect, it } from "vitest";
import {
  applyLocalDataBackup,
  clearEnglishMasterLocalData,
  createLocalDataBackup,
  inspectLocalDataBackup,
} from "@/lib/local-data-backup";

class MemoryStorage implements Storage {
  private readonly values = new Map<string, string>();
  get length() { return this.values.size; }
  clear() { this.values.clear(); }
  getItem(key: string) { return this.values.get(key) ?? null; }
  key(index: number) { return [...this.values.keys()][index] ?? null; }
  removeItem(key: string) { this.values.delete(key); }
  setItem(key: string, value: string) { this.values.set(key, value); }
}

describe("local data backup", () => {
  it("exports only English Master records and restores a checked envelope", () => {
    const source = new MemoryStorage();
    source.setItem("english-master.progress.v2.local-learner-001.en.A1", JSON.stringify({ version: 2 }));
    source.setItem("unrelated", JSON.stringify({ preserve: true }));
    const backup = createLocalDataBackup(source);
    expect(Object.keys(backup.records)).toEqual(["english-master.progress.v2.local-learner-001.en.A1"]);

    const target = new MemoryStorage();
    target.setItem("english-master.review.v1.local-learner-001.en.A1", JSON.stringify({ version: 1 }));
    target.setItem("unrelated", JSON.stringify({ preserve: true }));
    expect(applyLocalDataBackup(backup, target)).toBe(true);
    expect(target.getItem("english-master.progress.v2.local-learner-001.en.A1")).toBe(JSON.stringify({ version: 2 }));
    expect(target.getItem("english-master.review.v1.local-learner-001.en.A1")).toBeNull();
    expect(target.getItem("unrelated")).toBe(JSON.stringify({ preserve: true }));
  });

  it("rejects foreign, malformed, and non-object backup records before any restore", () => {
    expect(inspectLocalDataBackup(JSON.stringify({ version: 1, createdAt: "2026-10-10T00:00:00.000Z", records: { foreign: "{}" } })).valid).toBe(false);
    expect(inspectLocalDataBackup(JSON.stringify({ version: 1, createdAt: "2026-10-10T00:00:00.000Z", records: { "english-master.bad": "not json" } })).valid).toBe(false);
    expect(inspectLocalDataBackup(JSON.stringify({ version: 1, createdAt: "2026-10-10T00:00:00.000Z", records: { "english-master.bad": "1" } })).valid).toBe(false);

    const storage = new MemoryStorage();
    storage.setItem("unrelated", "keep");
    expect(applyLocalDataBackup({ version: 1, createdAt: "2026-10-10T00:00:00.000Z", records: { "english-master.bad": "{}" } } as unknown as ReturnType<typeof createLocalDataBackup>, storage)).toBe(false);
    expect(storage.getItem("unrelated")).toBe("keep");
  });

  it("clears only application records", () => {
    const storage = new MemoryStorage();
    storage.setItem("english-master.review.v1.local-learner-001.en.A1", JSON.stringify({ version: 1 }));
    storage.setItem("unrelated", "keep");
    expect(clearEnglishMasterLocalData(storage)).toBe(true);
    expect(storage.getItem("english-master.review.v1.local-learner-001.en.A1")).toBeNull();
    expect(storage.getItem("unrelated")).toBe("keep");
  });
});
