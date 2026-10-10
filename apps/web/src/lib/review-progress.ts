import type { CourseLevel, LanguageCode } from "@/content/types";
import type { StorageLike } from "./progress";
import { reportLocalStateAvailable, reportLocalStateIssue } from "./local-state";

export const REVIEW_PROGRESS_VERSION = 1 as const;
const REVIEW_PROGRESS_KEY_PREFIX = "english-master.review.v1";
const REVIEW_INTERVALS_MS = [10 * 60_000, 24 * 60 * 60_000, 3 * 24 * 60 * 60_000, 7 * 24 * 60 * 60_000, 14 * 24 * 60 * 60_000, 30 * 24 * 60 * 60_000, 60 * 24 * 60 * 60_000] as const;
const MAX_REVIEW_SESSION_SIZE = 10;

export type ReviewIntervalIndex = 0 | 1 | 2 | 3 | 4 | 5 | 6;
export type ReviewResult = "correct" | "incorrect";

export interface ReviewScope {
  readonly learnerId: string;
  readonly language: LanguageCode;
  readonly course: CourseLevel;
}

export interface ObjectiveReviewItem {
  readonly lessonId: string;
  readonly exerciseId: string;
  readonly firstSeenAt: string;
  readonly lastReviewedAt: string;
  readonly reviewCount: number;
  readonly correctCount: number;
  readonly incorrectCount: number;
  readonly ease: number;
  readonly intervalIndex: ReviewIntervalIndex;
  readonly mastery: number;
  readonly nextReviewAt: string;
  readonly lastResult: ReviewResult;
}

export interface ReviewProgress extends ReviewScope {
  readonly version: typeof REVIEW_PROGRESS_VERSION;
  readonly items: Readonly<Record<string, ObjectiveReviewItem>>;
}

export interface ObjectiveReviewOutcome {
  readonly lessonId: string;
  readonly exerciseId: string;
  readonly result: ReviewResult;
  readonly reviewedAt: string;
}

export interface ReviewCandidate {
  readonly source: "objective_exercise" | "vocabulary_sense";
  readonly id: string;
  readonly dueAt: string;
  readonly priority: "recent_incorrect" | "due";
  readonly order: number;
}

function browserStorage(): StorageLike {
  return window.localStorage;
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return Boolean(value) && typeof value === "object" && !Array.isArray(value);
}

function isLanguageCode(value: unknown): value is LanguageCode {
  return value === "en" || value === "de";
}

function isCourseLevel(value: unknown): value is CourseLevel {
  return value === "A1" || value === "A2" || value === "B1" || value === "B2" || value === "C1" || value === "C2";
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
  return typeof value === "number" && Number.isInteger(value) && value >= 0;
}

function isIntervalIndex(value: unknown): value is ReviewIntervalIndex {
  return typeof value === "number" && Number.isInteger(value) && value >= 0 && value < REVIEW_INTERVALS_MS.length;
}

function isEase(value: unknown): value is number {
  return typeof value === "number" && Number.isFinite(value) && value >= 1.3 && value <= 3;
}

function masteryFor(correctCount: number, reviewCount: number): number {
  return reviewCount === 0 ? 0 : Math.round((correctCount / reviewCount) * 100);
}

function reviewItemKey(lessonId: string, exerciseId: string): string {
  return `${lessonId}::${exerciseId}`;
}

function isObjectiveReviewItem(value: unknown): value is ObjectiveReviewItem {
  if (!isRecord(value)) return false;
  const item = value as Partial<ObjectiveReviewItem>;
  if (!isSafeId(item.lessonId) || !isSafeId(item.exerciseId) || !isTimestamp(item.firstSeenAt) ||
    !isTimestamp(item.lastReviewedAt) || !isTimestamp(item.nextReviewAt) || !isNonNegativeInteger(item.reviewCount) ||
    !isNonNegativeInteger(item.correctCount) || !isNonNegativeInteger(item.incorrectCount) || !isEase(item.ease) ||
    !isIntervalIndex(item.intervalIndex) || !isNonNegativeInteger(item.mastery) || item.mastery > 100 ||
    (item.lastResult !== "correct" && item.lastResult !== "incorrect")) {
    return false;
  }
  return item.reviewCount === item.correctCount + item.incorrectCount &&
    item.mastery === masteryFor(item.correctCount, item.reviewCount) &&
    Date.parse(item.firstSeenAt) <= Date.parse(item.lastReviewedAt);
}

function plusInterval(timestamp: string, intervalIndex: ReviewIntervalIndex): string {
  return new Date(Date.parse(timestamp) + REVIEW_INTERVALS_MS[intervalIndex]).toISOString();
}

function nextEase(current: number, result: ReviewResult): number {
  return Math.round(Math.min(3, Math.max(1.3, current + (result === "correct" ? 0.1 : -0.2))) * 10) / 10;
}

function nextInterval(current: ObjectiveReviewItem | undefined, result: ReviewResult): ReviewIntervalIndex {
  if (!current || result === "incorrect") return 0;
  return Math.min(current.intervalIndex + 1, REVIEW_INTERVALS_MS.length - 1) as ReviewIntervalIndex;
}

export function isObjectiveExerciseType(type: string): boolean {
  return ["multiple_choice", "fill_blank", "matching", "ordering", "reading", "listening", "selection", "completion"].includes(type);
}

export function reviewProgressKey(scope: ReviewScope): string {
  return `${REVIEW_PROGRESS_KEY_PREFIX}.${scope.learnerId}.${scope.language}.${scope.course}`;
}

export function emptyReviewProgress(scope: ReviewScope): ReviewProgress {
  return { version: REVIEW_PROGRESS_VERSION, ...scope, items: {} };
}

export function parseReviewProgress(serialized: string | null, scope: ReviewScope): ReviewProgress {
  if (!serialized) return emptyReviewProgress(scope);
  try {
    const candidate: unknown = JSON.parse(serialized);
    if (!isRecord(candidate) || candidate.version !== REVIEW_PROGRESS_VERSION || candidate.learnerId !== scope.learnerId ||
      candidate.language !== scope.language || candidate.course !== scope.course || !isLearnerId(candidate.learnerId) ||
      !isLanguageCode(candidate.language) || !isCourseLevel(candidate.course) || !isRecord(candidate.items) ||
      !Object.entries(candidate.items).every(([key, item]) => {
        if (!isObjectiveReviewItem(item)) return false;
        return key === reviewItemKey(item.lessonId, item.exerciseId);
      })) {
      return emptyReviewProgress(scope);
    }
    return candidate as unknown as ReviewProgress;
  } catch {
    return emptyReviewProgress(scope);
  }
}

export function loadReviewProgress(scope: ReviewScope, storage?: StorageLike): ReviewProgress {
  try {
    return parseReviewProgress((storage ?? browserStorage()).getItem(reviewProgressKey(scope)), scope);
  } catch {
    return emptyReviewProgress(scope);
  }
}

export function saveReviewProgress(progress: ReviewProgress, storage?: StorageLike): boolean {
  try {
    (storage ?? browserStorage()).setItem(reviewProgressKey(progress), JSON.stringify(progress));
    reportLocalStateAvailable();
    return true;
  } catch (error) {
    reportLocalStateIssue("write", error);
    return false;
  }
}

export function resetReviewProgress(scope: ReviewScope, storage?: StorageLike): boolean {
  try {
    (storage ?? browserStorage()).removeItem(reviewProgressKey(scope));
    reportLocalStateAvailable();
    return true;
  } catch (error) {
    reportLocalStateIssue("remove", error);
    return false;
  }
}

export function recordObjectiveReviewOutcome(progress: ReviewProgress, outcome: ObjectiveReviewOutcome): ReviewProgress {
  if (!isSafeId(outcome.lessonId) || !isSafeId(outcome.exerciseId) ||
    (outcome.result !== "correct" && outcome.result !== "incorrect") || !isTimestamp(outcome.reviewedAt)) {
    return progress;
  }
  const key = reviewItemKey(outcome.lessonId, outcome.exerciseId);
  const current = progress.items[key];
  if (current && Date.parse(outcome.reviewedAt) < Date.parse(current.lastReviewedAt)) return progress;
  const reviewCount = (current?.reviewCount ?? 0) + 1;
  const correctCount = (current?.correctCount ?? 0) + (outcome.result === "correct" ? 1 : 0);
  const incorrectCount = (current?.incorrectCount ?? 0) + (outcome.result === "incorrect" ? 1 : 0);
  const ease = nextEase(current?.ease ?? 2.5, outcome.result);
  const intervalIndex = nextInterval(current, outcome.result);
  const item: ObjectiveReviewItem = {
    lessonId: outcome.lessonId,
    exerciseId: outcome.exerciseId,
    firstSeenAt: current?.firstSeenAt ?? outcome.reviewedAt,
    lastReviewedAt: outcome.reviewedAt,
    reviewCount,
    correctCount,
    incorrectCount,
    ease,
    intervalIndex,
    mastery: masteryFor(correctCount, reviewCount),
    nextReviewAt: plusInterval(outcome.reviewedAt, intervalIndex),
    lastResult: outcome.result,
  };
  return { ...progress, items: { ...progress.items, [key]: item } };
}

export function selectReviewCandidates(
  candidates: readonly ReviewCandidate[],
  now: string,
  limit = MAX_REVIEW_SESSION_SIZE,
): readonly ReviewCandidate[] {
  if (!isTimestamp(now) || !Number.isInteger(limit) || limit < 1) return [];
  const seen = new Set<string>();
  return candidates
    .filter((candidate) => {
      if (seen.has(`${candidate.source}:${candidate.id}`)) return false;
      seen.add(`${candidate.source}:${candidate.id}`);
      return isTimestamp(candidate.dueAt) && candidate.dueAt <= now && Number.isInteger(candidate.order) && candidate.order >= 0 &&
        (candidate.priority === "recent_incorrect" || candidate.priority === "due");
    })
    .sort((left, right) => priorityValue(left.priority) - priorityValue(right.priority) ||
      left.dueAt.localeCompare(right.dueAt) || left.order - right.order ||
      left.source.localeCompare(right.source) || left.id.localeCompare(right.id))
    .slice(0, Math.min(limit, MAX_REVIEW_SESSION_SIZE));
}

function priorityValue(priority: ReviewCandidate["priority"]): number {
  return priority === "recent_incorrect" ? 0 : 1;
}

export function reviewItemId(lessonId: string, exerciseId: string): string {
  return reviewItemKey(lessonId, exerciseId);
}

export function isReviewItemDue(item: ObjectiveReviewItem, now: string): boolean {
  return isTimestamp(now) && item.nextReviewAt <= now;
}

export function isRecentIncorrect(item: ObjectiveReviewItem, now: string): boolean {
  return item.lastResult === "incorrect" && isTimestamp(now) &&
    Date.parse(item.lastReviewedAt) >= Date.parse(now) - 7 * 24 * 60 * 60_000;
}
