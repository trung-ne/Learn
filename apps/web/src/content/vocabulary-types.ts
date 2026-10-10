import type { Band, LanguageCode } from "./types";

export type VocabularyContentStatus = "UNREVIEWED";

export interface VocabularyExerciseBinding {
  readonly lessonId: string;
  readonly exerciseId: string;
}

export interface VocabularySense {
  readonly id: string;
  readonly language: LanguageCode;
  readonly band: Band;
  readonly tier: string;
  readonly lemma: string;
  readonly senseNumber: number;
  readonly partOfSpeech: string;
  readonly definition: string;
  readonly vietnameseMeaning?: string;
  readonly ipa?: string;
  readonly examples: readonly string[];
  readonly collocations: readonly string[];
  readonly introductionLessonId: string;
  readonly recallPrompt: string;
  readonly acceptedAnswers: readonly string[];
  readonly distractors: readonly string[];
  readonly exerciseBindings: readonly VocabularyExerciseBinding[];
  readonly contentStatus: VocabularyContentStatus;
}

export interface VocabularySnapshot {
  readonly schemaVersion: "1.0";
  readonly inventoryVersion: string;
  readonly senses: readonly VocabularySense[];
}
