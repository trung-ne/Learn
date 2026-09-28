import type { CourseLevel, LanguageCode } from "./languages";

export type { CourseLevel, LanguageCode } from "./languages";
export type Band = CourseLevel;
export type CourseAvailability = "AVAILABLE" | "PILOT";

export interface ContentSection {
  readonly id: string;
  readonly title: string;
  readonly type: string;
  readonly body: string;
  readonly vietnameseTip?: string;
}

export interface Pair {
  readonly left: string;
  readonly right: string;
}

export interface ExerciseQuestion {
  readonly question: string;
  readonly acceptable_answers: readonly string[];
}

export interface ExerciseRubric {
  readonly criteria?: readonly string[];
}

export interface DisplayExercise {
  readonly id: string;
  readonly type: string;
  readonly prompt: string;
  readonly options?: readonly string[];
  readonly correct_answer?: string;
  readonly acceptable_answers?: readonly string[];
  readonly answer?: string;
  readonly items?: readonly string[];
  readonly correct_order?: readonly string[];
  readonly pairs?: readonly Pair[];
  readonly stimulus?: string;
  readonly questions?: readonly ExerciseQuestion[];
  readonly rubric?: ExerciseRubric | string;
  readonly explanation?: string;
}

export interface PracticeProtocol {
  readonly instruction: string;
  readonly goal?: string;
  readonly question?: string;
  readonly answer?: string;
  readonly transcript?: string;
  readonly target?: string;
  readonly without_audio?: string;
  readonly assessment?: string;
  readonly constraints?: readonly string[];
  readonly checklist?: readonly string[];
  readonly feedback_boundary?: string;
  readonly mode?: string;
  readonly situation?: string;
  readonly learner_role?: string;
  readonly ai_role?: string;
  readonly useful_language?: readonly string[];
  readonly examples?: readonly string[];
  readonly explanation?: string;
}

export type PracticeModality = "listening" | "speaking" | "pronunciation" | "writing";
export type LessonPractice = Readonly<Partial<Record<PracticeModality, PracticeProtocol>>>;

export interface DisplayLesson {
  readonly language: LanguageCode;
  readonly band: Band;
  readonly courseAvailability: CourseAvailability;
  readonly tier: string;
  readonly unitId: string;
  readonly lessonId: string;
  readonly sequence: number;
  readonly title: string;
  readonly topic: string;
  readonly durationMinutes: number;
  readonly objectives?: readonly string[];
  readonly languageFocus?: string;
  readonly prerequisites?: readonly string[];
  readonly sections?: readonly ContentSection[];
  readonly exercises?: readonly DisplayExercise[];
  readonly practice?: LessonPractice;
}

export interface LanguageSummary {
  readonly code: LanguageCode;
  readonly name: string;
  readonly lessonCount: number;
  readonly bands: readonly Band[];
}

export interface CurriculumSnapshot {
  readonly schemaVersion: "1.1";
  readonly languages: readonly LanguageSummary[];
  readonly lessons: readonly DisplayLesson[];
}
