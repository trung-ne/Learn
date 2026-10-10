import { getAssessmentPackage } from "@/content/assessment-catalog";
import { getGrammarTargets, grammarSnapshot } from "@/content/grammar-catalog";
import { getVocabularySenses, vocabularySnapshot } from "@/content/vocabulary-catalog";
import type { CourseLevel, LanguageCode } from "@/content/types";
import {
  latestAssessmentAttempt,
  type AssessmentProgress,
} from "@/lib/assessment-progress";
import {
  selectGrammarReviewQueue,
  type GrammarProgress,
} from "@/lib/grammar-progress";
import type { CourseProgress } from "@/lib/progress";
import {
  selectVocabularyReviewQueue,
  type VocabularyProgress,
} from "@/lib/vocabulary-progress";
import { grammarHref, vocabularyHref } from "@/lib/routes";

export type TodayRecommendationCategory =
  | "vocabulary"
  | "grammar"
  | "listening"
  | "pronunciation"
  | "new_lesson";

export interface AdaptiveLessonInventory {
  readonly lessonId: string;
  readonly title: string;
  readonly sequence: number;
  readonly href: string;
  readonly hasListeningPractice: boolean;
  readonly hasPronunciationPractice: boolean;
  readonly durationMinutes: number;
}

export interface AdaptiveCourseInventory {
  readonly language: LanguageCode;
  readonly level: CourseLevel;
  readonly lessons: readonly AdaptiveLessonInventory[];
}

export interface TodayRecommendation {
  readonly category: TodayRecommendationCategory;
  readonly title: string;
  readonly detail: string;
  readonly actionLabel: string;
  readonly href: string;
  readonly itemCount?: number;
  readonly durationMinutes?: number;
}

export interface AdaptiveLearningInput {
  readonly course: AdaptiveCourseInventory;
  readonly courseProgress: CourseProgress;
  readonly now: string;
  readonly vocabularyProgress?: VocabularyProgress;
  readonly grammarProgress?: GrammarProgress;
  readonly assessmentProgress?: AssessmentProgress;
}

function hasValidNow(now: string): boolean {
  return /^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\.\d{3}Z$/u.test(now) && !Number.isNaN(Date.parse(now));
}

function orderedLessons(course: AdaptiveCourseInventory): readonly AdaptiveLessonInventory[] {
  const seen = new Set<string>();
  return course.lessons
    .filter((lesson) =>
      /^[a-z][a-z0-9-]*$/u.test(lesson.lessonId) &&
      typeof lesson.title === "string" && lesson.title.trim().length > 0 &&
      typeof lesson.href === "string" && lesson.href.startsWith("/") &&
      Number.isInteger(lesson.sequence) && lesson.sequence >= 0 &&
      Number.isInteger(lesson.durationMinutes) && lesson.durationMinutes > 0 &&
      !seen.has(lesson.lessonId) && (seen.add(lesson.lessonId), true),
    )
    .sort((left, right) => left.sequence - right.sequence || left.lessonId.localeCompare(right.lessonId));
}

function sameCourse(input: AdaptiveLearningInput): boolean {
  return input.courseProgress.language === input.course.language &&
    input.courseProgress.course === input.course.level;
}

function belongsToCurrentLearner(
  progress: { readonly learnerId: string } | undefined,
  courseProgress: CourseProgress,
): boolean {
  return progress?.learnerId === courseProgress.learnerId;
}

function listeningRecommendation(input: AdaptiveLearningInput, lessons: readonly AdaptiveLessonInventory[]): TodayRecommendation | undefined {
  if (input.course.language !== "en" || !input.assessmentProgress ||
    !belongsToCurrentLearner(input.assessmentProgress, input.courseProgress)) return undefined;
  const lessonById = new Map(lessons.map((lesson) => [lesson.lessonId, lesson]));
  const candidates: AdaptiveLessonInventory[] = [];
  for (const [assessmentId, record] of Object.entries(input.assessmentProgress.packages)) {
    const assessment = getAssessmentPackage(assessmentId);
    if (!assessment || record.packageSha256 !== assessment.packageSha256) continue;
    const attempt = latestAssessmentAttempt(input.assessmentProgress, assessment);
    if (!attempt) continue;
    attempt.itemResults.forEach((result, index) => {
      const item = assessment.items[index];
      if (!item || result.itemId !== item.id || result.correct || item.type !== "listening" || item.source.level !== input.course.level) return;
      const lesson = lessonById.get(item.source.lessonId);
      if (lesson?.hasListeningPractice) candidates.push(lesson);
    });
  }
  const lesson = candidates.sort((left, right) => left.sequence - right.sequence || left.lessonId.localeCompare(right.lessonId))[0];
  return lesson ? {
    category: "listening",
    title: "Listening practice",
    detail: "Revisit a supplied transcript-based listening activity. This is not audio-listening assessment.",
    actionLabel: "Open listening practice",
    href: lesson.href,
  } : undefined;
}

function pronunciationRecommendation(input: AdaptiveLearningInput, lessons: readonly AdaptiveLessonInventory[]): TodayRecommendation | undefined {
  if (!input.courseProgress.lastLessonId ||
    !lessons.some((lesson) => lesson.lessonId === input.courseProgress.lastLessonId)) return undefined;
  const lesson = lessons.find((candidate) =>
    candidate.hasPronunciationPractice && input.courseProgress.lessons[candidate.lessonId]?.protocols.pronunciation !== true,
  );
  return lesson ? {
    category: "pronunciation",
    title: "Pronunciation practice",
    detail: "Open an unfinished supplied pronunciation prompt. No pronunciation score is recorded.",
    actionLabel: "Open pronunciation prompt",
    href: lesson.href,
  } : undefined;
}

export function buildTodayRecommendations(input: AdaptiveLearningInput): readonly TodayRecommendation[] {
  if (!hasValidNow(input.now) || !sameCourse(input)) return [];
  const lessons = orderedLessons(input.course);
  if (!lessons.length) return [];
  const recommendations: TodayRecommendation[] = [];

  if (input.course.language === "en" && input.vocabularyProgress &&
    belongsToCurrentLearner(input.vocabularyProgress, input.courseProgress) &&
    input.vocabularyProgress.inventoryVersion === vocabularySnapshot.inventoryVersion) {
    const senses = getVocabularySenses("en")
      .filter((sense) => sense.band === input.course.level)
      .map((sense, introductionOrder) => ({ senseId: sense.id, introductionOrder }));
    const queue = selectVocabularyReviewQueue(input.vocabularyProgress, senses, input.now);
    if (queue.length) recommendations.push({
      category: "vocabulary",
      title: "Vocabulary review",
      detail: `Revisit ${queue.length} saved vocabulary ${queue.length === 1 ? "item" : "items"}.`,
      actionLabel: "Review vocabulary",
      href: vocabularyHref("en"),
      itemCount: queue.length,
    });
  }

  if (input.course.language === "en" && input.grammarProgress &&
    belongsToCurrentLearner(input.grammarProgress, input.courseProgress) &&
    input.grammarProgress.inventoryVersion === grammarSnapshot.inventoryVersion) {
    const targets = getGrammarTargets("en")
      .filter((target) => target.band === input.course.level)
      .map((target, introductionOrder) => ({ targetId: target.id, introductionOrder }));
    const queue = selectGrammarReviewQueue(input.grammarProgress, targets, input.now);
    const target = queue[0] ? getGrammarTargets("en").find((candidate) => candidate.id === queue[0]) : undefined;
    if (target) recommendations.push({
      category: "grammar",
      title: "Grammar review",
      detail: `Revisit the saved activity for ${target.title}.`,
      actionLabel: "Review grammar",
      href: grammarHref("en"),
      itemCount: queue.length,
    });
  }

  const listening = listeningRecommendation(input, lessons);
  if (listening) recommendations.push(listening);
  const pronunciation = pronunciationRecommendation(input, lessons);
  if (pronunciation) recommendations.push(pronunciation);

  const nextLesson = lessons.find((lesson) => input.courseProgress.lessons[lesson.lessonId]?.completed !== true);
  if (nextLesson) recommendations.push({
    category: "new_lesson",
    title: "New lesson",
    detail: "Open the next available lesson in this course.",
    actionLabel: "Start lesson",
    href: nextLesson.href,
    durationMinutes: nextLesson.durationMinutes,
  });

  return recommendations;
}
