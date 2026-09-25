import type { CourseLevel, LanguageCode } from "./languages";

export type { CourseLevel, LanguageCode } from "./languages";
export type Band = CourseLevel;
export type ContentStatus = "UNREVIEWED";

export interface ContentSection {
  readonly id: string;
  readonly title: string;
  readonly type: string;
  readonly body: string;
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
  readonly media_required?: boolean;
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
}

export interface DisplayLesson {
  readonly language: LanguageCode;
  readonly packetFamily: "english-full" | "german-pilot";
  readonly recordType: string;
  readonly languageName: string;
  readonly band: Band;
  readonly tier: string;
  readonly unitId: string;
  readonly lessonId: string;
  readonly packetId: string;
  readonly packetPath: string;
  readonly packetSha256: string;
  readonly sequence: number;
  readonly title: string;
  readonly topic: string;
  readonly durationMinutes: number;
  readonly objectives: readonly string[];
  readonly languageFocus: string;
  readonly prerequisites: readonly string[];
  readonly sections: readonly ContentSection[];
  readonly exercises: readonly DisplayExercise[];
  readonly practice: Readonly<Record<"listening" | "speaking" | "pronunciation" | "writing", PracticeProtocol>>;
  readonly contentStatus: ContentStatus;
  readonly provenance: Readonly<Record<string, string>>;
}

export interface SourceManifestReference {
  readonly language: LanguageCode;
  readonly band: Band;
  readonly path: string;
  readonly sha256: string;
  readonly declaredManifestSha256: string;
  readonly packetCount: number;
}

export interface LanguageSummary {
  readonly code: LanguageCode;
  readonly name: string;
  readonly lessonCount: number;
  readonly bands: readonly Band[];
}

export interface CurriculumSnapshot {
  readonly schemaVersion: "1.0";
  readonly contentStatus: ContentStatus;
  readonly sourceManifests: readonly SourceManifestReference[];
  readonly languages: readonly LanguageSummary[];
  readonly lessons: readonly DisplayLesson[];
  readonly snapshotSha256: string;
}
