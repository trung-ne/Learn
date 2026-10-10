import { getAssessmentPackages } from "@/content/assessment-catalog";
import { type AssessmentProgress } from "@/lib/assessment-progress";
import { grammarSnapshot, getGrammarTargets } from "@/content/grammar-catalog";
import type { CourseLevel, LanguageCode } from "@/content/types";
import { vocabularySnapshot, getVocabularySenses } from "@/content/vocabulary-catalog";
import {
  isGrammarTargetDue,
  type GrammarProgress,
} from "@/lib/grammar-progress";
import { deriveActivityOutcomePatterns } from "@/lib/mistake-weakness";
import {
  isRecentIncorrect,
  isReviewItemDue,
  type ReviewProgress,
} from "@/lib/review-progress";
import {
  summarizeCourseProgress,
  type CourseProgress,
} from "@/lib/progress";
import {
  isDue,
  type VocabularyProgress,
} from "@/lib/vocabulary-progress";

const COURSE_ORDER: readonly CourseLevel[] = ["A1", "A2", "B1", "B2", "C1", "C2"];

export interface ProgressDashboardLesson {
  readonly lessonId: string;
  readonly unitId: string;
}

export interface ProgressDashboardCourse {
  readonly language: LanguageCode;
  readonly level: CourseLevel;
  readonly lessons: readonly ProgressDashboardLesson[];
}

export interface CourseCompletionRow {
  readonly level: CourseLevel;
  readonly completedLessons: number;
  readonly suppliedLessons: number;
  readonly completionPercent: number;
}

export interface VocabularyStateSummary {
  readonly availability: "AVAILABLE" | "NOT_AVAILABLE";
  readonly suppliedSenses: number;
  readonly activeSenses: number;
  readonly locallyMasteredSenses: number;
  readonly sensesWithRecordedMistakes: number;
  readonly dueSenses: number;
}

export interface GrammarStateSummary {
  readonly availability: "AVAILABLE" | "NOT_AVAILABLE";
  readonly suppliedTargets: number;
  readonly activeTargets: number;
  readonly locallyConsolidatedTargets: number;
  readonly targetsWithRecordedIncorrectOutcomes: number;
  readonly dueTargets: number;
}

export interface LocalReviewSummary {
  readonly reviewedActivities: number;
  readonly reviewOutcomes: number;
  readonly correctOutcomes: number;
  readonly incorrectOutcomes: number;
  readonly dueActivities: number;
  readonly recentIncorrectActivities: number;
}

export interface ActivityOutcomeSummary {
  readonly activitiesWithRecordedIncorrectOutcomes: number;
  readonly repeatedIncorrectOutcomePatterns: number;
  readonly recentIncorrectOutcomePatterns: number;
}

export interface DirectSkillEvidence {
  readonly label: "Vocabulary" | "Grammar" | "Listening" | "Reading" | "Speaking" | "Writing";
  readonly status: "AVAILABLE" | "NOT_ASSESSED" | "NOT_AVAILABLE";
  readonly correct?: number;
  readonly total?: number;
  readonly limitation: string;
}

export interface PracticeActivitySummary {
  readonly listeningProtocolsMarkedComplete: number;
  readonly speakingProtocolsMarkedComplete: number;
  readonly pronunciationProtocolsMarkedComplete: number;
  readonly writingProtocolsMarkedComplete: number;
}

export interface ProgressDashboardSummary {
  readonly courses: readonly CourseCompletionRow[];
  readonly vocabulary: VocabularyStateSummary;
  readonly grammar: GrammarStateSummary;
  readonly directSkillEvidence: readonly DirectSkillEvidence[];
  readonly practiceActivity: PracticeActivitySummary;
  readonly review: LocalReviewSummary;
  readonly activityOutcomes: ActivityOutcomeSummary;
  readonly retentionStatus: "NOT_MEASURED";
  readonly mistakeTrendStatus: "NOT_TRACKED";
  readonly studyTimeStatus: "NOT_RECORDED";
}

export interface ProgressDashboardInput {
  readonly learnerId: string;
  readonly language: LanguageCode;
  readonly courses: readonly ProgressDashboardCourse[];
  readonly courseProgress: Readonly<Record<CourseLevel, CourseProgress | undefined>>;
  readonly vocabularyProgress?: VocabularyProgress;
  readonly grammarProgress?: GrammarProgress;
  readonly assessmentProgress?: AssessmentProgress;
  readonly reviewProgress: Readonly<Record<CourseLevel, ReviewProgress | undefined>>;
  readonly now: string;
}

function validTimestamp(value: string): boolean {
  return /^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\.\d{3}Z$/u.test(value) && !Number.isNaN(Date.parse(value));
}

function percent(numerator: number, denominator: number): number {
  return denominator ? Math.round((numerator / denominator) * 100) : 0;
}

function belongsToCourse(
  progress: CourseProgress | ReviewProgress | undefined,
  input: ProgressDashboardInput,
  level: CourseLevel,
): boolean {
  return progress?.learnerId === input.learnerId && progress.language === input.language && progress.course === level;
}

function orderedCourses(courses: readonly ProgressDashboardCourse[], language: LanguageCode): readonly ProgressDashboardCourse[] {
  const seen = new Set<CourseLevel>();
  return courses
    .filter((course) => course.language === language && !seen.has(course.level) && (seen.add(course.level), true))
    .sort((left, right) => COURSE_ORDER.indexOf(left.level) - COURSE_ORDER.indexOf(right.level));
}

function courseRows(input: ProgressDashboardInput, courses: readonly ProgressDashboardCourse[]): readonly CourseCompletionRow[] {
  return courses.map((course) => {
    const progress = input.courseProgress[course.level];
    const summary = belongsToCourse(progress, input, course.level)
      ? summarizeCourseProgress(progress, course.lessons)
      : { completedLessons: 0, totalLessons: course.lessons.length };
    return {
      level: course.level,
      completedLessons: summary.completedLessons,
      suppliedLessons: summary.totalLessons,
      completionPercent: percent(summary.completedLessons, summary.totalLessons),
    };
  });
}

function vocabularySummary(input: ProgressDashboardInput): VocabularyStateSummary {
  const progress = input.vocabularyProgress;
  const senses = getVocabularySenses(input.language);
  if (!progress || progress.learnerId !== input.learnerId || progress.language !== input.language ||
    progress.inventoryVersion !== vocabularySnapshot.inventoryVersion || !senses.length) {
    return { availability: "NOT_AVAILABLE", suppliedSenses: senses.length, activeSenses: 0, locallyMasteredSenses: 0, sensesWithRecordedMistakes: 0, dueSenses: 0 };
  }
  const knownIds = new Set(senses.map((sense) => sense.id));
  const entries = Object.entries(progress.senses)
    .filter(([senseId]) => knownIds.has(senseId))
    .map(([, item]) => item);
  return {
    availability: "AVAILABLE",
    suppliedSenses: senses.length,
    activeSenses: entries.filter((item) => item.state !== "mastered").length,
    locallyMasteredSenses: entries.filter((item) => item.state === "mastered").length,
    sensesWithRecordedMistakes: entries.filter((item) => item.mistakes > 0).length,
    dueSenses: validTimestamp(input.now) ? entries.filter((item) => isDue(item, input.now)).length : 0,
  };
}

function grammarSummary(input: ProgressDashboardInput): GrammarStateSummary {
  const progress = input.grammarProgress;
  const targets = getGrammarTargets(input.language);
  if (input.language !== "en" || !progress || progress.learnerId !== input.learnerId ||
    progress.language !== "en" || progress.inventoryVersion !== grammarSnapshot.inventoryVersion) {
    return { availability: "NOT_AVAILABLE", suppliedTargets: targets.length, activeTargets: 0, locallyConsolidatedTargets: 0, targetsWithRecordedIncorrectOutcomes: 0, dueTargets: 0 };
  }
  const knownIds = new Set(targets.map((target) => target.id));
  const entries = Object.entries(progress.targets)
    .filter(([targetId]) => knownIds.has(targetId))
    .map(([, item]) => item);
  return {
    availability: "AVAILABLE",
    suppliedTargets: targets.length,
    activeTargets: entries.filter((item) => item.state !== "locally_consolidated").length,
    locallyConsolidatedTargets: entries.filter((item) => item.state === "locally_consolidated").length,
    targetsWithRecordedIncorrectOutcomes: entries.filter((item) => item.incorrectOutcomes > 0).length,
    dueTargets: validTimestamp(input.now) ? entries.filter((item) => isGrammarTargetDue(item, input.now)).length : 0,
  };
}

interface AssessmentEvidenceTotal {
  readonly correct: number;
  readonly total: number;
}

function currentAssessmentEvidence(progress: AssessmentProgress): Readonly<Record<string, AssessmentEvidenceTotal>> {
  const totals: Record<string, AssessmentEvidenceTotal> = {};
  for (const assessment of getAssessmentPackages()) {
    const record = progress.packages[assessment.id];
    const attempt = record?.packageSha256 === assessment.packageSha256 ? record.attempts.at(-1) : undefined;
    if (!attempt || attempt.packageSha256 !== assessment.packageSha256 || attempt.itemResults.length !== assessment.items.length ||
      !attempt.itemResults.every((result, index) => result.itemId === assessment.items[index]?.id && result.type === assessment.items[index]?.type)) continue;
    attempt.itemResults.forEach((result, index) => {
      const item = assessment.items[index]!;
      for (const label of [...item.targetDimensions, `item:${item.type}`]) {
        const total = totals[label] ?? { correct: 0, total: 0 };
        totals[label] = { correct: total.correct + (result.correct ? 1 : 0), total: total.total + 1 };
      }
    });
  }
  return totals;
}

function directEvidence(input: ProgressDashboardInput): readonly DirectSkillEvidence[] {
  const unavailable = (label: DirectSkillEvidence["label"], limitation: string): DirectSkillEvidence => ({ label, status: "NOT_ASSESSED", limitation });
  if (input.language !== "en" || !input.assessmentProgress || input.assessmentProgress.learnerId !== input.learnerId || input.assessmentProgress.language !== "en") {
    return [
      { label: "Vocabulary", status: "NOT_AVAILABLE", limitation: "No supplied local objective evidence is available for this language." },
      { label: "Grammar", status: "NOT_AVAILABLE", limitation: "No supplied local objective evidence is available for this language." },
      { label: "Listening", status: "NOT_AVAILABLE", limitation: "No supplied transcript-based local evidence is available for this language." },
      { label: "Reading", status: "NOT_AVAILABLE", limitation: "No supplied local objective evidence is available for this language." },
      unavailable("Speaking", "NOT_ASSESSED: the browser does not capture or score speech."),
      unavailable("Writing", "NOT_ASSESSED: the browser does not score learner writing."),
    ];
  }
  const evidence = currentAssessmentEvidence(input.assessmentProgress);
  const measured = (label: DirectSkillEvidence["label"], key: string, limitation: string): DirectSkillEvidence => {
    const total = evidence[key];
    return total?.total
      ? { label, status: "AVAILABLE", correct: total.correct, total: total.total, limitation }
      : { label, status: "NOT_ASSESSED", limitation: `No submitted applicable local evidence. ${limitation}` };
  };
  return [
    measured("Vocabulary", "vocabulary_senses", "Only explicitly tagged vocabulary-sense items count."),
    measured("Grammar", "grammar", "Only explicitly tagged grammar-target items count."),
    measured("Listening", "item:listening", "These supplied items are transcript-based, not audio-listening assessment."),
    measured("Reading", "item:reading", "Only submitted supplied reading items count."),
    unavailable("Speaking", "NOT_ASSESSED: the browser does not capture or score speech."),
    unavailable("Writing", "NOT_ASSESSED: the browser does not score learner writing."),
  ];
}

function practiceActivity(input: ProgressDashboardInput, courses: readonly ProgressDashboardCourse[]): PracticeActivitySummary {
  let listeningProtocolsMarkedComplete = 0;
  let speakingProtocolsMarkedComplete = 0;
  let pronunciationProtocolsMarkedComplete = 0;
  let writingProtocolsMarkedComplete = 0;
  for (const course of courses) {
    const progress = input.courseProgress[course.level];
    if (!belongsToCourse(progress, input, course.level)) continue;
    const knownLessonIds = new Set(course.lessons.map((lesson) => lesson.lessonId));
    for (const [lessonId, lesson] of Object.entries(progress.lessons)) {
      if (!knownLessonIds.has(lessonId)) continue;
      if (lesson.protocols.listening) listeningProtocolsMarkedComplete += 1;
      if (lesson.protocols.speaking) speakingProtocolsMarkedComplete += 1;
      if (lesson.protocols.pronunciation) pronunciationProtocolsMarkedComplete += 1;
      if (lesson.protocols.writing) writingProtocolsMarkedComplete += 1;
    }
  }
  return { listeningProtocolsMarkedComplete, speakingProtocolsMarkedComplete, pronunciationProtocolsMarkedComplete, writingProtocolsMarkedComplete };
}

function reviewSummaries(input: ProgressDashboardInput, courses: readonly ProgressDashboardCourse[]): Pick<ProgressDashboardSummary, "review" | "activityOutcomes"> {
  let reviewedActivities = 0;
  let reviewOutcomes = 0;
  let correctOutcomes = 0;
  let incorrectOutcomes = 0;
  let dueActivities = 0;
  let recentIncorrectActivities = 0;
  let activitiesWithRecordedIncorrectOutcomes = 0;
  let repeatedIncorrectOutcomePatterns = 0;
  let recentIncorrectOutcomePatterns = 0;

  for (const course of courses) {
    const progress = input.reviewProgress[course.level];
    if (!belongsToCourse(progress, input, course.level)) continue;
    const knownLessonIds = new Set(course.lessons.map((lesson) => lesson.lessonId));
    const items = Object.values(progress.items).filter((item) => knownLessonIds.has(item.lessonId));
    reviewedActivities += items.length;
    reviewOutcomes += items.reduce((total, item) => total + item.reviewCount, 0);
    correctOutcomes += items.reduce((total, item) => total + item.correctCount, 0);
    incorrectOutcomes += items.reduce((total, item) => total + item.incorrectCount, 0);
    if (validTimestamp(input.now)) {
      dueActivities += items.filter((item) => isReviewItemDue(item, input.now)).length;
      recentIncorrectActivities += items.filter((item) => isRecentIncorrect(item, input.now)).length;
      const patterns = deriveActivityOutcomePatterns(progress, input.language, course.level, input.now);
      activitiesWithRecordedIncorrectOutcomes += patterns.length;
      repeatedIncorrectOutcomePatterns += patterns.filter((pattern) => pattern.hasRepeatedIncorrectOutcomes).length;
      recentIncorrectOutcomePatterns += patterns.filter((pattern) => pattern.isRecentIncorrect).length;
    }
  }
  return {
    review: { reviewedActivities, reviewOutcomes, correctOutcomes, incorrectOutcomes, dueActivities, recentIncorrectActivities },
    activityOutcomes: { activitiesWithRecordedIncorrectOutcomes, repeatedIncorrectOutcomePatterns, recentIncorrectOutcomePatterns },
  };
}

export function buildProgressDashboard(input: ProgressDashboardInput): ProgressDashboardSummary {
  const courses = orderedCourses(input.courses, input.language);
  const review = reviewSummaries(input, courses);
  return {
    courses: courseRows(input, courses),
    vocabulary: vocabularySummary(input),
    grammar: grammarSummary(input),
    directSkillEvidence: directEvidence(input),
    practiceActivity: practiceActivity(input, courses),
    review: review.review,
    activityOutcomes: review.activityOutcomes,
    retentionStatus: "NOT_MEASURED",
    mistakeTrendStatus: "NOT_TRACKED",
    studyTimeStatus: "NOT_RECORDED",
  };
}
