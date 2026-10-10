import type { Band, LanguageCode } from "./types";

export type SpeakingAssessmentAvailability = "NOT_ASSESSED";

export interface SpeakingAssessment {
  readonly overall: SpeakingAssessmentAvailability;
  readonly grammar: SpeakingAssessmentAvailability;
  readonly vocabulary: SpeakingAssessmentAvailability;
  readonly fluency: SpeakingAssessmentAvailability;
  readonly pronunciation: SpeakingAssessmentAvailability;
  readonly coherence: SpeakingAssessmentAvailability;
  readonly appropriacy: SpeakingAssessmentAvailability;
}

export interface SpeakingProtocol {
  readonly id: string;
  readonly language: LanguageCode;
  readonly band: Band;
  readonly tier: string;
  readonly unitId: string;
  readonly lessonId: string;
  readonly title: string;
  readonly topic: string;
  readonly instruction: string;
  readonly goal?: string;
  readonly constraints?: readonly string[];
  readonly checklist?: readonly string[];
  readonly assessment: SpeakingAssessment;
  readonly contentStatus: "UNREVIEWED";
}

export interface SpeakingSnapshot {
  readonly schemaVersion: "1.0";
  readonly inventoryVersion: string;
  readonly protocols: readonly SpeakingProtocol[];
}
