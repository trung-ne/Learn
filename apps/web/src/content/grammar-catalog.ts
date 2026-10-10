import rawSnapshot from "./generated/grammar-snapshot.json";
import type { LanguageCode } from "./types";
import type { GrammarSnapshot, GrammarTarget } from "./grammar-types";

const bands = new Set(["A1", "A2", "B1", "B2", "C1", "C2"]);

function isRecord(value: unknown): value is Record<string, unknown> {
  return Boolean(value) && typeof value === "object" && !Array.isArray(value);
}

function isNonEmptyString(value: unknown): value is string {
  return typeof value === "string" && value.trim().length > 0;
}

function isSafeId(value: unknown): value is string {
  return typeof value === "string" && /^[a-z][a-z0-9-]*$/u.test(value);
}

function hasOnlyFields(value: Record<string, unknown>, allowed: readonly string[], label: string): void {
  if (Object.keys(value).some((field) => !allowed.includes(field))) {
    throw new Error(`${label} contains unsupported learner-facing fields.`);
  }
}

function validateBinding(value: unknown): void {
  if (!isRecord(value)) throw new Error("Grammar snapshot contains an invalid exercise binding.");
  hasOnlyFields(value, ["lessonId", "exerciseId"], "Grammar exercise binding");
  if (!isSafeId(value.lessonId) || !isSafeId(value.exerciseId)) {
    throw new Error("Grammar snapshot contains an invalid exercise binding.");
  }
}

function validateTarget(value: unknown): void {
  if (!isRecord(value)) throw new Error("Grammar snapshot contains an invalid grammar target.");
  hasOnlyFields(value, [
    "id", "language", "band", "tier", "title", "topic", "introductionLessonId", "prerequisiteIds", "exerciseBindings", "contentStatus",
  ], "Grammar target");
  if (!isSafeId(value.id) || value.language !== "en" || !bands.has(value.band as string) ||
    !isNonEmptyString(value.tier) || !new RegExp(`^${value.band}\\.[12]$`, "u").test(value.tier) ||
    !isNonEmptyString(value.title) || !isNonEmptyString(value.topic) || !isSafeId(value.introductionLessonId) ||
    !Array.isArray(value.prerequisiteIds) || !value.prerequisiteIds.every(isSafeId) ||
    !Array.isArray(value.exerciseBindings) || !value.exerciseBindings.length || value.contentStatus !== "UNREVIEWED") {
    throw new Error("Grammar snapshot contains an invalid grammar target.");
  }
  value.exerciseBindings.forEach(validateBinding);
  const bindingKeys = value.exerciseBindings.map((binding) => `${(binding as Record<string, unknown>).lessonId}\u0000${(binding as Record<string, unknown>).exerciseId}`);
  if (new Set(value.prerequisiteIds).size !== value.prerequisiteIds.length || new Set(bindingKeys).size !== bindingKeys.length) {
    throw new Error("Grammar snapshot contains duplicate grammar relationships.");
  }
}

function validateAcyclic(targets: readonly GrammarTarget[]): void {
  const targetIds = new Set(targets.map((target) => target.id));
  for (const target of targets) {
    if (target.prerequisiteIds.some((id) => !targetIds.has(id))) {
      throw new Error("Grammar snapshot contains an unresolved prerequisite.");
    }
  }
  const visiting = new Set<string>();
  const visited = new Set<string>();
  const visit = (id: string): void => {
    if (visiting.has(id)) throw new Error("Grammar snapshot contains a prerequisite cycle.");
    if (visited.has(id)) return;
    visiting.add(id);
    const target = targets.find((candidate) => candidate.id === id);
    if (!target) throw new Error("Grammar snapshot contains an unresolved prerequisite.");
    target.prerequisiteIds.forEach(visit);
    visiting.delete(id);
    visited.add(id);
  };
  targets.forEach((target) => visit(target.id));
}

export function validateGrammarSnapshot(value: unknown): asserts value is GrammarSnapshot {
  if (!isRecord(value) || value.schemaVersion !== "1.0" || !isNonEmptyString(value.inventoryVersion) || !Array.isArray(value.targets)) {
    throw new Error("Unsupported grammar snapshot metadata.");
  }
  hasOnlyFields(value, ["schemaVersion", "inventoryVersion", "targets"], "Grammar snapshot");
  const ids = new Set<string>();
  for (const target of value.targets) {
    validateTarget(target);
    const item = target as GrammarTarget;
    if (ids.has(item.id)) throw new Error("Grammar snapshot contains duplicate target IDs.");
    ids.add(item.id);
  }
  validateAcyclic(value.targets as readonly GrammarTarget[]);
}

const candidateSnapshot: unknown = rawSnapshot;
validateGrammarSnapshot(candidateSnapshot);
export const grammarSnapshot = candidateSnapshot;

export function getGrammarTargets(language: LanguageCode): readonly GrammarTarget[] {
  return language === "en" ? grammarSnapshot.targets : [];
}

export function getGrammarTarget(targetId: string): GrammarTarget | undefined {
  return grammarSnapshot.targets.find((target) => target.id === targetId);
}

export function getGrammarTargetIdsForExercise(
  language: LanguageCode,
  lessonId: string,
  exerciseId: string,
): readonly string[] {
  return getGrammarTargets(language)
    .filter((target) => target.exerciseBindings.some((binding) =>
      binding.lessonId === lessonId && binding.exerciseId === exerciseId,
    ))
    .map((target) => target.id);
}
