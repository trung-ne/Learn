import snapshot from "./generated/dictionary-snapshot.json";
import type { DictionaryEntry, DictionarySnapshot } from "./dictionary-types";

export const dictionarySnapshot = snapshot as DictionarySnapshot;

function normalize(value: string): string {
  return value.trim().toLocaleLowerCase("en").replace(/\s+/gu, " ");
}

function searchText(entry: DictionaryEntry): string {
  return [
    entry.headword,
    entry.definition,
    entry.vietnameseMeaning ?? "",
    entry.partOfSpeech,
    entry.band,
    entry.tier,
    ...entry.collocations,
  ].join("\n").toLocaleLowerCase("en");
}

export function getDictionaryEntries(language: "en"): readonly DictionaryEntry[] {
  return dictionarySnapshot.entries.filter((entry) => entry.language === language);
}

export function getDictionaryEntry(entryId: string): DictionaryEntry | undefined {
  return dictionarySnapshot.entries.find((entry) => entry.id === entryId);
}

export function searchDictionaryEntries(language: "en", query: string): readonly DictionaryEntry[] {
  const normalized = normalize(query);
  const entries = getDictionaryEntries(language);
  return normalized ? entries.filter((entry) => searchText(entry).includes(normalized)) : entries;
}

export function getDictionaryRelations(entry: DictionaryEntry, relation: keyof DictionaryEntry["relations"]): readonly DictionaryEntry[] {
  const ids = new Set(entry.relations[relation]);
  return dictionarySnapshot.entries.filter((candidate) => ids.has(candidate.id));
}
