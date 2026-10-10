import type { CourseLevel, LanguageCode } from "@/content/types";
import { reportLocalStateAvailable, reportLocalStateIssue } from "./local-state";

export const LEARNER_STORAGE_VERSION = 2 as const;
export const PROGRESS_VERSION = 2 as const;
const PROFILE_KEY = "english-master.learner.v2.profile";
const PROGRESS_KEY_PREFIX = "english-master.progress.v2";

export type ExerciseResult = "correct" | "incorrect" | "self_practice";

export interface ExerciseProgress {
  readonly lastResult: ExerciseResult;
  readonly completed: boolean;
}

export interface ExerciseRunnerState {
  readonly currentExerciseId?: string;
  readonly finished: boolean;
  readonly exercises: Readonly<Record<string, ExerciseProgress>>;
}

export interface LessonProgress {
  readonly completed: boolean;
  readonly attempts: Readonly<Record<string, number>>;
  readonly protocols: Readonly<
    Partial<Record<"listening" | "speaking" | "pronunciation" | "writing", boolean>>
  >;
  readonly drafts: Readonly<Partial<Record<"writing", string>>>;
  readonly lastAccessedAt?: string;
  readonly exerciseRunner?: ExerciseRunnerState;
}

export interface ConceptProgress {
  readonly reviews: number;
}

export interface LocalLearner {
  readonly version: typeof LEARNER_STORAGE_VERSION;
  readonly learnerId: string;
  readonly activeLanguage: LanguageCode;
}

export interface CourseScope {
  readonly learnerId: string;
  readonly language: LanguageCode;
  readonly course: CourseLevel;
}

export interface CourseProgress extends CourseScope {
  readonly version: typeof PROGRESS_VERSION;
  readonly lastLessonId?: string;
  readonly lessons: Readonly<Record<string, LessonProgress>>;
  readonly concepts: Readonly<Record<string, ConceptProgress>>;
}

export interface CourseLessonInventory {
  readonly lessonId: string;
  readonly unitId: string;
}

export interface UnitProgressSummary {
  readonly unitId: string;
  readonly completedLessons: number;
  readonly totalLessons: number;
}

export interface CourseProgressSummary {
  readonly completedLessons: number;
  readonly totalLessons: number;
  readonly currentLessonId?: string;
  readonly lastAccessedLessonId?: string;
  readonly lastAccessedAt?: string;
  readonly units: readonly UnitProgressSummary[];
}

export interface StorageLike {
  getItem(key: string): string | null;
  setItem(key: string, value: string): void;
  removeItem(key: string): void;
}

function browserStorage(): StorageLike {
  return window.localStorage;
}

function createLearnerId(): string {
  if (typeof crypto !== "undefined" && typeof crypto.randomUUID === "function") {
    return crypto.randomUUID();
  }
  return `local-${Date.now().toString(36)}-${Math.random().toString(36).slice(2, 12)}`;
}

function isLanguageCode(value: unknown): value is LanguageCode {
  return value === "en" || value === "de";
}

function isCourseLevel(value: unknown): value is CourseLevel {
  return typeof value === "string" && /^(A1|A2|B1|B2|C1|C2)$/u.test(value);
}

function isLearnerId(value: unknown): value is string {
  return typeof value === "string" && /^[a-z0-9-]{8,128}$/iu.test(value);
}

function isSafeRecordId(value: string): boolean {
  return /^[a-z][a-z0-9-]*$/u.test(value);
}

function isTimestamp(value: unknown): value is string {
  return typeof value === "string" &&
    /^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\.\d{3}Z$/u.test(value) &&
    !Number.isNaN(Date.parse(value));
}

const modalities = new Set(["listening", "speaking", "pronunciation", "writing"]);
const exerciseResults = new Set<ExerciseResult>(["correct", "incorrect", "self_practice"]);

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

function isExerciseProgress(value: unknown): value is ExerciseProgress {
  if (!value || typeof value !== "object") return false;
  const item = value as Partial<ExerciseProgress>;
  return exerciseResults.has(item.lastResult as ExerciseResult) && typeof item.completed === "boolean";
}

function isExerciseRunnerState(value: unknown): value is ExerciseRunnerState {
  if (!value || typeof value !== "object") return false;
  const item = value as Partial<ExerciseRunnerState>;
  return (
    typeof item.finished === "boolean" &&
    (item.currentExerciseId === undefined ||
      (typeof item.currentExerciseId === "string" && isSafeRecordId(item.currentExerciseId))) &&
    Boolean(item.exercises) &&
    typeof item.exercises === "object" &&
    Object.entries(item.exercises).every(
      ([exerciseId, exercise]) => isSafeRecordId(exerciseId) && isExerciseProgress(exercise),
    )
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
    isWritingDraftRecord(item.drafts) &&
    (item.lastAccessedAt === undefined || isTimestamp(item.lastAccessedAt)) &&
    (item.exerciseRunner === undefined || isExerciseRunnerState(item.exerciseRunner))
  );
}

function isConceptProgress(value: unknown): value is ConceptProgress {
  return Boolean(value) && typeof value === "object" &&
    Number.isInteger((value as ConceptProgress).reviews) &&
    (value as ConceptProgress).reviews >= 0;
}

function emptyLessonProgress(): LessonProgress {
  return { completed: false, attempts: {}, protocols: {}, drafts: {} };
}

export function learnerProfileKey(): string {
  return PROFILE_KEY;
}

export function progressKey(scope: CourseScope): string {
  return `${PROGRESS_KEY_PREFIX}.${scope.learnerId}.${scope.language}.${scope.course}`;
}

export function emptyProgress(scope: CourseScope): CourseProgress {
  return { version: PROGRESS_VERSION, ...scope, lessons: {}, concepts: {} };
}

export function parseLearner(serialized: string | null): LocalLearner | undefined {
  if (!serialized) return undefined;
  try {
    const value: unknown = JSON.parse(serialized);
    if (!value || typeof value !== "object") return undefined;
    const learner = value as Partial<LocalLearner>;
    if (
      learner.version !== LEARNER_STORAGE_VERSION ||
      !isLearnerId(learner.learnerId) ||
      !isLanguageCode(learner.activeLanguage)
    ) {
      return undefined;
    }
    return learner as LocalLearner;
  } catch {
    return undefined;
  }
}

export function loadLearner(storage?: StorageLike): LocalLearner {
  try {
    const target = storage ?? browserStorage();
    const existing = parseLearner(target.getItem(learnerProfileKey()));
    if (existing) return existing;
    const learner: LocalLearner = {
      version: LEARNER_STORAGE_VERSION,
      learnerId: createLearnerId(),
      activeLanguage: "en",
    };
    target.setItem(learnerProfileKey(), JSON.stringify(learner));
    reportLocalStateAvailable();
    return learner;
  } catch (error) {
    reportLocalStateIssue("write", error);
    return { version: LEARNER_STORAGE_VERSION, learnerId: "local-unavailable", activeLanguage: "en" };
  }
}

export function setActiveLanguage(
  learner: LocalLearner,
  activeLanguage: LanguageCode,
  storage?: StorageLike,
): LocalLearner {
  const next: LocalLearner = { ...learner, activeLanguage };
  try {
    (storage ?? browserStorage()).setItem(learnerProfileKey(), JSON.stringify(next));
    reportLocalStateAvailable();
  } catch (error) {
    reportLocalStateIssue("write", error);
  }
  return next;
}

export function parseProgress(serialized: string | null, scope: CourseScope): CourseProgress {
  if (!serialized) return emptyProgress(scope);
  try {
    const value: unknown = JSON.parse(serialized);
    if (!value || typeof value !== "object") return emptyProgress(scope);
    const candidate = value as Partial<CourseProgress>;
    if (
      candidate.version !== PROGRESS_VERSION ||
      candidate.learnerId !== scope.learnerId ||
      candidate.language !== scope.language ||
      candidate.course !== scope.course ||
      !candidate.lessons || typeof candidate.lessons !== "object" ||
      !candidate.concepts || typeof candidate.concepts !== "object" ||
      (candidate.lastLessonId !== undefined &&
        (typeof candidate.lastLessonId !== "string" || !isSafeRecordId(candidate.lastLessonId))) ||
      !Object.entries(candidate.lessons).every(
        ([lessonId, item]) => isSafeRecordId(lessonId) && isLessonProgress(item),
      ) ||
      !Object.entries(candidate.concepts).every(
        ([conceptId, item]) => isSafeRecordId(conceptId) && isConceptProgress(item),
      )
    ) {
      return emptyProgress(scope);
    }
    return candidate as CourseProgress;
  } catch {
    return emptyProgress(scope);
  }
}

export function loadProgress(scope: CourseScope, storage?: StorageLike): CourseProgress {
  try {
    const target = storage ?? browserStorage();
    return parseProgress(target.getItem(progressKey(scope)), scope);
  } catch {
    return emptyProgress(scope);
  }
}

export function saveProgress(progress: CourseProgress, storage?: StorageLike): boolean {
  try {
    (storage ?? browserStorage()).setItem(progressKey(progress), JSON.stringify(progress));
    reportLocalStateAvailable();
    return true;
  } catch (error) {
    reportLocalStateIssue("write", error);
    return false;
  }
}

export function resetProgress(scope: CourseScope, storage?: StorageLike): boolean {
  try {
    (storage ?? browserStorage()).removeItem(progressKey(scope));
    reportLocalStateAvailable();
    return true;
  } catch (error) {
    reportLocalStateIssue("remove", error);
    return false;
  }
}

export function updateLessonProgress(
  progress: CourseProgress,
  lessonId: string,
  update: Partial<LessonProgress>,
): CourseProgress {
  if (!isSafeRecordId(lessonId)) return progress;
  const current = progress.lessons[lessonId] ?? emptyLessonProgress();
  return {
    ...progress,
    lastLessonId: lessonId,
    lessons: {
      ...progress.lessons,
      [lessonId]: {
        completed: update.completed ?? current.completed,
        attempts: update.attempts ?? current.attempts,
        protocols: update.protocols ?? current.protocols,
        drafts: update.drafts ?? current.drafts,
        lastAccessedAt: update.lastAccessedAt ?? current.lastAccessedAt,
        exerciseRunner: update.exerciseRunner ?? current.exerciseRunner,
      },
    },
  };
}

export function resetExerciseRunner(progress: CourseProgress, lessonId: string): CourseProgress {
  if (!isSafeRecordId(lessonId) || !progress.lessons[lessonId]) return progress;
  const { exerciseRunner: _exerciseRunner, ...lesson } = progress.lessons[lessonId];
  return {
    ...progress,
    lastLessonId: lessonId,
    lessons: { ...progress.lessons, [lessonId]: lesson },
  };
}

export function updateConceptProgress(
  progress: CourseProgress,
  conceptId: string,
  reviews: number,
): CourseProgress {
  if (!isSafeRecordId(conceptId) || !Number.isInteger(reviews) || reviews < 0) return progress;
  return { ...progress, concepts: { ...progress.concepts, [conceptId]: { reviews } } };
}

export function summarizeCourseProgress(
  progress: CourseProgress,
  inventory: readonly CourseLessonInventory[],
): CourseProgressSummary {
  const lessonIds = new Set(inventory.map((lesson) => lesson.lessonId));
  const unitTotals = new Map<string, { completedLessons: number; totalLessons: number }>();
  let completedLessons = 0;
  let lastAccessedLessonId: string | undefined;
  let lastAccessedAt: string | undefined;

  for (const lesson of inventory) {
    const unit = unitTotals.get(lesson.unitId) ?? { completedLessons: 0, totalLessons: 0 };
    const stored = progress.lessons[lesson.lessonId];
    unit.totalLessons += 1;
    if (stored?.completed) {
      completedLessons += 1;
      unit.completedLessons += 1;
    }
    unitTotals.set(lesson.unitId, unit);

    if (stored?.lastAccessedAt && (!lastAccessedAt || stored.lastAccessedAt > lastAccessedAt)) {
      lastAccessedLessonId = lesson.lessonId;
      lastAccessedAt = stored.lastAccessedAt;
    }
  }

  return {
    completedLessons,
    totalLessons: inventory.length,
    currentLessonId: progress.lastLessonId && lessonIds.has(progress.lastLessonId)
      ? progress.lastLessonId
      : undefined,
    lastAccessedLessonId,
    lastAccessedAt,
    units: [...unitTotals.entries()].map(([unitId, counts]) => ({ unitId, ...counts })),
  };
}

export function resumeLessonId(
  progress: CourseProgress,
  orderedLessonIds: readonly string[],
): string | undefined {
  if (progress.lastLessonId && orderedLessonIds.includes(progress.lastLessonId)) {
    return progress.lastLessonId;
  }
  return orderedLessonIds.find((lessonId) => !progress.lessons[lessonId]?.completed) ?? orderedLessonIds[0];
}
