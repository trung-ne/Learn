import type { AssessmentItem, AssessmentPackage } from "@/content/assessment-types";
import { ASSESSMENT_RUN_ID } from "@/content/assessment-types";
import { arraysMatch, matchesAnyAnswer } from "@/lib/answers";
import type { StorageLike } from "@/lib/progress";
import { reportLocalStateAvailable, reportLocalStateIssue } from "./local-state";

export const ASSESSMENT_PROGRESS_VERSION = 1 as const;
const STORAGE_PREFIX = "english-master.assessment.v1";
const TIER_ORDER = ["A1.1", "A1.2", "A2.1", "A2.2", "B1.1", "B1.2", "B2.1", "B2.2", "C1.1", "C1.2", "C2.1", "C2.2"] as const;

export type AssessmentResponse = string | readonly string[] | Readonly<Record<string, string>>;
export type AssessmentAttemptStatus = "IN_PROGRESS" | "SUBMITTED";

export interface AssessmentProgressScope {
  readonly learnerId: string;
  readonly language: "en";
}

export interface AssessmentItemResult {
  readonly itemId: string;
  readonly correct: boolean;
  readonly type: AssessmentItem["type"];
  readonly targetDimensions: readonly string[];
  readonly conceptIds: readonly string[];
}

export interface AssessmentAttempt {
  readonly attemptId: string;
  readonly packageSha256: string;
  readonly submittedAt: string;
  readonly correctCount: number;
  readonly itemCount: number;
  readonly itemResults: readonly AssessmentItemResult[];
  readonly suggestedStartTier?: string;
}

export interface AssessmentPackageProgress {
  readonly packageSha256: string;
  readonly draftResponses?: Readonly<Record<string, AssessmentResponse>>;
  readonly attempts: readonly AssessmentAttempt[];
}

export interface AssessmentProgress extends AssessmentProgressScope {
  readonly version: typeof ASSESSMENT_PROGRESS_VERSION;
  readonly runId: typeof ASSESSMENT_RUN_ID;
  readonly packages: Readonly<Record<string, AssessmentPackageProgress>>;
}

export interface EvidenceTotal {
  readonly correct: number;
  readonly total: number;
  readonly completedPackages: number;
}

function browserStorage(): StorageLike { return window.localStorage; }
function isRecord(value: unknown): value is Record<string, unknown> { return Boolean(value) && typeof value === "object" && !Array.isArray(value); }
function isSafeId(value: unknown): value is string { return typeof value === "string" && /^[A-Za-z0-9][A-Za-z0-9._-]*$/u.test(value); }
function isHash(value: unknown): value is string { return typeof value === "string" && /^[a-f0-9]{64}$/u.test(value); }
function isTimestamp(value: unknown): value is string {
  return typeof value === "string" && /^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\.\d{3}Z$/u.test(value) && !Number.isNaN(Date.parse(value));
}
function isLearnerId(value: unknown): value is string { return typeof value === "string" && /^[a-z0-9-]{8,128}$/iu.test(value); }
function isResponse(value: unknown): value is AssessmentResponse {
  return typeof value === "string" || Array.isArray(value) && value.every((item) => typeof item === "string") ||
    isRecord(value) && Object.entries(value).every(([key, item]) => typeof key === "string" && typeof item === "string");
}
function isItemResult(value: unknown): value is AssessmentItemResult {
  if (!isRecord(value) || !isSafeId(value.itemId) || typeof value.correct !== "boolean" ||
    !["multiple_choice", "fill_blank", "matching", "ordering", "reading", "listening"].includes(value.type as string) ||
    !Array.isArray(value.targetDimensions) || !value.targetDimensions.every((item) => typeof item === "string") ||
    !Array.isArray(value.conceptIds) || !value.conceptIds.every((item) => typeof item === "string")) return false;
  return true;
}
function isAttempt(value: unknown): value is AssessmentAttempt {
  if (!isRecord(value) || !isSafeId(value.attemptId) || !isHash(value.packageSha256) || !isTimestamp(value.submittedAt) ||
    !Number.isInteger(value.correctCount) || !Number.isInteger(value.itemCount) || value.correctCount < 0 || value.itemCount < 1 || value.correctCount > value.itemCount ||
    !Array.isArray(value.itemResults) || value.itemResults.length !== value.itemCount || !value.itemResults.every(isItemResult) ||
    value.suggestedStartTier !== undefined && !TIER_ORDER.includes(value.suggestedStartTier as (typeof TIER_ORDER)[number])) return false;
  return new Set(value.itemResults.map((item) => item.itemId)).size === value.itemResults.length;
}
function isPackageProgress(value: unknown): value is AssessmentPackageProgress {
  if (!isRecord(value) || !isHash(value.packageSha256) || !Array.isArray(value.attempts) || !value.attempts.every(isAttempt)) return false;
  if (value.draftResponses !== undefined && (!isRecord(value.draftResponses) || !Object.entries(value.draftResponses).every(([itemId, response]) => isSafeId(itemId) && isResponse(response)))) return false;
  return true;
}

export function assessmentProgressKey(scope: AssessmentProgressScope): string {
  return `${STORAGE_PREFIX}.${scope.learnerId}.${scope.language}.${ASSESSMENT_RUN_ID}`;
}
export function emptyAssessmentProgress(scope: AssessmentProgressScope): AssessmentProgress {
  return { version: ASSESSMENT_PROGRESS_VERSION, runId: ASSESSMENT_RUN_ID, ...scope, packages: {} };
}
export function parseAssessmentProgress(serialized: string | null, scope: AssessmentProgressScope): AssessmentProgress {
  if (!serialized) return emptyAssessmentProgress(scope);
  try {
    const value: unknown = JSON.parse(serialized);
    if (!isRecord(value) || value.version !== ASSESSMENT_PROGRESS_VERSION || value.runId !== ASSESSMENT_RUN_ID ||
      value.learnerId !== scope.learnerId || value.language !== "en" || !isLearnerId(value.learnerId) || !isRecord(value.packages) ||
      !Object.entries(value.packages).every(([packageId, progress]) => isSafeId(packageId) && isPackageProgress(progress))) {
      return emptyAssessmentProgress(scope);
    }
    return value as unknown as AssessmentProgress;
  } catch { return emptyAssessmentProgress(scope); }
}
export function loadAssessmentProgress(scope: AssessmentProgressScope, storage?: StorageLike): AssessmentProgress {
  try { return parseAssessmentProgress((storage ?? browserStorage()).getItem(assessmentProgressKey(scope)), scope); }
  catch { return emptyAssessmentProgress(scope); }
}
export function saveAssessmentProgress(progress: AssessmentProgress, storage?: StorageLike): boolean {
  if (progress.version !== ASSESSMENT_PROGRESS_VERSION || progress.runId !== ASSESSMENT_RUN_ID || progress.language !== "en" || !isLearnerId(progress.learnerId)) return false;
  try {
    (storage ?? browserStorage()).setItem(assessmentProgressKey(progress), JSON.stringify(progress));
    reportLocalStateAvailable();
    return true;
  } catch (error) {
    reportLocalStateIssue("write", error);
    return false;
  }
}
export function resetAssessmentProgress(scope: AssessmentProgressScope, storage?: StorageLike): boolean {
  try {
    (storage ?? browserStorage()).removeItem(assessmentProgressKey(scope));
    reportLocalStateAvailable();
    return true;
  } catch (error) {
    reportLocalStateIssue("remove", error);
    return false;
  }
}

function validDraftResponseForItem(item: AssessmentItem, response: AssessmentResponse | undefined): boolean {
  if (response === undefined) return false;
  if (item.type === "matching") {
    return isRecord(response) && "pairs" in item.answerContract &&
      Object.entries(response).every(([left, right]) =>
        item.answerContract.pairs.some((pair) => pair.left === left) && typeof right === "string",
      );
  }
  if (item.type === "ordering") {
    return Array.isArray(response) && "correctOrder" in item.answerContract &&
      response.length === item.answerContract.correctOrder.length &&
      new Set(response).size === response.length &&
      response.every((entry) => item.answerContract.correctOrder.includes(entry));
  }
  return typeof response === "string";
}

function completeResponseForItem(item: AssessmentItem, response: AssessmentResponse | undefined): boolean {
  if (!validDraftResponseForItem(item, response)) return false;
  if (item.type === "matching") {
    return isRecord(response) && "pairs" in item.answerContract &&
      Object.keys(response).length === item.answerContract.pairs.length &&
      item.answerContract.pairs.every((pair) => response[pair.left].trim().length > 0);
  }
  return item.type === "ordering" || typeof response === "string" && response.trim().length > 0;
}
function responseCorrect(item: AssessmentItem, response: AssessmentResponse): boolean {
  if (item.type === "matching") {
    if (!isRecord(response) || !("pairs" in item.answerContract)) return false;
    return item.answerContract.pairs.every((pair) => response[pair.left] === pair.right);
  }
  if (item.type === "ordering") return Array.isArray(response) && "correctOrder" in item.answerContract && arraysMatch(response, item.answerContract.correctOrder);
  if (typeof response !== "string") return false;
  if ("correctAnswer" in item.answerContract) return matchesAnyAnswer(response, [item.answerContract.correctAnswer]);
  return "acceptableAnswers" in item.answerContract && matchesAnyAnswer(response, item.answerContract.acceptableAnswers);
}
function packageCompatible(progress: AssessmentPackageProgress | undefined, assessment: AssessmentPackage): AssessmentPackageProgress {
  return progress && progress.packageSha256 === assessment.packageSha256 ? progress : { packageSha256: assessment.packageSha256, attempts: [] };
}
function attemptId(assessment: AssessmentPackage, index: number, submittedAt: string): string {
  return `attempt-${assessment.id}-${index + 1}-${Date.parse(submittedAt).toString(36)}`;
}

export function saveAssessmentDraft(
  progress: AssessmentProgress,
  assessment: AssessmentPackage,
  responses: Readonly<Record<string, AssessmentResponse>>,
): AssessmentProgress {
  const allowed = new Set(assessment.items.map((item) => item.id));
  if (!Object.entries(responses).every(([itemId, response]) => allowed.has(itemId) && validDraftResponseForItem(assessment.items.find((item) => item.id === itemId)!, response))) return progress;
  const current = packageCompatible(progress.packages[assessment.id], assessment);
  return { ...progress, packages: { ...progress.packages, [assessment.id]: { ...current, draftResponses: { ...responses } } } };
}

export function submitAssessment(
  progress: AssessmentProgress,
  assessment: AssessmentPackage,
  responses: Readonly<Record<string, AssessmentResponse>>,
  submittedAt: string,
): AssessmentProgress {
  if (!isTimestamp(submittedAt) || !assessment.items.every((item) => completeResponseForItem(item, responses[item.id])) ||
    Object.keys(responses).some((itemId) => !assessment.items.some((item) => item.id === itemId))) return progress;
  const current = packageCompatible(progress.packages[assessment.id], assessment);
  const itemResults = assessment.items.map((item) => ({
    itemId: item.id,
    correct: responseCorrect(item, responses[item.id]!),
    type: item.type,
    targetDimensions: item.targetDimensions,
    conceptIds: item.conceptIds,
  }));
  const correctCount = itemResults.filter((result) => result.correct).length;
  const result: AssessmentAttempt = {
    attemptId: attemptId(assessment, current.attempts.length, submittedAt),
    packageSha256: assessment.packageSha256,
    submittedAt,
    correctCount,
    itemCount: itemResults.length,
    itemResults,
    ...(assessment.type === "PLACEMENT" ? { suggestedStartTier: placementSuggestion(assessment, itemResults) } : {}),
  };
  return { ...progress, packages: { ...progress.packages, [assessment.id]: { packageSha256: assessment.packageSha256, attempts: [...current.attempts, result] } } };
}

export function latestAssessmentAttempt(progress: AssessmentProgress, assessment: AssessmentPackage): AssessmentAttempt | undefined {
  const record = progress.packages[assessment.id];
  if (!record || record.packageSha256 !== assessment.packageSha256) return undefined;
  return record.attempts.at(-1);
}
export function assessmentDraft(progress: AssessmentProgress, assessment: AssessmentPackage): Readonly<Record<string, AssessmentResponse>> {
  const record = progress.packages[assessment.id];
  return record?.packageSha256 === assessment.packageSha256 ? record.draftResponses ?? {} : {};
}
export function placementSuggestion(assessment: AssessmentPackage, results: readonly AssessmentItemResult[]): string {
  if (assessment.type !== "PLACEMENT") return "A1.1";
  const required = assessment.scope.passingCorrectPerTier ?? 2;
  for (const tier of TIER_ORDER) {
    const itemIds = assessment.items.filter((item) => item.source.tier === tier).map((item) => item.id);
    const correct = results.filter((result) => itemIds.includes(result.itemId) && result.correct).length;
    if (correct < required) return tier;
  }
  return "C2.2";
}
export function aggregateAssessmentEvidence(progress: AssessmentProgress): Readonly<Record<string, EvidenceTotal>> {
  const totals: Record<string, EvidenceTotal> = {};
  for (const record of Object.values(progress.packages)) {
    const attempt = record.attempts.at(-1);
    if (!attempt) continue;
    const labelsInPackage = new Set<string>();
    for (const result of attempt.itemResults) {
      const labels = [...result.targetDimensions, `item:${result.type}`];
      for (const label of labels) {
        labelsInPackage.add(label);
        const current = totals[label] ?? { correct: 0, total: 0, completedPackages: 0 };
        totals[label] = { ...current, correct: current.correct + (result.correct ? 1 : 0), total: current.total + 1 };
      }
    }
    for (const label of labelsInPackage) {
      const current = totals[label]!;
      totals[label] = { ...current, completedPackages: current.completedPackages + 1 };
    }
  }
  return totals;
}
