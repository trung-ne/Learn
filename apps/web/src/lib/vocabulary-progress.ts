import type { LanguageCode } from "@/content/types";
import type { StorageLike } from "./progress";
import { reportLocalStateAvailable, reportLocalStateIssue } from "./local-state";

export const VOCABULARY_PROGRESS_VERSION = 1 as const;
const VOCABULARY_PROGRESS_KEY_PREFIX = "english-master.vocabulary.v1";
const REVIEW_INTERVAL_DAYS = [1, 3, 7, 14, 30, 60] as const;
const MAX_REVIEW_SESSION_SIZE = 10;

export type VocabularyLearningState = "learning" | "reviewing" | "mastered";
export type VocabularyIntervalIndex = 0 | 1 | 2 | 3 | 4 | 5;

export interface VocabularyScope {
  readonly learnerId: string;
  readonly language: LanguageCode;
}

export interface WordSenseProgress {
  readonly state: VocabularyLearningState;
  readonly attempts: number;
  readonly correctAttempts: number;
  readonly mistakes: number;
  readonly masteryScore: number;
  readonly intervalIndex: VocabularyIntervalIndex;
  readonly introducedAt: string;
  readonly lastAttemptAt?: string;
  readonly lastMistakeAt?: string;
  readonly nextReviewAt: string;
}

export interface VocabularyProgress extends VocabularyScope {
  readonly version: typeof VOCABULARY_PROGRESS_VERSION;
  readonly inventoryVersion: string;
  readonly senses: Readonly<Record<string, WordSenseProgress>>;
}

export interface VocabularyQueueCandidate {
  readonly senseId: string;
  readonly introductionOrder: number;
}

interface QueueEntry extends VocabularyQueueCandidate {
  readonly progress: WordSenseProgress;
  readonly priority: number;
}

function browserStorage(): StorageLike {
  return window.localStorage;
}

function isLanguageCode(value: unknown): value is LanguageCode {
  return value === "en" || value === "de";
}

function isLearnerId(value: unknown): value is string {
  return typeof value === "string" && /^[a-z0-9-]{8,128}$/iu.test(value);
}

function isSafeSenseId(value: unknown): value is string {
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

function isIntervalIndex(value: unknown): value is VocabularyIntervalIndex {
  return Number.isInteger(value) && typeof value === "number" && value >= 0 && value < REVIEW_INTERVAL_DAYS.length;
}

function isLearningState(value: unknown): value is VocabularyLearningState {
  return value === "learning" || value === "reviewing" || value === "mastered";
}

function calculateMasteryScore(correctAttempts: number, attempts: number): number {
  return attempts === 0 ? 0 : Math.round((correctAttempts / attempts) * 100);
}

function isWordSenseProgress(value: unknown): value is WordSenseProgress {
  if (!value || typeof value !== "object") return false;
  const item = value as Partial<WordSenseProgress>;
  if (!isLearningState(item.state) || !isNonNegativeInteger(item.attempts) ||
    !isNonNegativeInteger(item.correctAttempts) || !isNonNegativeInteger(item.mistakes) ||
    !isIntervalIndex(item.intervalIndex) || !isNonNegativeInteger(item.masteryScore) || item.masteryScore > 100 ||
    !isTimestamp(item.introducedAt) || !isTimestamp(item.nextReviewAt) ||
    (item.lastAttemptAt !== undefined && !isTimestamp(item.lastAttemptAt)) ||
    (item.lastMistakeAt !== undefined && !isTimestamp(item.lastMistakeAt))) {
    return false;
  }
  if (item.attempts !== item.correctAttempts + item.mistakes ||
    item.masteryScore !== calculateMasteryScore(item.correctAttempts, item.attempts)) {
    return false;
  }
  if (item.state === "mastered" && item.intervalIndex !== 5) return false;
  if (item.state === "learning" && item.intervalIndex !== 0) return false;
  return true;
}

function utcDayAfter(timestamp: string, days: number): string {
  const date = new Date(timestamp);
  const next = new Date(Date.UTC(
    date.getUTCFullYear(),
    date.getUTCMonth(),
    date.getUTCDate() + days,
    date.getUTCHours(),
    date.getUTCMinutes(),
    date.getUTCSeconds(),
    date.getUTCMilliseconds(),
  ));
  return next.toISOString();
}

function reviewDays(intervalIndex: VocabularyIntervalIndex): number {
  return REVIEW_INTERVAL_DAYS[intervalIndex];
}

export function vocabularyProgressKey(scope: VocabularyScope): string {
  return `${VOCABULARY_PROGRESS_KEY_PREFIX}.${scope.learnerId}.${scope.language}`;
}

export function emptyVocabularyProgress(scope: VocabularyScope, inventoryVersion: string): VocabularyProgress {
  return { version: VOCABULARY_PROGRESS_VERSION, ...scope, inventoryVersion, senses: {} };
}

export function parseVocabularyProgress(
  serialized: string | null,
  scope: VocabularyScope,
  inventoryVersion: string,
): VocabularyProgress {
  if (!serialized) return emptyVocabularyProgress(scope, inventoryVersion);
  try {
    const value: unknown = JSON.parse(serialized);
    if (!value || typeof value !== "object") return emptyVocabularyProgress(scope, inventoryVersion);
    const candidate = value as Partial<VocabularyProgress>;
    if (candidate.version !== VOCABULARY_PROGRESS_VERSION || candidate.learnerId !== scope.learnerId ||
      candidate.language !== scope.language || !isLearnerId(candidate.learnerId) || !isLanguageCode(candidate.language) ||
      typeof candidate.inventoryVersion !== "string" || candidate.inventoryVersion.trim().length === 0 ||
      !candidate.senses || typeof candidate.senses !== "object" ||
      !Object.entries(candidate.senses).every(([senseId, item]) => isSafeSenseId(senseId) && isWordSenseProgress(item))) {
      return emptyVocabularyProgress(scope, inventoryVersion);
    }
    return { ...candidate as VocabularyProgress, inventoryVersion };
  } catch {
    return emptyVocabularyProgress(scope, inventoryVersion);
  }
}

export function loadVocabularyProgress(
  scope: VocabularyScope,
  inventoryVersion: string,
  storage?: StorageLike,
): VocabularyProgress {
  try {
    return parseVocabularyProgress((storage ?? browserStorage()).getItem(vocabularyProgressKey(scope)), scope, inventoryVersion);
  } catch {
    return emptyVocabularyProgress(scope, inventoryVersion);
  }
}

export function saveVocabularyProgress(progress: VocabularyProgress, storage?: StorageLike): boolean {
  try {
    (storage ?? browserStorage()).setItem(vocabularyProgressKey(progress), JSON.stringify(progress));
    reportLocalStateAvailable();
    return true;
  } catch (error) {
    reportLocalStateIssue("write", error);
    return false;
  }
}

export function startWordSense(
  progress: VocabularyProgress,
  senseId: string,
  now: string,
): VocabularyProgress {
  if (!isSafeSenseId(senseId) || !isTimestamp(now) || progress.senses[senseId]) return progress;
  const state: WordSenseProgress = {
    state: "learning",
    attempts: 0,
    correctAttempts: 0,
    mistakes: 0,
    masteryScore: 0,
    intervalIndex: 0,
    introducedAt: now,
    nextReviewAt: now,
  };
  return { ...progress, senses: { ...progress.senses, [senseId]: state } };
}

export function recordWordSenseResult(
  progress: VocabularyProgress,
  senseId: string,
  correct: boolean,
  now: string,
): VocabularyProgress {
  if (!isSafeSenseId(senseId) || !isTimestamp(now)) return progress;
  const started = startWordSense(progress, senseId, now);
  const current = started.senses[senseId];
  if (!current) return progress;
  const attempts = current.attempts + 1;
  const correctAttempts = current.correctAttempts + (correct ? 1 : 0);
  const mistakes = current.mistakes + (correct ? 0 : 1);
  const intervalIndex: VocabularyIntervalIndex = correct
    ? Math.min(current.intervalIndex + 1, 5) as VocabularyIntervalIndex
    : 0;
  const state: VocabularyLearningState = correct
    ? current.intervalIndex === 5 ? "mastered" : "reviewing"
    : "learning";
  const scheduledInterval: VocabularyIntervalIndex = correct ? current.intervalIndex : 0;
  const next: WordSenseProgress = {
    state,
    attempts,
    correctAttempts,
    mistakes,
    masteryScore: calculateMasteryScore(correctAttempts, attempts),
    intervalIndex,
    introducedAt: current.introducedAt,
    lastAttemptAt: now,
    ...(correct ? { lastMistakeAt: current.lastMistakeAt } : { lastMistakeAt: now }),
    nextReviewAt: utcDayAfter(now, reviewDays(scheduledInterval)),
  };
  return { ...started, senses: { ...started.senses, [senseId]: next } };
}

export function isDue(progress: WordSenseProgress, now: string): boolean {
  return isTimestamp(now) && progress.nextReviewAt <= now;
}

export function hasRecentVocabularyMistake(progress: WordSenseProgress, now: string): boolean {
  if (!progress.lastMistakeAt || !isTimestamp(now)) return false;
  return Date.parse(progress.lastMistakeAt) >= Date.parse(utcDayAfter(now, -7));
}

export function selectVocabularyReviewQueue(
  progress: VocabularyProgress,
  candidates: readonly VocabularyQueueCandidate[],
  now: string,
  limit = MAX_REVIEW_SESSION_SIZE,
): readonly string[] {
  if (!isTimestamp(now) || !Number.isInteger(limit) || limit < 1) return [];
  const known = new Set<string>();
  const entries: QueueEntry[] = [];
  for (const candidate of candidates) {
    if (!isSafeSenseId(candidate.senseId) || known.has(candidate.senseId) ||
      !Number.isInteger(candidate.introductionOrder) || candidate.introductionOrder < 0) continue;
    known.add(candidate.senseId);
    const item = progress.senses[candidate.senseId];
    if (!item) continue;
    const priority = hasRecentVocabularyMistake(item, now) ? 0 : isDue(item, now) ? 1 : 2;
    if (priority === 2) continue;
    entries.push({ ...candidate, progress: item, priority });
  }
  return entries
    .sort((left, right) => left.priority - right.priority ||
      left.progress.nextReviewAt.localeCompare(right.progress.nextReviewAt) ||
      left.progress.masteryScore - right.progress.masteryScore ||
      left.introductionOrder - right.introductionOrder ||
      left.senseId.localeCompare(right.senseId))
    .slice(0, Math.min(limit, MAX_REVIEW_SESSION_SIZE))
    .map((entry) => entry.senseId);
}

export function activeVocabularySenseIds(
  progress: VocabularyProgress,
  knownSenseIds: ReadonlySet<string>,
): readonly string[] {
  return Object.keys(progress.senses).filter((senseId) => knownSenseIds.has(senseId));
}
