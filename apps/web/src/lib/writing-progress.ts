import type { Band } from "@/content/types";
import { reportLocalStateAvailable, reportLocalStateIssue } from "./local-state";

export const WRITING_PROGRESS_VERSION = 1 as const;
export const WRITING_DRAFT_LIMIT = 12_000;
const keyPrefix = "english-master.writing.v1";
const bands = new Set<Band>(["A1", "A2", "B1", "B2", "C1", "C2"]);

export interface WritingScope {
  readonly learnerId: string;
  readonly language: "en";
}

export interface WritingProtocolReference {
  readonly id: string;
  readonly lessonId: string;
  readonly band: Band;
}

export interface LocalWritingAttempt {
  readonly id: string;
  readonly protocolId: string;
  readonly lessonId: string;
  readonly band: Band;
  readonly draft: string;
  readonly createdAt: string;
  readonly updatedAt: string;
  readonly status: "DRAFT" | "REVISED";
  readonly parentAttemptId?: string;
}

export interface WritingProgress extends WritingScope {
  readonly version: typeof WRITING_PROGRESS_VERSION;
  readonly inventoryVersion: string;
  readonly attempts: Readonly<Record<string, LocalWritingAttempt>>;
}

export interface StorageLike {
  getItem(key: string): string | null;
  setItem(key: string, value: string): void;
}

function browserStorage(): StorageLike { return window.localStorage; }
function isRecord(value: unknown): value is Record<string, unknown> { return Boolean(value) && typeof value === "object" && !Array.isArray(value); }
function isSafeId(value: unknown): value is string { return typeof value === "string" && /^[a-z][a-z0-9-]*$/u.test(value); }
function isTimestamp(value: unknown): value is string {
  return typeof value === "string" && /^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\.\d{3}Z$/u.test(value) && !Number.isNaN(Date.parse(value));
}
function isDraft(value: unknown): value is string { return typeof value === "string" && value.length <= WRITING_DRAFT_LIMIT; }
function knownById(protocols: readonly WritingProtocolReference[]): ReadonlyMap<string, WritingProtocolReference> {
  return new Map(protocols.map((protocol) => [protocol.id, protocol]));
}
function primaryAttemptId(protocolId: string): string { return `writing-${protocolId}`; }
function nextRevisionId(attempts: Readonly<Record<string, LocalWritingAttempt>>, parentId: string): string {
  let sequence = 1;
  while (attempts[`${parentId}-revision-${sequence}`]) sequence += 1;
  return `${parentId}-revision-${sequence}`;
}
function isAttempt(value: unknown, protocols: ReadonlyMap<string, WritingProtocolReference>): value is LocalWritingAttempt {
  if (!isRecord(value) || !isSafeId(value.id) || !isSafeId(value.protocolId) || !isSafeId(value.lessonId) || !bands.has(value.band as Band) ||
    !isDraft(value.draft) || !isTimestamp(value.createdAt) || !isTimestamp(value.updatedAt) ||
    (value.status !== "DRAFT" && value.status !== "REVISED") ||
    (value.parentAttemptId !== undefined && !isSafeId(value.parentAttemptId))) return false;
  const protocol = protocols.get(value.protocolId);
  return Boolean(protocol && protocol.lessonId === value.lessonId && protocol.band === value.band);
}

export function writingProgressKey(scope: WritingScope): string {
  return `${keyPrefix}.${scope.learnerId}.${scope.language}`;
}

export function emptyWritingProgress(scope: WritingScope, inventoryVersion: string): WritingProgress {
  return { version: WRITING_PROGRESS_VERSION, ...scope, inventoryVersion, attempts: {} };
}

export function parseWritingProgress(
  serialized: string | null,
  scope: WritingScope,
  inventoryVersion: string,
  protocols: readonly WritingProtocolReference[],
): WritingProgress | undefined {
  if (!serialized) return undefined;
  try {
    const value: unknown = JSON.parse(serialized);
    if (!isRecord(value) || value.version !== WRITING_PROGRESS_VERSION || value.learnerId !== scope.learnerId ||
      value.language !== scope.language || value.inventoryVersion !== inventoryVersion || !isRecord(value.attempts)) return undefined;
    const references = knownById(protocols);
    if (!Object.entries(value.attempts).every(([id, attempt]) => id === (attempt as LocalWritingAttempt)?.id && isAttempt(attempt, references))) return undefined;
    const attempts = value.attempts as Readonly<Record<string, LocalWritingAttempt>>;
    for (const attempt of Object.values(attempts)) {
      if (attempt.parentAttemptId && !attempts[attempt.parentAttemptId]) return undefined;
    }
    return { version: WRITING_PROGRESS_VERSION, ...scope, inventoryVersion, attempts };
  } catch { return undefined; }
}

export function loadWritingProgress(
  scope: WritingScope,
  inventoryVersion: string,
  protocols: readonly WritingProtocolReference[],
  storage?: StorageLike,
): WritingProgress {
  try { return parseWritingProgress((storage ?? browserStorage()).getItem(writingProgressKey(scope)), scope, inventoryVersion, protocols) ?? emptyWritingProgress(scope, inventoryVersion); }
  catch { return emptyWritingProgress(scope, inventoryVersion); }
}

export function saveWritingProgress(progress: WritingProgress, storage?: StorageLike): boolean {
  try {
    (storage ?? browserStorage()).setItem(writingProgressKey(progress), JSON.stringify(progress));
    reportLocalStateAvailable();
    return true;
  } catch (error) {
    reportLocalStateIssue("write", error);
    return false;
  }
}

export function getLatestWritingAttempt(progress: WritingProgress, protocolId: string): LocalWritingAttempt | undefined {
  return Object.values(progress.attempts)
    .filter((attempt) => attempt.protocolId === protocolId)
    .sort((left, right) => right.updatedAt.localeCompare(left.updatedAt) || right.id.localeCompare(left.id))[0];
}

export function saveWritingDraft(
  progress: WritingProgress,
  protocol: WritingProtocolReference,
  draft: string,
  now: string,
  attemptId = getLatestWritingAttempt(progress, protocol.id)?.id ?? primaryAttemptId(protocol.id),
): WritingProgress {
  if (!isDraft(draft) || !isTimestamp(now) || !isSafeId(attemptId)) return progress;
  const existing = progress.attempts[attemptId];
  if (existing && (existing.protocolId !== protocol.id || existing.lessonId !== protocol.lessonId || existing.band !== protocol.band)) return progress;
  const attempt: LocalWritingAttempt = existing
    ? { ...existing, draft, updatedAt: now }
    : { id: attemptId, protocolId: protocol.id, lessonId: protocol.lessonId, band: protocol.band, draft, createdAt: now, updatedAt: now, status: "DRAFT" };
  return { ...progress, attempts: { ...progress.attempts, [attempt.id]: attempt } };
}

export function forkWritingRevision(progress: WritingProgress, attemptId: string, now: string): WritingProgress {
  const parent = progress.attempts[attemptId];
  if (!parent || !isTimestamp(now)) return progress;
  const id = nextRevisionId(progress.attempts, parent.id);
  const revision: LocalWritingAttempt = { ...parent, id, createdAt: now, updatedAt: now, status: "REVISED", parentAttemptId: parent.id };
  return { ...progress, attempts: { ...progress.attempts, [id]: revision } };
}

export function importLegacyWritingDraft(
  progress: WritingProgress,
  protocol: WritingProtocolReference,
  draft: string | undefined,
  now: string,
): WritingProgress {
  if (!draft || getLatestWritingAttempt(progress, protocol.id)) return progress;
  return saveWritingDraft(progress, protocol, draft, now, primaryAttemptId(protocol.id));
}
