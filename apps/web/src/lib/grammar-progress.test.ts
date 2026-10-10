import { describe, expect, it } from "vitest";
import {
  emptyGrammarProgress,
  grammarProgressKey,
  parseGrammarProgress,
  recordGrammarTargetResult,
  selectGrammarReviewQueue,
} from "@/lib/grammar-progress";

const scope = { learnerId: "local-learner-001", language: "en" as const };
const targetId = "grammar-en-05b276d38d616598fff9";
const start = "2026-10-04T10:00:00.000Z";

function recordCorrectly(times: number) {
  let progress = emptyGrammarProgress(scope, "grammar-test");
  for (let index = 0; index < times; index += 1) {
    progress = recordGrammarTargetResult(progress, targetId, true, `2026-10-${String(index + 4).padStart(2, "0")}T10:00:00.000Z`);
  }
  return progress;
}

describe("grammar progress", () => {
  it("isolates state and advances the local review ladder", () => {
    const first = recordGrammarTargetResult(emptyGrammarProgress(scope, "grammar-test"), targetId, true, start);
    expect(grammarProgressKey(scope)).toBe("english-master.grammar.v1.local-learner-001.en");
    expect(first.targets[targetId]).toMatchObject({ state: "reviewing", intervalIndex: 1, localScore: 100, nextReviewAt: "2026-10-05T10:00:00.000Z" });

    const reset = recordGrammarTargetResult(first, targetId, false, "2026-10-05T10:00:00.000Z");
    expect(reset.targets[targetId]).toMatchObject({ state: "practising", intervalIndex: 0, attempts: 2, correctAttempts: 1, incorrectOutcomes: 1, nextReviewAt: "2026-10-06T10:00:00.000Z" });
  });

  it("labels only the final scheduled stage as locally consolidated", () => {
    const progress = recordCorrectly(6);
    expect(progress.targets[targetId]).toMatchObject({ state: "locally_consolidated", intervalIndex: 5, attempts: 6 });
  });

  it("rejects malformed or stale stored state and selects only due known targets", () => {
    expect(parseGrammarProgress("{", scope, "grammar-test")).toEqual(emptyGrammarProgress(scope, "grammar-test"));
    const stale = { ...emptyGrammarProgress(scope, "grammar-old"), targets: {} };
    expect(parseGrammarProgress(JSON.stringify(stale), scope, "grammar-test")).toEqual(emptyGrammarProgress(scope, "grammar-test"));
    const progress = recordGrammarTargetResult(emptyGrammarProgress(scope, "grammar-test"), targetId, false, start);
    expect(selectGrammarReviewQueue(progress, [{ targetId, introductionOrder: 0 }], "2026-10-05T10:00:00.000Z")).toEqual([]);
    expect(selectGrammarReviewQueue(progress, [{ targetId, introductionOrder: 0 }], "2026-10-06T10:00:00.000Z")).toEqual([targetId]);
  });
});
