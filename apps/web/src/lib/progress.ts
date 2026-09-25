import type { LanguageCode } from "@/content/types";

export const PROGRESS_VERSION = 1 as const;
const KEY_PREFIX = "english-master.progress.v1";

export interface LessonProgress {
  readonly completed: boolean;
  readonly attempts: Readonly<Record<string, number>>;
  readonly protocols: Readonly<Partial<Record<"listening" | "speaking" | "pronunciation" | "writing", boolean>>>;
  readonly drafts: Readonly<Partial<Record<"writing", string>>>;
}

export interface LanguageProgress {
  readonly version: typeof PROGRESS_VERSION;
  readonly language: LanguageCode;
  readonly lessons: Readonly<Record<string, LessonProgress>>;
}

export interface StorageLike {
  getItem(key: string): string | null;
  setItem(key: string, value: string): void;
  removeItem(key: string): void;
}

export function progressKey(language: LanguageCode): string {
  return `${KEY_PREFIX}.${language}`;
}

export function emptyProgress(language: LanguageCode): LanguageProgress {
  return { version: PROGRESS_VERSION, language, lessons: {} };
}

const modalities = new Set(["listening", "speaking", "pronunciation", "writing"]);

function isBooleanRecord(value: unknown): value is Record<string, boolean> {
  return Boolean(value) && typeof value === "object" && Object.entries(value).every(
    ([key, item]) => modalities.has(key) && typeof item === "boolean",
  );
}

function isWritingDraftRecord(value: unknown): value is Record<string, string> {
  return Boolean(value) && typeof value === "object" && Object.entries(value).every(
    ([key, item]) => key === "writing" && typeof item === "string",
  );
}

function isLessonProgress(value: unknown): value is LessonProgress {
  if (!value || typeof value !== "object") return false;
  const item = value as Partial<LessonProgress>;
  return (
    typeof item.completed === "boolean" &&
    Boolean(item.attempts) &&
    typeof item.attempts === "object" &&
    Object.values(item.attempts).every((attempt) => Number.isInteger(attempt) && attempt >= 0) &&
    isBooleanRecord(item.protocols) &&
    isWritingDraftRecord(item.drafts)
  );
}

function isSafeLessonId(lessonId: string): boolean {
  return /^[a-z][a-z0-9-]*$/u.test(lessonId);
}

export function parseProgress(serialized: string | null, language: LanguageCode): LanguageProgress {
  if (!serialized) return emptyProgress(language);
  try {
    const value: unknown = JSON.parse(serialized);
    if (!value || typeof value !== "object") return emptyProgress(language);
    const candidate = value as Partial<LanguageProgress>;
    if (candidate.version !== PROGRESS_VERSION || candidate.language !== language || !candidate.lessons || typeof candidate.lessons !== "object") {
      return emptyProgress(language);
    }
    if (!Object.entries(candidate.lessons).every(([lessonId, item]) => isSafeLessonId(lessonId) && isLessonProgress(item))) {
      return emptyProgress(language);
    }
    return candidate as LanguageProgress;
  } catch {
    return emptyProgress(language);
  }
}

export function loadProgress(language: LanguageCode, storage?: StorageLike): LanguageProgress {
  try {
    const target = storage ?? window.localStorage;
    return parseProgress(target.getItem(progressKey(language)), language);
  } catch {
    return emptyProgress(language);
  }
}

export function saveProgress(progress: LanguageProgress, storage?: StorageLike): boolean {
  try {
    const target = storage ?? window.localStorage;
    target.setItem(progressKey(progress.language), JSON.stringify(progress));
    return true;
  } catch {
    return false;
  }
}

export function resetProgress(language: LanguageCode, storage?: StorageLike): boolean {
  try {
    const target = storage ?? window.localStorage;
    target.removeItem(progressKey(language));
    return true;
  } catch {
    return false;
  }
}

export function updateLessonProgress(
  progress: LanguageProgress,
  lessonId: string,
  update: Partial<LessonProgress>,
): LanguageProgress {
  const current = progress.lessons[lessonId] ?? {
    completed: false,
    attempts: {},
    protocols: {},
    drafts: {},
  };
  return {
    ...progress,
    lessons: {
      ...progress.lessons,
      [lessonId]: {
        completed: update.completed ?? current.completed,
        attempts: update.attempts ?? current.attempts,
        protocols: update.protocols ?? current.protocols,
        drafts: update.drafts ?? current.drafts,
      },
    },
  };
}
