import type { Band, LanguageCode } from "./types";

export type DictionaryEntryKind = "word_sense" | "phrasal_verb" | "word_form";
export type DictionaryContentStatus = "UNREVIEWED";

export interface DictionaryRelations {
  readonly senseIds: readonly string[];
  readonly phrasalVerbIds: readonly string[];
  readonly wordFamilyIds: readonly string[];
}

export interface DictionaryRecall {
  readonly prompt: string;
  readonly acceptedAnswers: readonly string[];
  readonly distractors: readonly string[];
}

export interface DictionaryEntry {
  readonly id: string;
  readonly language: LanguageCode;
  readonly kind: DictionaryEntryKind;
  readonly headword: string;
  readonly senseNumber?: number;
  readonly band: Band;
  readonly tier: string;
  readonly partOfSpeech: string;
  readonly definition: string;
  readonly vietnameseMeaning?: string;
  readonly ipa?: string;
  readonly examples: readonly string[];
  readonly collocations: readonly string[];
  readonly relations: DictionaryRelations;
  readonly recall: DictionaryRecall;
  readonly contentStatus: DictionaryContentStatus;
}

export interface DictionarySnapshot {
  readonly schemaVersion: "1.0";
  readonly inventoryVersion: string;
  readonly entries: readonly DictionaryEntry[];
}
