import rawSnapshot from "./generated/assessment-snapshot.json";
import type {
  AssessmentAnswerContract,
  AssessmentItem,
  AssessmentItemType,
  AssessmentPackage,
  AssessmentSnapshot,
  AssessmentType,
} from "./assessment-types";
import { ASSESSMENT_RUN_ID } from "./assessment-types";

const packageTypes = new Set<AssessmentType>(["LESSON_QUIZ", "UNIT_TEST", "LEVEL_TEST", "PLACEMENT"]);
const itemTypes = new Set<AssessmentItemType>(["multiple_choice", "fill_blank", "matching", "ordering", "reading", "listening"]);
const safeId = /^[A-Za-z0-9][A-Za-z0-9._-]*$/u;
const hash = /^[a-f0-9]{64}$/u;
const bands = new Set(["A1", "A2", "B1", "B2", "C1", "C2"]);

function isRecord(value: unknown): value is Record<string, unknown> {
  return Boolean(value) && typeof value === "object" && !Array.isArray(value);
}
function only(value: Record<string, unknown>, fields: readonly string[], label: string): void {
  if (Object.keys(value).some((field) => !fields.includes(field))) throw new Error(`${label} contains unsupported fields.`);
}
function text(value: unknown): value is string { return typeof value === "string" && value.trim().length > 0; }
function strings(value: unknown): value is readonly string[] { return Array.isArray(value) && value.length > 0 && value.every(text) && new Set(value).size === value.length; }
function safe(value: unknown): value is string { return text(value) && safeId.test(value); }
function validHash(value: unknown): value is string { return text(value) && hash.test(value); }

function validateAnswerContract(value: unknown, type: AssessmentItemType): asserts value is AssessmentAnswerContract {
  if (!isRecord(value)) throw new Error("Assessment snapshot contains an invalid answer contract.");
  if (type === "multiple_choice") {
    only(value, ["correctAnswer"], "Assessment multiple-choice answer contract");
    if (!text(value.correctAnswer)) throw new Error("Assessment snapshot contains an invalid multiple-choice answer.");
    return;
  }
  if (type === "fill_blank" || type === "reading" || type === "listening") {
    only(value, ["acceptableAnswers"], "Assessment answer contract");
    if (!strings(value.acceptableAnswers)) throw new Error("Assessment snapshot contains invalid acceptable answers.");
    return;
  }
  if (type === "matching") {
    only(value, ["pairs"], "Assessment matching contract");
    if (!Array.isArray(value.pairs) || value.pairs.length === 0 || !value.pairs.every((pair) =>
      isRecord(pair) && Object.keys(pair).length === 2 && text(pair.left) && text(pair.right))) {
      throw new Error("Assessment snapshot contains invalid matching pairs.");
    }
    const pairs = value.pairs as readonly Record<string, unknown>[];
    if (new Set(pairs.map((pair) => pair.left)).size !== pairs.length || new Set(pairs.map((pair) => pair.right)).size !== pairs.length) {
      throw new Error("Assessment snapshot contains duplicate matching pairs.");
    }
    return;
  }
  only(value, ["correctOrder"], "Assessment ordering contract");
  if (!strings(value.correctOrder)) throw new Error("Assessment snapshot contains invalid ordering answers.");
}

function validateItem(value: unknown): asserts value is AssessmentItem {
  if (!isRecord(value)) throw new Error("Assessment snapshot contains an invalid item.");
  only(value, ["id", "type", "prompt", "stimulus", "question", "options", "items", "source", "targetIds", "targetDimensions", "conceptIds", "answerContract"], "Assessment item");
  if (!safe(value.id) || !text(value.type) || !itemTypes.has(value.type as AssessmentItemType) || !text(value.prompt) ||
    !strings(value.targetIds) || !strings(value.targetDimensions) || !strings(value.conceptIds) || !isRecord(value.source)) {
    throw new Error("Assessment snapshot contains an invalid item.");
  }
  const type = value.type as AssessmentItemType;
  only(value.source, ["level", "tier", "unitId", "lessonId", "packetId", "packetSha256", "exerciseId", "questionIndex"], "Assessment item source");
  if (!text(value.source.level) || !bands.has(value.source.level) || !text(value.source.tier) || !safe(value.source.unitId) ||
    !safe(value.source.lessonId) || !safe(value.source.packetId) || !validHash(value.source.packetSha256) || !safe(value.source.exerciseId) ||
    (value.source.questionIndex !== undefined && (!Number.isInteger(value.source.questionIndex) || (value.source.questionIndex as number) < 1))) {
    throw new Error("Assessment snapshot contains an invalid item source.");
  }
  if (value.stimulus !== undefined && !text(value.stimulus) || value.question !== undefined && !text(value.question) ||
    value.options !== undefined && !strings(value.options) || value.items !== undefined && !strings(value.items)) {
    throw new Error("Assessment snapshot contains invalid optional item content.");
  }
  validateAnswerContract(value.answerContract, type);
  if (type === "multiple_choice" && (!strings(value.options) || !value.options.includes((value.answerContract as { correctAnswer: string }).correctAnswer))) {
    throw new Error("Assessment snapshot contains invalid multiple-choice options.");
  }
  if (type === "ordering") {
    const contract = value.answerContract as { correctOrder: readonly string[] };
    if (!strings(value.items) || value.items.length !== contract.correctOrder.length ||
      JSON.stringify([...value.items].sort()) !== JSON.stringify([...contract.correctOrder].sort())) throw new Error("Assessment snapshot contains invalid ordering data.");
  }
  if ((type === "reading" || type === "listening") && (!text(value.stimulus) || !text(value.question) || value.source.questionIndex === undefined)) {
    throw new Error("Assessment snapshot contains an incomplete question item.");
  }
}

function validatePackage(value: unknown): asserts value is AssessmentPackage {
  if (!isRecord(value)) throw new Error("Assessment snapshot contains an invalid package.");
  only(value, ["id", "type", "packageSha256", "scope", "items", "contentStatus"], "Assessment package");
  if (!safe(value.id) || !text(value.type) || !packageTypes.has(value.type as AssessmentType) || !validHash(value.packageSha256) ||
    value.contentStatus !== "UNREVIEWED" || !isRecord(value.scope) || !Array.isArray(value.items) || value.items.length === 0) {
    throw new Error("Assessment snapshot contains an invalid package.");
  }
  only(value.scope, ["levels", "tiers", "unitIds", "lessonIds", "targetDimensions", "outlineAssessmentId", "itemsPerTier", "passingCorrectPerTier", "outputField"], "Assessment package scope");
  if (!strings(value.scope.levels) || value.scope.levels.some((band) => !bands.has(band)) || !strings(value.scope.tiers) ||
    !strings(value.scope.unitIds) || !strings(value.scope.lessonIds) || value.scope.targetDimensions !== undefined && !strings(value.scope.targetDimensions) ||
    value.scope.outlineAssessmentId !== undefined && !safe(value.scope.outlineAssessmentId) ||
    value.scope.itemsPerTier !== undefined && (!Number.isInteger(value.scope.itemsPerTier) || (value.scope.itemsPerTier as number) < 1) ||
    value.scope.passingCorrectPerTier !== undefined && (!Number.isInteger(value.scope.passingCorrectPerTier) || (value.scope.passingCorrectPerTier as number) < 1) ||
    value.scope.outputField !== undefined && !text(value.scope.outputField)) {
    throw new Error("Assessment snapshot contains an invalid package scope.");
  }
  value.items.forEach(validateItem);
  const items = value.items as readonly AssessmentItem[];
  if (new Set(items.map((item) => item.id)).size !== items.length) throw new Error("Assessment snapshot contains duplicate item IDs.");
}

export function validateAssessmentSnapshot(value: unknown): asserts value is AssessmentSnapshot {
  if (!isRecord(value)) throw new Error("Unsupported assessment snapshot metadata.");
  only(value, ["schemaVersion", "runId", "manifestSha256", "contentStatus", "packages"], "Assessment snapshot");
  if (value.schemaVersion !== "1.0" || value.runId !== ASSESSMENT_RUN_ID || !validHash(value.manifestSha256) ||
    value.contentStatus !== "UNREVIEWED" || !Array.isArray(value.packages) || value.packages.length !== 367) {
    throw new Error("Unsupported assessment snapshot metadata.");
  }
  value.packages.forEach(validatePackage);
  const packages = value.packages as readonly AssessmentPackage[];
  if (new Set(packages.map((item) => item.id)).size !== packages.length) throw new Error("Assessment snapshot contains duplicate package IDs.");
  const counts = packages.reduce<Record<string, number>>((result, assessment) => ({ ...result, [assessment.type]: (result[assessment.type] ?? 0) + 1 }), {});
  if (counts.LESSON_QUIZ !== 300 || counts.UNIT_TEST !== 60 || counts.LEVEL_TEST !== 6 || counts.PLACEMENT !== 1 || Object.keys(counts).length !== 4) {
    throw new Error("Assessment snapshot inventory drifted.");
  }
}

const candidate: unknown = rawSnapshot;
validateAssessmentSnapshot(candidate);
export const assessmentSnapshot = candidate;

export function getAssessmentPackages(): readonly AssessmentPackage[] { return assessmentSnapshot.packages; }
export function getAssessmentPackage(assessmentId: string): AssessmentPackage | undefined {
  return assessmentSnapshot.packages.find((assessment) => assessment.id === assessmentId);
}
export function getPlacementPackage(): AssessmentPackage {
  const assessment = assessmentSnapshot.packages.find((item) => item.type === "PLACEMENT");
  if (!assessment) throw new Error("Assessment snapshot has no placement package.");
  return assessment;
}
export function getLessonQuiz(lessonId: string): AssessmentPackage | undefined {
  return assessmentSnapshot.packages.find((item) => item.type === "LESSON_QUIZ" && item.scope.lessonIds.length === 1 && item.scope.lessonIds[0] === lessonId);
}
export function getUnitTest(unitId: string): AssessmentPackage | undefined {
  return assessmentSnapshot.packages.find((item) => item.type === "UNIT_TEST" && item.scope.unitIds.length === 1 && item.scope.unitIds[0] === unitId);
}
export function getLevelTest(level: string): AssessmentPackage | undefined {
  return assessmentSnapshot.packages.find((item) => item.type === "LEVEL_TEST" && item.scope.levels.length === 1 && item.scope.levels[0] === level);
}
