import type { Band, LanguageCode } from "@/content/types";
import type { StorageLike } from "@/lib/progress";
import { reportLocalStateAvailable, reportLocalStateIssue } from "@/lib/local-state";

export const TUTOR_PREFERENCES_VERSION = 1 as const;
const TUTOR_PREFERENCES_KEY_PREFIX = "english-master.tutor-preferences.v1";
const MAX_CONTEXT_ITEMS = 5;

export const BAND_ORDER = ["A1", "A2", "B1", "B2", "C1", "C2"] as const;
export const TUTOR_GOALS = [
  "conversation", "vocabulary", "grammar", "listening",
  "speaking", "pronunciation", "reading", "writing",
] as const;

export type TutorGoal = (typeof TUTOR_GOALS)[number];
export const DAILY_ALLOCATION_OPTIONS = [15, 30, 45, 60, 90] as const;
export type DailyAllocationMinutes = (typeof DAILY_ALLOCATION_OPTIONS)[number];
export type TutorVocabularyState = "learning" | "reviewing" | "mastered";
export type TutorGrammarState = "practising" | "reviewing" | "locally_consolidated";
export type TutorReviewPriority = "recent_incorrect" | "due";

export interface TutorPreferenceScope {
  readonly learnerId: string;
  readonly language: LanguageCode;
}

/** Learner choices only. Bands in this record are not assessment results. */
export interface TutorPreferences extends TutorPreferenceScope {
  readonly version: typeof TUTOR_PREFERENCES_VERSION;
  readonly currentBand?: Band;
  readonly targetBand?: Band;
  readonly dailyAllocationMinutes?: DailyAllocationMinutes;
  readonly goals: readonly TutorGoal[];
}

/** Safe, catalog-derived data. Callers must supply labels, never record IDs or learner text. */
export interface TutorLessonLabelSource {
  readonly title: string;
  readonly recencyOrder: number;
}

export interface TutorVocabularyLabelSource {
  readonly label: string;
  readonly state: TutorVocabularyState;
  readonly order: number;
}

export interface TutorGrammarLabelSource {
  readonly label: string;
  readonly state: TutorGrammarState;
  readonly order: number;
}

export interface TutorOutcomePatternSource {
  readonly label: string;
  readonly incorrectOutcomes: number;
  readonly reviewCount: number;
  readonly recentIncorrect: boolean;
  readonly repeatedIncorrect: boolean;
  readonly order: number;
}

export interface TutorReviewItemSource {
  readonly label: string;
  readonly source: "objective_activity" | "vocabulary" | "grammar";
  readonly priority: TutorReviewPriority;
  readonly order: number;
}

export interface TutorContextSources {
  readonly language: LanguageCode;
  readonly course?: Band;
  readonly recentLessons?: readonly TutorLessonLabelSource[];
  readonly vocabulary?: readonly TutorVocabularyLabelSource[];
  readonly grammar?: readonly TutorGrammarLabelSource[];
  readonly outcomePatterns?: readonly TutorOutcomePatternSource[];
  readonly reviewItems?: readonly TutorReviewItemSource[];
}

export interface TutorContext {
  readonly version: 1;
  readonly language: LanguageCode;
  readonly selfReportedCurrentBand?: Band;
  readonly aspirationalTargetBand?: Band;
  readonly course?: Band;
  readonly goals: readonly TutorGoal[];
  readonly recentLessonTitles: readonly string[];
  readonly vocabulary: readonly Readonly<{ label: string; state: TutorVocabularyState }>[];
  readonly grammar?: readonly Readonly<{ label: string; state: TutorGrammarState }>[];
  readonly objectiveActivityOutcomePatterns: readonly Readonly<{
    label: string;
    incorrectOutcomes: number;
    reviewCount: number;
    recentIncorrect: boolean;
    repeatedIncorrect: boolean;
  }>[];
  readonly reviewItems: readonly Readonly<{
    label: string;
    source: "objective_activity" | "vocabulary" | "grammar";
    priority: TutorReviewPriority;
  }>[];
  readonly limitations: readonly [
    "Bands are learner-reported preferences, not proficiency or diagnostic results.",
    "Local activity states and outcomes do not establish ability, mastery, or a linguistic weakness.",
  ];
}

function browserStorage(): StorageLike { return window.localStorage; }
function isRecord(value: unknown): value is Record<string, unknown> {
  return Boolean(value) && typeof value === "object" && !Array.isArray(value);
}
function isLearnerId(value: unknown): value is string {
  return typeof value === "string" && /^[a-z0-9-]{8,128}$/iu.test(value);
}
function isLanguage(value: unknown): value is LanguageCode { return value === "en" || value === "de"; }
function isBand(value: unknown): value is Band {
  return typeof value === "string" && (BAND_ORDER as readonly string[]).includes(value);
}
function isGoal(value: unknown): value is TutorGoal {
  return typeof value === "string" && (TUTOR_GOALS as readonly string[]).includes(value);
}
function isDailyAllocationMinutes(value: unknown): value is DailyAllocationMinutes {
  return typeof value === "number" && (DAILY_ALLOCATION_OPTIONS as readonly number[]).includes(value);
}
function isGoalAvailable(goal: TutorGoal, language: LanguageCode): boolean {
  return language === "en" || goal !== "grammar";
}
function canonicalGoals(goals: readonly TutorGoal[], language: LanguageCode): readonly TutorGoal[] {
  const selected = new Set(goals);
  return TUTOR_GOALS.filter((goal) => selected.has(goal) && isGoalAvailable(goal, language));
}
function isSafeLabel(value: unknown): value is string {
  return typeof value === "string" && value === value.trim() && value.length > 0 && value.length <= 160 &&
    !/[\u0000-\u001f\u007f]/u.test(value);
}
function isOrder(value: unknown): value is number {
  return typeof value === "number" && Number.isInteger(value) && value >= 0;
}
function isCount(value: unknown): value is number {
  return typeof value === "number" && Number.isInteger(value) && value >= 0;
}
function boundedByOrder<T extends { readonly label: string; readonly order: number }>(
  items: readonly T[] | undefined,
  valid: (item: T) => boolean,
): readonly T[] {
  const labels = new Set<string>();
  return (items ?? []).filter((item) => {
    if (!valid(item) || labels.has(item.label)) return false;
    labels.add(item.label);
    return true;
  }).sort((left, right) => left.order - right.order || left.label.localeCompare(right.label))
    .slice(0, MAX_CONTEXT_ITEMS);
}

export function bandIndex(band: Band): number { return BAND_ORDER.indexOf(band); }
export function compareBands(left: Band, right: Band): number { return bandIndex(left) - bandIndex(right); }
export function isHigherBand(target: Band, current: Band): boolean { return compareBands(target, current) > 0; }
export function isCourseCompatible(currentBand: Band | undefined, course: Band | undefined): boolean {
  return currentBand !== undefined && course !== undefined && compareBands(currentBand, course) >= 0;
}

export function tutorPreferencesKey(scope: TutorPreferenceScope): string {
  return `${TUTOR_PREFERENCES_KEY_PREFIX}.${scope.learnerId}.${scope.language}`;
}
export function emptyTutorPreferences(scope: TutorPreferenceScope): TutorPreferences {
  return { version: TUTOR_PREFERENCES_VERSION, ...scope, goals: [] };
}
export function parseTutorPreferences(serialized: string | null, scope: TutorPreferenceScope): TutorPreferences {
  if (!serialized) return emptyTutorPreferences(scope);
  try {
    const candidate: unknown = JSON.parse(serialized);
    if (!isRecord(candidate) || candidate.version !== TUTOR_PREFERENCES_VERSION ||
      candidate.learnerId !== scope.learnerId || candidate.language !== scope.language ||
      !isLearnerId(candidate.learnerId) || !isLanguage(candidate.language) ||
      (candidate.currentBand !== undefined && !isBand(candidate.currentBand)) ||
      (candidate.targetBand !== undefined && !isBand(candidate.targetBand)) ||
      (candidate.dailyAllocationMinutes !== undefined && !isDailyAllocationMinutes(candidate.dailyAllocationMinutes)) ||
      !Array.isArray(candidate.goals) || !candidate.goals.every(isGoal) ||
      !candidate.goals.every((goal) => isGoalAvailable(goal as TutorGoal, scope.language)) ||
      new Set(candidate.goals).size !== candidate.goals.length ||
      (candidate.targetBand !== undefined && candidate.currentBand === undefined) ||
      (isBand(candidate.currentBand) && isBand(candidate.targetBand) && !isHigherBand(candidate.targetBand, candidate.currentBand))) {
      return emptyTutorPreferences(scope);
    }
    return {
      version: TUTOR_PREFERENCES_VERSION, ...scope,
      ...(isBand(candidate.currentBand) ? { currentBand: candidate.currentBand } : {}),
      ...(isBand(candidate.targetBand) ? { targetBand: candidate.targetBand } : {}),
      ...(isDailyAllocationMinutes(candidate.dailyAllocationMinutes) ? { dailyAllocationMinutes: candidate.dailyAllocationMinutes } : {}),
      goals: canonicalGoals(candidate.goals as TutorGoal[], scope.language),
    };
  } catch { return emptyTutorPreferences(scope); }
}
export function loadTutorPreferences(scope: TutorPreferenceScope, storage?: StorageLike): TutorPreferences {
  try { return parseTutorPreferences((storage ?? browserStorage()).getItem(tutorPreferencesKey(scope)), scope); }
  catch { return emptyTutorPreferences(scope); }
}
export function saveTutorPreferences(preferences: TutorPreferences, storage?: StorageLike): boolean {
  if (preferences.version !== TUTOR_PREFERENCES_VERSION || !isLearnerId(preferences.learnerId) ||
    !isLanguage(preferences.language) ||
    (preferences.currentBand !== undefined && !isBand(preferences.currentBand)) ||
    (preferences.targetBand !== undefined && !isBand(preferences.targetBand)) ||
    (preferences.dailyAllocationMinutes !== undefined && !isDailyAllocationMinutes(preferences.dailyAllocationMinutes)) ||
    preferences.goals.some((goal) => !isGoal(goal) || !isGoalAvailable(goal, preferences.language)) ||
    new Set(preferences.goals).size !== preferences.goals.length ||
    (preferences.targetBand !== undefined && preferences.currentBand === undefined) ||
    (preferences.currentBand !== undefined && preferences.targetBand !== undefined &&
      !isHigherBand(preferences.targetBand, preferences.currentBand))) return false;
  const normalized: TutorPreferences = { ...preferences, goals: canonicalGoals(preferences.goals, preferences.language) };
  try {
    (storage ?? browserStorage()).setItem(tutorPreferencesKey(normalized), JSON.stringify(normalized));
    reportLocalStateAvailable();
    return true;
  } catch (error) {
    reportLocalStateIssue("write", error);
    return false;
  }
}
export function resetTutorPreferences(scope: TutorPreferenceScope, storage?: StorageLike): boolean {
  try {
    (storage ?? browserStorage()).removeItem(tutorPreferencesKey(scope));
    reportLocalStateAvailable();
    return true;
  } catch (error) {
    reportLocalStateIssue("remove", error);
    return false;
  }
}

export function projectTutorContext(preferences: TutorPreferences, sources: TutorContextSources): TutorContext {
  const scopeMatches = sources.language === preferences.language;
  const compatibleCourse = scopeMatches && isCourseCompatible(preferences.currentBand, sources.course) &&
    (sources.language === "en" || sources.course === "A1") ? sources.course : undefined;
  const includeSources = scopeMatches && compatibleCourse !== undefined;
  const lessons = boundedByOrder(
    includeSources ? (sources.recentLessons ?? []).map((item) => ({ label: item.title, order: item.recencyOrder })) : [],
    (item) => isSafeLabel(item.label) && isOrder(item.order),
  );
  const vocabulary = boundedByOrder(includeSources ? sources.vocabulary : [], (item) =>
    isSafeLabel(item.label) && isOrder(item.order) && ["learning", "reviewing", "mastered"].includes(item.state));
  const grammar = boundedByOrder(includeSources && preferences.language === "en" ? sources.grammar : [], (item) =>
    isSafeLabel(item.label) && isOrder(item.order) && ["practising", "reviewing", "locally_consolidated"].includes(item.state));
  const patterns = boundedByOrder(includeSources ? sources.outcomePatterns : [], (item) =>
    isSafeLabel(item.label) && isOrder(item.order) && isCount(item.incorrectOutcomes) &&
    isCount(item.reviewCount) && item.incorrectOutcomes > 0 && item.incorrectOutcomes <= item.reviewCount &&
    typeof item.recentIncorrect === "boolean" && typeof item.repeatedIncorrect === "boolean");
  const reviewItems = boundedByOrder(includeSources ? sources.reviewItems : [], (item) =>
    isSafeLabel(item.label) && isOrder(item.order) &&
    (item.source === "objective_activity" || item.source === "vocabulary" || item.source === "grammar") &&
    (item.priority === "recent_incorrect" || item.priority === "due"));

  return {
    version: 1,
    language: preferences.language,
    ...(preferences.currentBand ? { selfReportedCurrentBand: preferences.currentBand } : {}),
    ...(preferences.targetBand ? { aspirationalTargetBand: preferences.targetBand } : {}),
    ...(compatibleCourse ? { course: compatibleCourse } : {}),
    goals: canonicalGoals(preferences.goals, preferences.language),
    recentLessonTitles: lessons.map((item) => item.label),
    vocabulary: vocabulary.map(({ label, state }) => ({ label, state })),
    ...(preferences.language === "en" ? { grammar: grammar.map(({ label, state }) => ({ label, state })) } : {}),
    objectiveActivityOutcomePatterns: patterns.map(({ label, incorrectOutcomes, reviewCount, recentIncorrect, repeatedIncorrect }) =>
      ({ label, incorrectOutcomes, reviewCount, recentIncorrect, repeatedIncorrect })),
    reviewItems: reviewItems.map(({ label, source, priority }) => ({ label, source, priority })),
    limitations: [
      "Bands are learner-reported preferences, not proficiency or diagnostic results.",
      "Local activity states and outcomes do not establish ability, mastery, or a linguistic weakness.",
    ],
  };
}

export function serializeTutorContext(context: TutorContext): string {
  const format = <T>(items: readonly T[], render: (item: T) => string): string =>
    items.length ? items.map(render).join("; ") : "none";
  const lines = [
    "You are an external practice partner. Treat the following as learner-provided local records, not verified ability.",
    "Stay within the compatible current course. Use only supplied labels and states. Ask one bounded practice question or offer one bounded explanation at a time.",
    "Do not assess CEFR, claim mastery or proficiency, diagnose a weakness, infer why an outcome was incorrect, request private drafts/audio/transcripts, or introduce material above the compatible course.",
    "",
    "Tutor context (local, bounded labels and states only)",
    `Target language: ${context.language === "en" ? "English" : "German"}`,
    `Self-reported current band: ${context.selfReportedCurrentBand ?? "not provided"}`,
    `Aspirational target band: ${context.aspirationalTargetBand ?? "not provided"}`,
    `Compatible current course: ${context.course ?? "not provided"}`,
    `Learning goals: ${context.goals.length ? context.goals.join(", ") : "not provided"}`,
    `Recent lessons: ${context.recentLessonTitles.length ? context.recentLessonTitles.join("; ") : "none"}`,
    `Vocabulary local states: ${format(context.vocabulary, (item) => `${item.label} (${item.state})`)}`,
  ];
  if (context.grammar) lines.push(`Grammar local states: ${format(context.grammar, (item) => `${item.label} (${item.state})`)}`);
  lines.push(
    `Objective activity outcome patterns: ${format(context.objectiveActivityOutcomePatterns, (item) =>
      `${item.label} (${item.incorrectOutcomes}/${item.reviewCount} incorrect outcomes; recent=${item.recentIncorrect}; repeated=${item.repeatedIncorrect})`)}`,
    `Review items: ${format(context.reviewItems, (item) => `${item.label} (${item.source}; ${item.priority})`)}`,
    ...context.limitations.map((limitation) => `Limitation: ${limitation}`),
  );
  return lines.join("\n");
}
