import type { LanguageCode } from "@/content/types";
import type { StorageLike } from "@/lib/progress";
import { reportLocalStateAvailable, reportLocalStateIssue } from "./local-state";

export const DICTIONARY_PROGRESS_VERSION = 1 as const;
const KEY_PREFIX = "english-master.dictionary.v1";

export type DictionaryStatus = "learned" | "learning" | "weak" | "not_learned";

export interface DictionaryProgressScope {
  readonly learnerId: string;
  readonly language: LanguageCode;
}

export interface DictionaryEntryProgress {
  readonly startedAt: string;
  readonly correctCount: number;
  readonly incorrectCount: number;
  readonly lastAttemptAt?: string;
}

export interface DictionaryProgress extends DictionaryProgressScope {
  readonly version: typeof DICTIONARY_PROGRESS_VERSION;
  readonly inventoryVersion: string;
  readonly entries: Readonly<Record<string, DictionaryEntryProgress>>;
}

function browserStorage(): StorageLike { return window.localStorage; }
function isRecord(value: unknown): value is Record<string, unknown> { return Boolean(value) && typeof value === "object" && !Array.isArray(value); }
function validLearnerId(value: unknown): value is string { return typeof value === "string" && /^[a-z0-9-]{8,128}$/iu.test(value); }
function validTimestamp(value: unknown): value is string { return typeof value === "string" && /^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\.\d{3}Z$/u.test(value) && !Number.isNaN(Date.parse(value)); }
function validEntryId(value: unknown): value is string { return typeof value === "string" && /^[a-z][a-z0-9-]*$/u.test(value); }
function validCount(value: unknown): value is number { return Number.isInteger(value) && typeof value === "number" && value >= 0; }

export function dictionaryProgressKey(scope: DictionaryProgressScope): string {
  return `${KEY_PREFIX}.${scope.learnerId}.${scope.language}`;
}

export function emptyDictionaryProgress(scope: DictionaryProgressScope, inventoryVersion: string): DictionaryProgress {
  return { version: DICTIONARY_PROGRESS_VERSION, ...scope, inventoryVersion, entries: {} };
}

export function parseDictionaryProgress(serialized: string | null, scope: DictionaryProgressScope, inventoryVersion: string, knownEntryIds: readonly string[]): DictionaryProgress {
  const empty = emptyDictionaryProgress(scope, inventoryVersion);
  if (!serialized) return empty;
  try {
    const candidate: unknown = JSON.parse(serialized);
    if (!isRecord(candidate) || candidate.version !== DICTIONARY_PROGRESS_VERSION || candidate.learnerId !== scope.learnerId ||
      candidate.language !== scope.language || candidate.inventoryVersion !== inventoryVersion || !validLearnerId(candidate.learnerId) ||
      !isRecord(candidate.entries)) return empty;
    const allowed = new Set(knownEntryIds);
    const entries: Record<string, DictionaryEntryProgress> = {};
    for (const [id, value] of Object.entries(candidate.entries)) {
      if (!allowed.has(id) || !validEntryId(id) || !isRecord(value) || !validTimestamp(value.startedAt) ||
        !validCount(value.correctCount) || !validCount(value.incorrectCount) ||
        (value.lastAttemptAt !== undefined && !validTimestamp(value.lastAttemptAt))) continue;
      entries[id] = {
        startedAt: value.startedAt,
        correctCount: value.correctCount,
        incorrectCount: value.incorrectCount,
        ...(validTimestamp(value.lastAttemptAt) ? { lastAttemptAt: value.lastAttemptAt } : {}),
      };
    }
    return { version: DICTIONARY_PROGRESS_VERSION, ...scope, inventoryVersion, entries };
  } catch { return empty; }
}

export function loadDictionaryProgress(scope: DictionaryProgressScope, inventoryVersion: string, knownEntryIds: readonly string[], storage?: StorageLike): DictionaryProgress {
  try { return parseDictionaryProgress((storage ?? browserStorage()).getItem(dictionaryProgressKey(scope)), scope, inventoryVersion, knownEntryIds); }
  catch { return emptyDictionaryProgress(scope, inventoryVersion); }
}

export function saveDictionaryProgress(progress: DictionaryProgress, storage?: StorageLike): boolean {
  try {
    (storage ?? browserStorage()).setItem(dictionaryProgressKey(progress), JSON.stringify(progress));
    reportLocalStateAvailable();
    return true;
  } catch (error) {
    reportLocalStateIssue("write", error);
    return false;
  }
}

export function startDictionaryEntry(progress: DictionaryProgress, entryId: string, now: string): DictionaryProgress {
  if (!validEntryId(entryId) || !validTimestamp(now) || progress.entries[entryId]) return progress;
  return { ...progress, entries: { ...progress.entries, [entryId]: { startedAt: now, correctCount: 0, incorrectCount: 0 } } };
}

export function recordDictionaryOutcome(progress: DictionaryProgress, entryId: string, correct: boolean, now: string): DictionaryProgress {
  const entry = progress.entries[entryId];
  if (!entry || !validTimestamp(now)) return progress;
  return {
    ...progress,
    entries: {
      ...progress.entries,
      [entryId]: {
        ...entry,
        correctCount: entry.correctCount + (correct ? 1 : 0),
        incorrectCount: entry.incorrectCount + (correct ? 0 : 1),
        lastAttemptAt: now,
      },
    },
  };
}

export function dictionaryStatus(entry: DictionaryEntryProgress | undefined): DictionaryStatus {
  if (!entry) return "not_learned";
  if (entry.incorrectCount > 0) return "weak";
  return entry.correctCount >= 3 ? "learned" : "learning";
}
