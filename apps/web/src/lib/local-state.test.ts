import { describe, expect, it } from "vitest";
import { isEnglishMasterStorageKey } from "@/lib/local-state";

describe("English Master local-storage key policy", () => {
  it("accepts only supported application storage keys", () => {
    expect(isEnglishMasterStorageKey("english-master.learner.v2.profile")).toBe(true);
    expect(isEnglishMasterStorageKey("english-master.progress.v2.local-learner-001.en.A1")).toBe(true);
    expect(isEnglishMasterStorageKey("english-master.tutor-preferences.v1.local-learner-001.de")).toBe(true);
    expect(isEnglishMasterStorageKey("english-master.assessment.v1.local-learner-001.en.assessment_38118701")).toBe(true);
  });

  it("rejects probes, unknown records, and malformed scope keys", () => {
    expect(isEnglishMasterStorageKey("english-master.storage-probe")).toBe(false);
    expect(isEnglishMasterStorageKey("english-master.bad")).toBe(false);
    expect(isEnglishMasterStorageKey("english-master.progress.v2.short.en.A1")).toBe(false);
    expect(isEnglishMasterStorageKey("english-master.progress.v2.local-learner-001.en.C3")).toBe(false);
  });
});
