import { getGrammarTargets, grammarSnapshot } from "@/content/grammar-catalog";
import type { CourseLevel, LanguageCode, PracticeModality } from "@/content/types";
import { getVocabularySenses, vocabularySnapshot } from "@/content/vocabulary-catalog";
import { isGrammarTargetDue, type GrammarProgress } from "@/lib/grammar-progress";
import type { CourseProgress } from "@/lib/progress";
import {
  isRecentIncorrect,
  isReviewItemDue,
  type ReviewProgress,
} from "@/lib/review-progress";
import {
  BAND_ORDER,
  compareBands,
  type TutorPreferences,
} from "@/lib/tutor-context";
import { isDue, type VocabularyProgress } from "@/lib/vocabulary-progress";

const REVIEW_SHARE_DIVISOR = 3;
const MAX_REVIEW_QUOTA = 3;
const WEEKLY_DAYS = 7;
const SKILL_ORDER = ["Vocabulary", "Grammar", "Reading", "Transcript-based listening", "Speaking", "Writing", "Pronunciation"] as const;

export interface StudyPlanLesson {
  readonly lessonId: string;
  readonly title: string;
  readonly level: CourseLevel;
  readonly sequence: number;
  readonly durationMinutes: number;
  readonly href: string;
  readonly exerciseTypes: readonly string[];
  /** Current supplied objective exercise IDs; absent data cannot authorize objective review. */
  readonly objectiveExerciseIds?: readonly string[];
  readonly practiceModalities: readonly PracticeModality[];
}

export interface StudyPlanCourse {
  readonly language: LanguageCode;
  readonly level: CourseLevel;
  readonly lessons: readonly StudyPlanLesson[];
}

export interface StudyPlanReviewAction {
  readonly source: string;
  readonly itemCount: number;
  readonly href: string;
}

export interface StudyPlanWeeklyBlock {
  readonly blockNumber: number;
  readonly levels: readonly CourseLevel[];
  readonly lessons: readonly StudyPlanLesson[];
  readonly suppliedDisplayMinutes: number;
}

export interface ReadyPersonalStudyPlan {
  readonly status: "READY";
  readonly currentBand: CourseLevel;
  readonly targetBand: CourseLevel;
  readonly dailyAllocationMinutes: number;
  readonly reviewAllocationMinutes: number;
  readonly lessonAllocationMinutes: number;
  readonly remainingLessons: readonly StudyPlanLesson[];
  readonly remainingSuppliedDisplayMinutes: number;
  readonly plannedDailyBlocks: number;
  readonly plannedWeeklyBlocks: number;
  readonly dailyLessons: readonly StudyPlanLesson[];
  readonly reviewQuota: readonly StudyPlanReviewAction[];
  readonly weeklyBlocks: readonly StudyPlanWeeklyBlock[];
  readonly availablePracticeFocus: readonly (typeof SKILL_ORDER)[number][];
}

export interface UnavailablePersonalStudyPlan {
  readonly status: "UNAVAILABLE";
  readonly reason: string;
}

export type PersonalStudyPlan = ReadyPersonalStudyPlan | UnavailablePersonalStudyPlan;

export interface PersonalStudyPlanInput {
  readonly language: LanguageCode;
  readonly learnerId: string;
  readonly preferences: TutorPreferences;
  readonly courses: readonly StudyPlanCourse[];
  readonly courseProgress: Readonly<Record<CourseLevel, CourseProgress | undefined>>;
  readonly reviewProgress: Readonly<Record<CourseLevel, ReviewProgress | undefined>>;
  readonly vocabularyProgress?: VocabularyProgress;
  readonly grammarProgress?: GrammarProgress;
  readonly reviewHref: (level: CourseLevel) => string;
  readonly vocabularyHref?: string;
  readonly grammarHref?: string;
  readonly now: string;
}

function unavailable(reason: string): UnavailablePersonalStudyPlan {
  return { status: "UNAVAILABLE", reason };
}

function validTimestamp(value: string): boolean {
  return /^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\.\d{3}Z$/u.test(value) && !Number.isNaN(Date.parse(value));
}

function validLesson(lesson: StudyPlanLesson): boolean {
  return /^[a-z][a-z0-9-]*$/u.test(lesson.lessonId) && lesson.title.trim().length > 0 &&
    Number.isInteger(lesson.sequence) && lesson.sequence >= 0 &&
    Number.isInteger(lesson.durationMinutes) && lesson.durationMinutes > 0 && lesson.href.startsWith("/");
}

function corridorLevels(current: CourseLevel, target: CourseLevel): readonly CourseLevel[] {
  return BAND_ORDER.filter((band) => compareBands(band, current) >= 0 && compareBands(band, target) <= 0);
}

function scopedCourseProgress(
  progress: CourseProgress | undefined,
  input: PersonalStudyPlanInput,
  level: CourseLevel,
): CourseProgress | undefined {
  return progress?.learnerId === input.learnerId && progress.language === input.language && progress.course === level
    ? progress
    : undefined;
}

function scopedReviewProgress(
  progress: ReviewProgress | undefined,
  input: PersonalStudyPlanInput,
  level: CourseLevel,
): ReviewProgress | undefined {
  return progress?.learnerId === input.learnerId && progress.language === input.language && progress.course === level
    ? progress
    : undefined;
}

function orderedCourseLessons(course: StudyPlanCourse): readonly StudyPlanLesson[] | undefined {
  const seen = new Set<string>();
  const lessons = course.lessons.filter((lesson) => validLesson(lesson) && lesson.level === course.level && !seen.has(lesson.lessonId) && (seen.add(lesson.lessonId), true))
    .sort((left, right) => left.sequence - right.sequence || left.lessonId.localeCompare(right.lessonId));
  return lessons.length === course.lessons.length ? lessons : undefined;
}

function remainingLessons(input: PersonalStudyPlanInput, levels: readonly CourseLevel[]): readonly StudyPlanLesson[] | undefined {
  const result: StudyPlanLesson[] = [];
  for (const level of levels) {
    const course = input.courses.find((candidate) => candidate.language === input.language && candidate.level === level);
    if (!course) return undefined;
    const lessons = orderedCourseLessons(course);
    if (!lessons?.length) return undefined;
    const progress = scopedCourseProgress(input.courseProgress[level], input, level);
    result.push(...lessons.filter((lesson) => progress?.lessons[lesson.lessonId]?.completed !== true));
  }
  return result;
}

function plannedLessons(lessons: readonly StudyPlanLesson[], budget: number): readonly StudyPlanLesson[] {
  const selected: StudyPlanLesson[] = [];
  let total = 0;
  for (const lesson of lessons) {
    if (total + lesson.durationMinutes > budget) break;
    selected.push(lesson);
    total += lesson.durationMinutes;
  }
  return selected;
}

function weeklyBlocks(lessons: readonly StudyPlanLesson[], weeklyBudget: number): readonly StudyPlanWeeklyBlock[] {
  const blocks: StudyPlanWeeklyBlock[] = [];
  let current: StudyPlanLesson[] = [];
  let minutes = 0;
  const publish = () => {
    if (!current.length) return;
    blocks.push({
      blockNumber: blocks.length + 1,
      levels: [...new Set(current.map((lesson) => lesson.level))],
      lessons: current,
      suppliedDisplayMinutes: minutes,
    });
    current = [];
    minutes = 0;
  };
  for (const lesson of lessons) {
    if (current.length && minutes + lesson.durationMinutes > weeklyBudget) publish();
    current.push(lesson);
    minutes += lesson.durationMinutes;
  }
  publish();
  return blocks;
}

interface ReviewQuotaCandidate {
  readonly source: "objective" | "vocabulary" | "grammar";
  readonly level?: CourseLevel;
  readonly id: string;
  readonly dueAt: string;
  readonly priority: "recent_incorrect" | "due";
  readonly order: number;
  readonly href: string;
}

function reviewPriority(candidate: ReviewQuotaCandidate): number {
  return candidate.priority === "recent_incorrect" ? 0 : 1;
}

function reviewQuotaCandidates(input: PersonalStudyPlanInput, levels: readonly CourseLevel[]): readonly ReviewQuotaCandidate[] {
  const candidates: ReviewQuotaCandidate[] = [];
  for (const level of levels) {
    const progress = scopedReviewProgress(input.reviewProgress[level], input, level);
    const course = input.courses.find((candidate) => candidate.language === input.language && candidate.level === level);
    const lessons = course && orderedCourseLessons(course);
    if (!progress || !lessons) continue;
    const objectiveExerciseIds = new Map(lessons.map((lesson) => [lesson.lessonId, new Set(lesson.objectiveExerciseIds ?? [])]));
    Object.values(progress.items).forEach((item, order) => {
      if (!objectiveExerciseIds.get(item.lessonId)?.has(item.exerciseId) || !isReviewItemDue(item, input.now)) return;
      candidates.push({
        source: "objective",
        level,
        id: `${level}:${item.lessonId}:${item.exerciseId}`,
        dueAt: item.nextReviewAt,
        priority: isRecentIncorrect(item, input.now) ? "recent_incorrect" : "due",
        order,
        href: input.reviewHref(level),
      });
    });
  }

  const permitted = new Set(levels);
  const vocabularyProgress = input.vocabularyProgress;
  if (input.language === "en" && input.vocabularyHref && vocabularyProgress?.learnerId === input.learnerId &&
    vocabularyProgress.language === "en" && vocabularyProgress.inventoryVersion === vocabularySnapshot.inventoryVersion) {
    getVocabularySenses("en").forEach((sense, order) => {
      const progress = vocabularyProgress.senses[sense.id];
      if (!permitted.has(sense.band) || !progress || !isDue(progress, input.now)) return;
      candidates.push({ source: "vocabulary", id: sense.id, dueAt: progress.nextReviewAt, priority: "due", order, href: input.vocabularyHref! });
    });
  }

  const grammarProgress = input.grammarProgress;
  if (input.language === "en" && input.grammarHref && grammarProgress?.learnerId === input.learnerId &&
    grammarProgress.language === "en" && grammarProgress.inventoryVersion === grammarSnapshot.inventoryVersion) {
    getGrammarTargets("en").forEach((target, order) => {
      const progress = grammarProgress.targets[target.id];
      if (!permitted.has(target.band) || !progress || !isGrammarTargetDue(progress, input.now)) return;
      candidates.push({ source: "grammar", id: target.id, dueAt: progress.nextReviewAt, priority: "due", order, href: input.grammarHref! });
    });
  }
  return candidates;
}

function reviewQuota(input: PersonalStudyPlanInput, levels: readonly CourseLevel[]): readonly StudyPlanReviewAction[] {
  const selected = reviewQuotaCandidates(input, levels)
    .filter((candidate) => validTimestamp(candidate.dueAt) && candidate.dueAt <= input.now)
    .sort((left, right) => reviewPriority(left) - reviewPriority(right) || left.dueAt.localeCompare(right.dueAt) ||
      left.order - right.order || left.source.localeCompare(right.source) || left.id.localeCompare(right.id))
    .slice(0, MAX_REVIEW_QUOTA);
  const actions = new Map<string, StudyPlanReviewAction>();
  for (const candidate of selected) {
    const source = candidate.source === "objective"
      ? `Objective review (${candidate.level})`
      : candidate.source === "vocabulary" ? "Vocabulary review" : "Grammar review";
    const key = `${source}:${candidate.href}`;
    const current = actions.get(key);
    actions.set(key, current ? { ...current, itemCount: current.itemCount + 1 } : {
      source,
      itemCount: 1,
      href: candidate.href,
    });
  }
  return [...actions.values()];
}

function practiceFocus(input: PersonalStudyPlanInput, levels: readonly CourseLevel[], lessons: readonly StudyPlanLesson[]): readonly (typeof SKILL_ORDER)[number][] {
  const available = new Set<(typeof SKILL_ORDER)[number]>();
  if (input.language === "en" && getVocabularySenses("en").some((sense) => levels.includes(sense.band))) available.add("Vocabulary");
  if (input.language === "en" && getGrammarTargets("en").some((target) => levels.includes(target.band))) available.add("Grammar");
  if (lessons.some((lesson) => lesson.exerciseTypes.includes("reading"))) available.add("Reading");
  if (lessons.some((lesson) => lesson.exerciseTypes.includes("listening") || lesson.practiceModalities.includes("listening"))) available.add("Transcript-based listening");
  if (lessons.some((lesson) => lesson.practiceModalities.includes("speaking"))) available.add("Speaking");
  if (lessons.some((lesson) => lesson.practiceModalities.includes("writing"))) available.add("Writing");
  if (lessons.some((lesson) => lesson.practiceModalities.includes("pronunciation"))) available.add("Pronunciation");
  return SKILL_ORDER.filter((skill) => available.has(skill));
}

export function buildPersonalStudyPlan(input: PersonalStudyPlanInput): PersonalStudyPlan {
  if (!validTimestamp(input.now)) return unavailable("A valid local time is required to build the plan.");
  const { currentBand, targetBand, dailyAllocationMinutes } = input.preferences;
  if (input.preferences.learnerId !== input.learnerId || input.preferences.language !== input.language || !currentBand || !targetBand || !dailyAllocationMinutes) {
    return unavailable("Choose a self-reported current band, a higher goal, and a daily planning allocation.");
  }
  if (compareBands(targetBand, currentBand) <= 0) return unavailable("Choose a goal higher than the self-reported current band.");
  const levels = corridorLevels(currentBand, targetBand);
  const remaining = remainingLessons(input, levels);
  if (!remaining) return unavailable("The supplied curriculum does not contain a complete path for these selections.");
  const reviewAllocationMinutes = Math.ceil(dailyAllocationMinutes / REVIEW_SHARE_DIVISOR);
  const lessonAllocationMinutes = dailyAllocationMinutes - reviewAllocationMinutes;
  const totalMinutes = remaining.reduce((total, lesson) => total + lesson.durationMinutes, 0);
  const daily = plannedLessons(remaining, lessonAllocationMinutes);
  const dailyBlocks = weeklyBlocks(remaining, lessonAllocationMinutes);
  const weekly = weeklyBlocks(remaining, lessonAllocationMinutes * WEEKLY_DAYS);
  return {
    status: "READY",
    currentBand,
    targetBand,
    dailyAllocationMinutes,
    reviewAllocationMinutes,
    lessonAllocationMinutes,
    remainingLessons: remaining,
    remainingSuppliedDisplayMinutes: totalMinutes,
    plannedDailyBlocks: dailyBlocks.length,
    plannedWeeklyBlocks: weekly.length,
    dailyLessons: daily,
    reviewQuota: reviewQuota(input, levels),
    weeklyBlocks: weekly,
    availablePracticeFocus: practiceFocus(input, levels, remaining),
  };
}
