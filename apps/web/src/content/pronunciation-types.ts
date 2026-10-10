import type { Band, LanguageCode } from "./types";

export type PronunciationAssessmentAvailability = "NOT_ASSESSED";

export interface PronunciationProtocol {
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
  readonly target?: string;
  readonly constraints?: readonly string[];
  readonly checklist?: readonly string[];
  readonly examples?: readonly string[];
  readonly explanation?: string;
  readonly assessmentAvailability: PronunciationAssessmentAvailability;
  readonly contentStatus: "UNREVIEWED";
}

export interface PronunciationSnapshot {
  readonly schemaVersion: "1.0";
  readonly inventoryVersion: string;
  readonly protocols: readonly PronunciationProtocol[];
}
