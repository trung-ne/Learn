import type { Band, LanguageCode } from "./types";

export type GrammarContentStatus = "UNREVIEWED";

export interface GrammarExerciseBinding {
  readonly lessonId: string;
  readonly exerciseId: string;
}

export interface GrammarTarget {
  readonly id: string;
  readonly language: "en";
  readonly band: Band;
  readonly tier: string;
  readonly title: string;
  readonly topic: string;
  readonly introductionLessonId: string;
  readonly prerequisiteIds: readonly string[];
  readonly exerciseBindings: readonly GrammarExerciseBinding[];
  readonly contentStatus: GrammarContentStatus;
}

export interface GrammarSnapshot {
  readonly schemaVersion: "1.0";
  readonly inventoryVersion: string;
  readonly targets: readonly GrammarTarget[];
}

export type GrammarLearningState = "practising" | "reviewing" | "locally_consolidated";
