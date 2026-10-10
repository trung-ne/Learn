import type { Band } from "./types";

export type ReadingContentStatus = "UNREVIEWED";
export type ReadingMode = "GRADED_OBJECTIVE" | "SUPPLIED_TEXT";

export interface ReadingQuestion {
  readonly prompt: string;
  readonly acceptedAnswers: readonly string[];
}

export interface ReadingWordSenseRange {
  readonly start: number;
  readonly end: number;
  readonly senseId: string;
}

export interface ReadingReader {
  readonly id: string;
  readonly band: Band;
  readonly tier: string;
  readonly title: string;
  readonly topic: string;
  readonly mode: ReadingMode;
  readonly sourceText: string;
  readonly questions?: readonly ReadingQuestion[];
  readonly wordSenseRanges?: readonly ReadingWordSenseRange[];
  readonly capabilityLabels?: readonly string[];
  readonly contentStatus: ReadingContentStatus;
}

export interface ReadingSnapshot {
  readonly schemaVersion: "1.0";
  readonly inventoryVersion: string;
  readonly readers: readonly ReadingReader[];
}

export interface ReadingCatalogSelectors {
  readonly band?: Band;
  readonly tier?: string;
  readonly topic?: string;
  readonly mode?: ReadingMode;
}
