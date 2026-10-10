import type { StorageLike } from "./progress";
import { reportLocalStateAvailable, reportLocalStateIssue } from "./local-state";

export const LISTENING_LAB_PROGRESS_VERSION = 1 as const;
const KEY_PREFIX = "english-master.listening-lab.v1";

export type ListeningLabStage = "meaning_attempted" | "dictation_attempted" | "transcript_revealed" | "shadow_marked" | "final_listen_marked";
const stages: readonly ListeningLabStage[] = [
  "meaning_attempted", "dictation_attempted", "transcript_revealed", "shadow_marked", "final_listen_marked",
];

export interface ListeningLabScope {
  readonly learnerId: string;
  readonly language: "en";
  readonly course: "A1" | "A2" | "B1" | "B2" | "C1" | "C2";
}

export interface ListeningLabSessionProgress {
  readonly completedStages: readonly ListeningLabStage[];
  readonly meaningAttempts: number;
  readonly dictationAttempts: number;
  readonly updatedAt: string;
}

export interface ListeningLabProgress extends ListeningLabScope {
  readonly version: typeof LISTENING_LAB_PROGRESS_VERSION;
  readonly inventoryVersion: string;
  readonly sessions: Readonly<Record<string, ListeningLabSessionProgress>>;
}

function browserStorage(): StorageLike { return window.localStorage; }
function isSafeId(value: unknown): value is string { return typeof value === "string" && /^[a-z][a-z0-9-]*$/u.test(value); }
function isLearnerId(value: unknown): value is string { return typeof value === "string" && /^[a-z0-9-]{8,128}$/iu.test(value); }
function isCourse(value: unknown): value is ListeningLabScope["course"] { return typeof value === "string" && /^(A1|A2|B1|B2|C1|C2)$/u.test(value); }
function isTimestamp(value: unknown): value is string { return typeof value === "string" && /^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\.\d{3}Z$/u.test(value) && !Number.isNaN(Date.parse(value)); }
function isNonNegativeInteger(value: unknown): value is number { return typeof value === "number" && Number.isInteger(value) && value >= 0; }
function isStage(value: unknown): value is ListeningLabStage { return stages.includes(value as ListeningLabStage); }
function isSessionProgress(value: unknown): value is ListeningLabSessionProgress {
  if (!value || typeof value !== "object") return false;
  const candidate = value as Partial<ListeningLabSessionProgress>;
  return Array.isArray(candidate.completedStages) && candidate.completedStages.every(isStage) &&
    new Set(candidate.completedStages).size === candidate.completedStages.length &&
    candidate.completedStages.every((stage, index) => stages.indexOf(stage) === index) &&
    isNonNegativeInteger(candidate.meaningAttempts) && isNonNegativeInteger(candidate.dictationAttempts) && isTimestamp(candidate.updatedAt);
}

export function listeningLabProgressKey(scope: ListeningLabScope): string {
  return `${KEY_PREFIX}.${scope.learnerId}.${scope.language}.${scope.course}`;
}

export function emptyListeningLabProgress(scope: ListeningLabScope, inventoryVersion: string): ListeningLabProgress {
  return { version: LISTENING_LAB_PROGRESS_VERSION, ...scope, inventoryVersion, sessions: {} };
}

export function parseListeningLabProgress(serialized: string | null, scope: ListeningLabScope, inventoryVersion: string): ListeningLabProgress {
  if (!serialized) return emptyListeningLabProgress(scope, inventoryVersion);
  try {
    const value: unknown = JSON.parse(serialized);
    if (!value || typeof value !== "object") return emptyListeningLabProgress(scope, inventoryVersion);
    const candidate = value as Partial<ListeningLabProgress>;
    if (candidate.version !== LISTENING_LAB_PROGRESS_VERSION || candidate.learnerId !== scope.learnerId || candidate.language !== "en" ||
      candidate.course !== scope.course || !isLearnerId(candidate.learnerId) || !isCourse(candidate.course) || candidate.inventoryVersion !== inventoryVersion ||
      !candidate.sessions || typeof candidate.sessions !== "object" ||
      !Object.entries(candidate.sessions).every(([id, item]) => isSafeId(id) && isSessionProgress(item))) {
      return emptyListeningLabProgress(scope, inventoryVersion);
    }
    return candidate as ListeningLabProgress;
  } catch { return emptyListeningLabProgress(scope, inventoryVersion); }
}

export function loadListeningLabProgress(scope: ListeningLabScope, inventoryVersion: string, storage?: StorageLike): ListeningLabProgress {
  try { return parseListeningLabProgress((storage ?? browserStorage()).getItem(listeningLabProgressKey(scope)), scope, inventoryVersion); }
  catch { return emptyListeningLabProgress(scope, inventoryVersion); }
}

export function saveListeningLabProgress(progress: ListeningLabProgress, storage?: StorageLike): boolean {
  try {
    (storage ?? browserStorage()).setItem(listeningLabProgressKey(progress), JSON.stringify(progress));
    reportLocalStateAvailable();
    return true;
  } catch (error) {
    reportLocalStateIssue("write", error);
    return false;
  }
}

export function recordListeningLabStage(
  progress: ListeningLabProgress,
  sessionId: string,
  stage: ListeningLabStage,
  now: string,
): ListeningLabProgress {
  if (!isSafeId(sessionId) || !isStage(stage) || !isTimestamp(now)) return progress;
  const current = progress.sessions[sessionId] ?? { completedStages: [], meaningAttempts: 0, dictationAttempts: 0, updatedAt: now };
  const expected = stages[current.completedStages.length];
  if (stage !== expected) return progress;
  const nextStages = [...current.completedStages, stage];
  return {
    ...progress,
    sessions: {
      ...progress.sessions,
      [sessionId]: {
        completedStages: nextStages,
        meaningAttempts: current.meaningAttempts + (stage === "meaning_attempted" ? 1 : 0),
        dictationAttempts: current.dictationAttempts + (stage === "dictation_attempted" ? 1 : 0),
        updatedAt: now,
      },
    },
  };
}
