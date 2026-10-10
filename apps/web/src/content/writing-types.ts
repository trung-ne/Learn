import type { Band } from "./types";

export type WritingContentStatus = "UNREVIEWED";
export type WritingFeedbackBoundary = "FEEDBACK_ONLY_NO_REPLACEMENT";

export interface WritingProtocol {
  readonly id: string;
  readonly language: "en";
  readonly band: Band;
  readonly tier: string;
  readonly unitId: string;
  readonly lessonId: string;
  readonly title: string;
  readonly topic: string;
  readonly goal: string;
  readonly instruction: string;
  readonly constraints: readonly string[];
  readonly feedbackBoundary: WritingFeedbackBoundary;
  readonly contentStatus: WritingContentStatus;
}

export interface WritingSnapshot {
  readonly schemaVersion: "1.0";
  readonly inventoryVersion: string;
  readonly protocols: readonly WritingProtocol[];
}
