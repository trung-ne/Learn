import { getLessonById } from "@/content/catalog";
import type { CourseLevel, LanguageCode } from "@/content/types";
import {
  isObjectiveExerciseType,
  isRecentIncorrect,
  reviewItemId,
  type ReviewProgress,
  type ReviewResult,
} from "@/lib/review-progress";

export interface ActivityOutcomePattern {
  readonly id: string;
  readonly lessonId: string;
  readonly unitId: string;
  readonly exerciseId: string;
  readonly lessonTitle: string;
  readonly lessonTopic: string;
  readonly lessonSequence: number;
  readonly associatedObjectives: readonly string[];
  readonly reviewCount: number;
  readonly correctCount: number;
  readonly incorrectCount: number;
  readonly incorrectOutcomePercent: number;
  readonly firstSeenAt: string;
  readonly lastReviewedAt: string;
  readonly lastResult: ReviewResult;
  readonly nextReviewAt: string;
  readonly hasIncorrectOutcome: true;
  readonly hasRepeatedIncorrectOutcomes: boolean;
  readonly isRecentIncorrect: boolean;
}

export function deriveActivityOutcomePatterns(
  progress: ReviewProgress,
  language: LanguageCode,
  course: CourseLevel,
  now: string,
): readonly ActivityOutcomePattern[] {
  if (progress.language !== language || progress.course !== course) return [];
  const patterns = Object.values(progress.items).flatMap((item) => {
    if (item.incorrectCount < 1) return [];
    const lesson = getLessonById(language, course, item.lessonId);
    const exercise = lesson?.exercises?.find((candidate) => candidate.id === item.exerciseId);
    if (!lesson || !exercise || !isObjectiveExerciseType(exercise.type)) return [];
    return [{
      id: reviewItemId(item.lessonId, item.exerciseId),
      lessonId: item.lessonId,
      unitId: lesson.unitId,
      exerciseId: item.exerciseId,
      lessonTitle: lesson.title,
      lessonTopic: lesson.topic,
      lessonSequence: lesson.sequence,
      associatedObjectives: lesson.objectives ?? [],
      reviewCount: item.reviewCount,
      correctCount: item.correctCount,
      incorrectCount: item.incorrectCount,
      incorrectOutcomePercent: Math.round((item.incorrectCount / item.reviewCount) * 100),
      firstSeenAt: item.firstSeenAt,
      lastReviewedAt: item.lastReviewedAt,
      lastResult: item.lastResult,
      nextReviewAt: item.nextReviewAt,
      hasIncorrectOutcome: true as const,
      hasRepeatedIncorrectOutcomes: item.incorrectCount >= 2,
      isRecentIncorrect: isRecentIncorrect(item, now),
    }];
  });
  return patterns.sort((left, right) =>
    resultRank(left.lastResult) - resultRank(right.lastResult) ||
    Number(right.hasRepeatedIncorrectOutcomes) - Number(left.hasRepeatedIncorrectOutcomes) ||
    right.incorrectCount - left.incorrectCount ||
    right.lastReviewedAt.localeCompare(left.lastReviewedAt) ||
    left.lessonSequence - right.lessonSequence ||
    left.lessonId.localeCompare(right.lessonId) ||
    left.exerciseId.localeCompare(right.exerciseId),
  );
}

function resultRank(result: ReviewResult): number {
  return result === "incorrect" ? 0 : 1;
}
