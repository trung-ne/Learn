import rawSnapshot from "./generated/vocabulary-snapshot.json";
import type { LanguageCode } from "./types";
import type { VocabularySense, VocabularySnapshot } from "./vocabulary-types";

function isRecord(value: unknown): value is Record<string, unknown> {
  return Boolean(value) && typeof value === "object" && !Array.isArray(value);
}

function isNonEmptyString(value: unknown): value is string {
  return typeof value === "string" && value.trim().length > 0;
}

function isSafeSenseId(value: unknown): value is string {
  return typeof value === "string" && /^[a-z][a-z0-9-]*$/u.test(value);
}

function isStringArray(value: unknown): value is readonly string[] {
  return Array.isArray(value) && value.every(isNonEmptyString);
}

function hasOnlyFields(value: Record<string, unknown>, allowed: readonly string[], label: string): void {
  if (Object.keys(value).some((field) => !allowed.includes(field))) {
    throw new Error(`${label} contains unsupported learner-facing fields.`);
  }
}

function validateBinding(value: unknown): void {
  if (!isRecord(value)) throw new Error("Vocabulary snapshot contains an invalid exercise binding.");
  hasOnlyFields(value, ["lessonId", "exerciseId"], "Vocabulary exercise binding");
  if (!isSafeSenseId(value.lessonId) || !isSafeSenseId(value.exerciseId)) {
    throw new Error("Vocabulary snapshot contains an invalid exercise binding.");
  }
}

function validateSense(value: unknown): void {
  if (!isRecord(value)) throw new Error("Vocabulary snapshot contains an invalid WordSense.");
  hasOnlyFields(value, [
    "id", "language", "band", "tier", "lemma", "senseNumber", "partOfSpeech", "definition", "vietnameseMeaning", "ipa",
    "examples", "collocations", "introductionLessonId", "recallPrompt", "acceptedAnswers", "distractors", "exerciseBindings", "contentStatus",
  ], "WordSense");
  if (!isSafeSenseId(value.id) || value.language !== "en" || !["A1", "A2", "B1", "B2", "C1", "C2"].includes(value.band as string) ||
    !isNonEmptyString(value.tier) || !isNonEmptyString(value.lemma) || !Number.isInteger(value.senseNumber) ||
    (value.senseNumber as number) < 1 || !isNonEmptyString(value.partOfSpeech) || !isNonEmptyString(value.definition) ||
    !isStringArray(value.examples) || !value.examples.length || !isStringArray(value.collocations) || !value.collocations.length ||
    !isSafeSenseId(value.introductionLessonId) || !isNonEmptyString(value.recallPrompt) ||
    !isStringArray(value.acceptedAnswers) || !value.acceptedAnswers.length || !isStringArray(value.distractors) ||
    value.distractors.length < 2 || value.contentStatus !== "UNREVIEWED" || !Array.isArray(value.exerciseBindings) ||
    !value.exerciseBindings.length || (value.vietnameseMeaning !== undefined && !isNonEmptyString(value.vietnameseMeaning)) ||
    (value.ipa !== undefined && !isNonEmptyString(value.ipa))) {
    throw new Error("Vocabulary snapshot contains an invalid WordSense.");
  }
  const acceptedAnswers = value.acceptedAnswers as readonly string[];
  const distractors = value.distractors as readonly string[];
  if (new Set(acceptedAnswers).size !== acceptedAnswers.length ||
    new Set(distractors).size !== distractors.length ||
    distractors.some((item) => acceptedAnswers.includes(item))) {
    throw new Error("Vocabulary snapshot contains invalid answer data.");
  }
  value.exerciseBindings.forEach(validateBinding);
}

export function validateVocabularySnapshot(value: unknown): asserts value is VocabularySnapshot {
  if (!isRecord(value) || value.schemaVersion !== "1.0" || !isNonEmptyString(value.inventoryVersion) || !Array.isArray(value.senses)) {
    throw new Error("Unsupported vocabulary snapshot metadata.");
  }
  hasOnlyFields(value, ["schemaVersion", "inventoryVersion", "senses"], "Vocabulary snapshot");
  const ids = new Set<string>();
  const identities = new Set<string>();
  for (const sense of value.senses) {
    validateSense(sense);
    const item = sense as VocabularySense;
    const identity = `${item.lemma}\u0000${item.partOfSpeech}\u0000${item.senseNumber}`;
    if (ids.has(item.id) || identities.has(identity)) throw new Error("Vocabulary snapshot contains duplicate WordSense identities.");
    ids.add(item.id);
    identities.add(identity);
  }
}

const candidateSnapshot: unknown = rawSnapshot;
validateVocabularySnapshot(candidateSnapshot);
export const vocabularySnapshot = candidateSnapshot;

export function getVocabularySenses(language: LanguageCode): readonly VocabularySense[] {
  return vocabularySnapshot.senses.filter((sense) => sense.language === language);
}

export function getVocabularySense(senseId: string): VocabularySense | undefined {
  return vocabularySnapshot.senses.find((sense) => sense.id === senseId);
}

export function getVocabularyForLesson(language: LanguageCode, lessonId: string): readonly VocabularySense[] {
  return getVocabularySenses(language).filter((sense) => sense.introductionLessonId === lessonId);
}

export function getVocabularySenseIdsForExercise(
  language: LanguageCode,
  lessonId: string,
  exerciseId: string,
): readonly string[] {
  return getVocabularySenses(language)
    .filter((sense) => sense.exerciseBindings.some((binding) =>
      binding.lessonId === lessonId && binding.exerciseId === exerciseId,
    ))
    .map((sense) => sense.id);
}
