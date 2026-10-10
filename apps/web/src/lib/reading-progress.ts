import type { StorageLike } from "./progress";
import { reportLocalStateAvailable, reportLocalStateIssue } from "./local-state";

export const READING_PROGRESS_VERSION = 1 as const;
const KEY_PREFIX = "english-master.reading.v1";

export interface ReadingScope {
  readonly learnerId: string;
  readonly language: "en";
}

export interface ReadingBookmark {
  readonly firstOpenedAt: string;
  readonly lastOpenedAt: string;
}

export interface ReadingProgress extends ReadingScope {
  readonly version: typeof READING_PROGRESS_VERSION;
  readonly inventoryVersion: string;
  readonly bookmarks: Readonly<Record<string, ReadingBookmark>>;
}

function browserStorage(): StorageLike { return window.localStorage; }
function isSafeId(value: unknown): value is string { return typeof value === "string" && /^[a-z][a-z0-9-]*$/u.test(value); }
function isLearnerId(value: unknown): value is string { return typeof value === "string" && /^[a-z0-9-]{8,128}$/iu.test(value); }
function isTimestamp(value: unknown): value is string {
  return typeof value === "string" && /^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\.\d{3}Z$/u.test(value) && !Number.isNaN(Date.parse(value));
}
function isBookmark(value: unknown): value is ReadingBookmark {
  if (!value || typeof value !== "object") return false;
  const candidate = value as Partial<ReadingBookmark>;
  return isTimestamp(candidate.firstOpenedAt) && isTimestamp(candidate.lastOpenedAt) && candidate.firstOpenedAt <= candidate.lastOpenedAt;
}

export function readingProgressKey(scope: ReadingScope): string {
  return `${KEY_PREFIX}.${scope.learnerId}.${scope.language}`;
}

export function emptyReadingProgress(scope: ReadingScope, inventoryVersion: string): ReadingProgress {
  return { version: READING_PROGRESS_VERSION, ...scope, inventoryVersion, bookmarks: {} };
}

export function parseReadingProgress(serialized: string | null, scope: ReadingScope, inventoryVersion: string): ReadingProgress {
  if (!serialized) return emptyReadingProgress(scope, inventoryVersion);
  try {
    const value: unknown = JSON.parse(serialized);
    if (!value || typeof value !== "object") return emptyReadingProgress(scope, inventoryVersion);
    const candidate = value as Partial<ReadingProgress>;
    if (candidate.version !== READING_PROGRESS_VERSION || candidate.learnerId !== scope.learnerId || candidate.language !== "en" ||
      !isLearnerId(candidate.learnerId) || candidate.inventoryVersion !== inventoryVersion || !candidate.bookmarks ||
      typeof candidate.bookmarks !== "object" || !Object.entries(candidate.bookmarks).every(([id, bookmark]) => isSafeId(id) && isBookmark(bookmark))) {
      return emptyReadingProgress(scope, inventoryVersion);
    }
    return candidate as ReadingProgress;
  } catch { return emptyReadingProgress(scope, inventoryVersion); }
}

export function loadReadingProgress(scope: ReadingScope, inventoryVersion: string, storage?: StorageLike): ReadingProgress {
  try { return parseReadingProgress((storage ?? browserStorage()).getItem(readingProgressKey(scope)), scope, inventoryVersion); }
  catch { return emptyReadingProgress(scope, inventoryVersion); }
}

export function saveReadingProgress(progress: ReadingProgress, storage?: StorageLike): boolean {
  try {
    (storage ?? browserStorage()).setItem(readingProgressKey(progress), JSON.stringify(progress));
    reportLocalStateAvailable();
    return true;
  } catch (error) {
    reportLocalStateIssue("write", error);
    return false;
  }
}

export function toggleReadingBookmark(progress: ReadingProgress, readingId: string, now: string): ReadingProgress {
  if (!isSafeId(readingId) || !isTimestamp(now)) return progress;
  const current = progress.bookmarks[readingId];
  if (current) {
    const { [readingId]: _removed, ...bookmarks } = progress.bookmarks;
    return { ...progress, bookmarks };
  }
  return { ...progress, bookmarks: { ...progress.bookmarks, [readingId]: { firstOpenedAt: now, lastOpenedAt: now } } };
}
