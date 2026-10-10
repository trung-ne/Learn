import { describe, expect, it } from "vitest";
import {
  getGrammarTargetIdsForExercise,
  getGrammarTargets,
  grammarSnapshot,
  validateGrammarSnapshot,
} from "@/content/grammar-catalog";

describe("grammar catalog", () => {
  it("exposes only the explicit English target bindings", () => {
    const target = grammarSnapshot.targets[0]!;
    const binding = target.exerciseBindings[0]!;

    expect(getGrammarTargets("en")).toHaveLength(20);
    expect(getGrammarTargets("de")).toEqual([]);
    expect(getGrammarTargetIdsForExercise("en", binding.lessonId, binding.exerciseId)).toContain(target.id);
    expect(getGrammarTargetIdsForExercise("de", binding.lessonId, binding.exerciseId)).toEqual([]);
  });

  it("rejects source metadata and broken prerequisite references", () => {
    const leaked = structuredClone(grammarSnapshot) as { targets: Array<Record<string, unknown>> };
    leaked.targets[0]!.sourceTargetId = "a1t_u01_personal_origin";
    expect(() => validateGrammarSnapshot(leaked)).toThrow(/unsupported learner-facing fields/i);

    const broken = structuredClone(grammarSnapshot) as { targets: Array<Record<string, unknown>> };
    broken.targets[0]!.prerequisiteIds = ["grammar-en-missing"];
    expect(() => validateGrammarSnapshot(broken)).toThrow(/unresolved prerequisite/i);
  });
});
