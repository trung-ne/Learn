import type { Band } from "./types";

export type ListeningAvailability = "NO_AUTHORIZED_MEDIA" | "AUTHORIZED_MEDIA_AVAILABLE";

export interface ListeningSentence {
  readonly id: string;
  readonly startSeconds: number;
  readonly endSeconds: number;
  readonly text: string;
  readonly speaker: string;
}

export interface ListeningSession {
  readonly id: string;
  readonly language: "en";
  readonly band: Band;
  readonly tier: string;
  readonly unitId: string;
  readonly lessonId: string;
  readonly title: string;
  readonly topic: string;
  readonly mediaKind: "audio" | "video";
  readonly mimeType: "audio/mpeg" | "audio/ogg" | "audio/wav" | "video/mp4" | "video/webm";
  readonly assetPath: string;
  readonly assetHash: string;
  readonly durationSeconds: number;
  readonly accent: string;
  readonly speakerLabels: readonly string[];
  readonly speed: string;
  readonly grammar: readonly string[];
  readonly vocabulary: readonly string[];
  readonly phoneticFeatures: readonly string[];
  readonly meaningPrompt: string;
  readonly acceptedMeaningAnswers: readonly string[];
  readonly dictationPrompt: string;
  readonly transcript: string;
  readonly sentences: readonly ListeningSentence[];
  readonly contentStatus: "UNREVIEWED";
}

export interface ListeningSnapshot {
  readonly schemaVersion: "1.0";
  readonly inventoryVersion: string;
  readonly availability: ListeningAvailability;
  readonly sessions: readonly ListeningSession[];
}
