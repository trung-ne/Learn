import type { GrammarLearningState } from "@/content/grammar-types";
import type { StorageLike } from "./progress";
import { reportLocalStateAvailable, reportLocalStateIssue } from "./local-state";

export const GRAMMAR_PROGRESS_VERSION = 1 as const;
const GRAMMAR_PROGRESS_KEY_PREFIX = "english-master.grammar.v1";
const REVIEW_INTERVAL_DAYS = [1, 3, 7, 14, 30, 60] as const;
const MAX_REVIEW_SESSION_SIZE = 10;

export type GrammarIntervalIndex = 0 | 1 | 2 | 3 | 4 | 5;

export interface GrammarScope {
  readonly learnerId: string;
  readonly language: "en";
}

export interface GrammarTargetProgress {
  readonly state: GrammarLearningState;
  readonly attempts: number;
  readonly correctAttempts: number;
  readonly incorrectOutcomes: number;
  readonly localScore: number;
  readonly intervalIndex: GrammarIntervalIndex;
  readonly introducedAt: string;
  readonly lastAttemptAt?: string;
  readonly lastIncorrectAt?: string;
  readonly nextReviewAt: string;
}

export interface GrammarProgress extends GrammarScope {
  readonly version: typeof GRAMMAR_PROGRESS_VERSION;
  readonly inventoryVersion: string;
  readonly targets: Readonly<Record<string, GrammarTargetProgress>>;
}

export interface GrammarQueueCandidate {
  readonly targetId: string;
  readonly introductionOrder: number;
}

interface QueueEntry extends GrammarQueueCandidate {
  readonly progress: GrammarTargetProgress;
  readonly priority: number;
}

function browserStorage(): StorageLike {
  return window.localStorage;
}

function isLearnerId(value: unknown): value is string {
  return typeof value === "string" && /^[a-z0-9-]{8,128}$/iu.test(value);
}

function isSafeId(value: unknown): value is string {
  return typeof value === "string" && /^[a-z][a-z0-9-]*$/u.test(value);
}

function isTimestamp(value: unknown): value is string {
  return typeof value === "string" &&
    /^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\.\d{3}Z$/u.test(value) &&
    !Number.isNaN(Date.parse(value));
}

function isNonNegativeInteger(value: unknown): value is number {
  return Number.isInteger(value) && typeof value === "number" && value >= 0;
}

function isIntervalIndex(value: unknown): value is GrammarIntervalIndex {
  return Number.isInteger(value) && typeof value === "number" && value >= 0 && value < REVIEW_INTERVAL_DAYS.length;
}

function isLearningState(value: unknown): value is GrammarLearningState {
  return value === "practising" || value === "reviewing" || value === "locally_consolidated";
}

function calculateLocalScore(correctAttempts: number, attempts: number): number {
  return attempts === 0 ? 0 : Math.round((correctAttempts / attempts) * 100);
}

function isTargetProgress(value: unknown): value is GrammarTargetProgress {
  if (!value || typeof value !== "object") return false;
  const item = value as Partial<GrammarTargetProgress>;
  if (!isLearningState(item.state) || !isNonNegativeInteger(item.attempts) ||
    !isNonNegativeInteger(item.correctAttempts) || !isNonNegativeInteger(item.incorrectOutcomes) ||
    !isIntervalIndex(item.intervalIndex) || !isNonNegativeInteger(item.localScore) || item.localScore > 100 ||
    !isTimestamp(item.introducedAt) || !isTimestamp(item.nextReviewAt) ||
    (item.lastAttemptAt !== undefined && !isTimestamp(item.lastAttemptAt)) ||
    (item.lastIncorrectAt !== undefined && !isTimestamp(item.lastIncorrectAt))) {
    return false;
  }
  if (item.attempts !== item.correctAttempts + item.incorrectOutcomes ||
    item.localScore !== calculateLocalScore(item.correctAttempts, item.attempts) ||
    (item.state === "locally_consolidated" && item.intervalIndex !== 5) ||
    (item.state === "practising" && item.intervalIndex !== 0)) {
    return false;
  }
  return true;
}

function utcDayAfter(timestamp: string, days: number): string {
  const date = new Date(timestamp);
  return new Date(Date.UTC(
    date.getUTCFullYear(), date.getUTCMonth(), date.getUTCDate() + days,
    date.getUTCHours(), date.getUTCMinutes(), date.getUTCSeconds(), date.getUTCMilliseconds(),
  )).toISOString();
}

function reviewDays(intervalIndex: GrammarIntervalIndex): number {
  return REVIEW_INTERVAL_DAYS[intervalIndex];
}

export function grammarProgressKey(scope: GrammarScope): string {
  return `${GRAMMAR_PROGRESS_KEY_PREFIX}.${scope.learnerId}.${scope.language}`;
}

export function emptyGrammarProgress(scope: GrammarScope, inventoryVersion: string): GrammarProgress {
  return { version: GRAMMAR_PROGRESS_VERSION, ...scope, inventoryVersion, targets: {} };
}

export function parseGrammarProgress(
  serialized: string | null,
  scope: GrammarScope,
  inventoryVersion: string,
): GrammarProgress {
  if (!serialized) return emptyGrammarProgress(scope, inventoryVersion);
  try {
    const value: unknown = JSON.parse(serialized);
    if (!value || typeof value !== "object") return emptyGrammarProgress(scope, inventoryVersion);
    const candidate = value as Partial<GrammarProgress>;
    if (candidate.version !== GRAMMAR_PROGRESS_VERSION || candidate.learnerId !== scope.learnerId ||
      candidate.language !== "en" || !isLearnerId(candidate.learnerId) ||
      candidate.inventoryVersion !== inventoryVersion ||
      typeof candidate.inventoryVersion !== "string" || candidate.inventoryVersion.trim().length === 0 ||
      !candidate.targets || typeof candidate.targets !== "object" ||
      !Object.entries(candidate.targets).every(([targetId, item]) => isSafeId(targetId) && isTargetProgress(item))) {
      return emptyGrammarProgress(scope, inventoryVersion);
    }
    return { ...candidate as GrammarProgress, inventoryVersion };
  } catch {
    return emptyGrammarProgress(scope, inventoryVersion);
  }
}

export function loadGrammarProgress(
  scope: GrammarScope,
  inventoryVersion: string,
  storage?: StorageLike,
): GrammarProgress {
  try {
    return parseGrammarProgress((storage ?? browserStorage()).getItem(grammarProgressKey(scope)), scope, inventoryVersion);
  } catch {
    return emptyGrammarProgress(scope, inventoryVersion);
  }
}

export function saveGrammarProgress(progress: GrammarProgress, storage?: StorageLike): boolean {
  try {
    (storage ?? browserStorage()).setItem(grammarProgressKey(progress), JSON.stringify(progress));
    reportLocalStateAvailable();
    return true;
  } catch (error) {
    reportLocalStateIssue("write", error);
    return false;
  }
}

function initialTargetProgress(now: string): GrammarTargetProgress {
  return {
    state: "practising", attempts: 0, correctAttempts: 0, incorrectOutcomes: 0, localScore: 0,
    intervalIndex: 0, introducedAt: now, nextReviewAt: now,
  };
}

export function recordGrammarTargetResult(
  progress: GrammarProgress,
  targetId: string,
  correct: boolean,
  now: string,
): GrammarProgress {
  if (!isSafeId(targetId) || !isTimestamp(now)) return progress;
  const current = progress.targets[targetId] ?? initialTargetProgress(now);
  const attempts = current.attempts + 1;
  const correctAttempts = current.correctAttempts + (correct ? 1 : 0);
  const incorrectOutcomes = current.incorrectOutcomes + (correct ? 0 : 1);
  const intervalIndex: GrammarIntervalIndex = correct
    ? Math.min(current.intervalIndex + 1, 5) as GrammarIntervalIndex
    : 0;
  const state: GrammarLearningState = correct
    ? current.intervalIndex === 5 ? "locally_consolidated" : "reviewing"
    : "practising";
  const scheduledInterval = correct ? current.intervalIndex : 0;
  const next: GrammarTargetProgress = {
    state,
    attempts,
    correctAttempts,
    incorrectOutcomes,
    localScore: calculateLocalScore(correctAttempts, attempts),
    intervalIndex,
    introducedAt: current.introducedAt,
    lastAttemptAt: now,
    ...(correct ? { lastIncorrectAt: current.lastIncorrectAt } : { lastIncorrectAt: now }),
    nextReviewAt: utcDayAfter(now, reviewDays(scheduledInterval)),
  };
  return { ...progress, targets: { ...progress.targets, [targetId]: next } };
}

export function isGrammarTargetDue(progress: GrammarTargetProgress, now: string): boolean {
  return isTimestamp(now) && progress.nextReviewAt <= now;
}

export function selectGrammarReviewQueue(
  progress: GrammarProgress,
  candidates: readonly GrammarQueueCandidate[],
  now: string,
  limit = MAX_REVIEW_SESSION_SIZE,
): readonly string[] {
  if (!isTimestamp(now) || !Number.isInteger(limit) || limit < 1) return [];
  const seen = new Set<string>();
  const entries: QueueEntry[] = [];
  for (const candidate of candidates) {
    if (!isSafeId(candidate.targetId) || seen.has(candidate.targetId) ||
      !Number.isInteger(candidate.introductionOrder) || candidate.introductionOrder < 0) continue;
    seen.add(candidate.targetId);
    const item = progress.targets[candidate.targetId];
    if (!item || !isGrammarTargetDue(item, now)) continue;
    entries.push({ ...candidate, progress: item, priority: item.lastIncorrectAt ? 0 : 1 });
  }
  return entries
    .sort((left, right) => left.priority - right.priority ||
      left.progress.nextReviewAt.localeCompare(right.progress.nextReviewAt) ||
      left.progress.localScore - right.progress.localScore ||
      left.introductionOrder - right.introductionOrder || left.targetId.localeCompare(right.targetId))
    .slice(0, Math.min(limit, MAX_REVIEW_SESSION_SIZE))
    .map((entry) => entry.targetId);
}

export function activeGrammarTargetIds(progress: GrammarProgress, knownTargetIds: ReadonlySet<string>): readonly string[] {
  return Object.keys(progress.targets).filter((targetId) => knownTargetIds.has(targetId));
}
