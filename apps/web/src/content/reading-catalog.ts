import rawSnapshot from "./generated/reading-snapshot.json";
import type {
  ReadingCatalogSelectors,
  ReadingMode,
  ReadingReader,
  ReadingSnapshot,
  ReadingWordSenseRange,
} from "./reading-types";
import { vocabularySnapshot } from "./vocabulary-catalog";
import type { Band } from "./types";

const bands: readonly Band[] = ["A1", "A2", "B1", "B2", "C1", "C2"];
const modes: readonly ReadingMode[] = ["GRADED_OBJECTIVE", "SUPPLIED_TEXT"];

function isRecord(value: unknown): value is Record<string, unknown> {
  return Boolean(value) && typeof value === "object" && !Array.isArray(value);
}

function isNonEmptyString(value: unknown): value is string {
  return typeof value === "string" && value.trim().length > 0;
}

function isSafeId(value: unknown): value is string {
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

function validateQuestion(value: unknown): void {
  if (!isRecord(value)) throw new Error("Reading snapshot contains an invalid objective question.");
  hasOnlyFields(value, ["prompt", "acceptedAnswers"], "Reading question");
  if (!isNonEmptyString(value.prompt) || !isStringArray(value.acceptedAnswers) || !value.acceptedAnswers.length ||
    new Set(value.acceptedAnswers).size !== value.acceptedAnswers.length) {
    throw new Error("Reading snapshot contains an invalid objective question.");
  }
}

function validateRange(value: unknown, sourceText: string, knownSenseIds: ReadonlySet<string>): asserts value is ReadingWordSenseRange {
  if (!isRecord(value)) throw new Error("Reading snapshot contains an invalid WordSense range.");
  hasOnlyFields(value, ["start", "end", "senseId"], "Reading WordSense range");
  if (!Number.isInteger(value.start) || !Number.isInteger(value.end) || (value.start as number) < 0 ||
    (value.end as number) <= (value.start as number) || (value.end as number) > sourceText.length ||
    !isSafeId(value.senseId) || !knownSenseIds.has(value.senseId)) {
    throw new Error("Reading snapshot contains an invalid WordSense range.");
  }
  const sense = vocabularySnapshot.senses.find((candidate) => candidate.id === value.senseId);
  if (!sense || sourceText.slice(value.start as number, value.end as number) !== sense.lemma) {
    throw new Error("Reading snapshot contains a WordSense range that is not an exact literal occurrence.");
  }
  if (((value.start as number) > 0 && /[A-Za-z]/u.test(sourceText[(value.start as number) - 1]!)) ||
    ((value.end as number) < sourceText.length && /[A-Za-z]/u.test(sourceText[value.end as number]!))) {
    throw new Error("Reading snapshot contains a partial-word WordSense range.");
  }
}

function validateReader(value: unknown, knownSenseIds: ReadonlySet<string>): void {
  if (!isRecord(value)) throw new Error("Reading snapshot contains an invalid reader.");
  hasOnlyFields(value, [
    "id", "band", "tier", "title", "topic", "mode", "sourceText", "questions", "wordSenseRanges", "capabilityLabels", "contentStatus",
  ], "Reading reader");
  if (!isSafeId(value.id) || !bands.includes(value.band as Band) || value.band === "B2" ||
    !isNonEmptyString(value.tier) || !new RegExp(`^${value.band}\\.[12]$`, "u").test(value.tier) ||
    !isNonEmptyString(value.title) || !isNonEmptyString(value.topic) || !modes.includes(value.mode as ReadingMode) ||
    !isNonEmptyString(value.sourceText) || value.contentStatus !== "UNREVIEWED" ||
    (value.capabilityLabels !== undefined && (!isStringArray(value.capabilityLabels) || !value.capabilityLabels.length ||
      new Set(value.capabilityLabels).size !== value.capabilityLabels.length))) {
    throw new Error("Reading snapshot contains an invalid reader.");
  }
  if (value.mode === "GRADED_OBJECTIVE") {
    if (!["A1", "A2", "B1"].includes(value.band as string) || !Array.isArray(value.questions) || !value.questions.length) {
      throw new Error("A graded reading reader must contain supplied objective questions.");
    }
    value.questions.forEach(validateQuestion);
  } else if (value.mode === "SUPPLIED_TEXT") {
    if (!["C1", "C2"].includes(value.band as string) || value.questions !== undefined) {
      throw new Error("A supplied-text reading reader cannot contain objective answer data.");
    }
  }
  if (value.wordSenseRanges !== undefined) {
    if (!Array.isArray(value.wordSenseRanges) || !value.wordSenseRanges.length) {
      throw new Error("Reading snapshot contains invalid WordSense ranges.");
    }
    value.wordSenseRanges.forEach((range) => validateRange(range, value.sourceText as string, knownSenseIds));
    const ranges = value.wordSenseRanges as readonly ReadingWordSenseRange[];
    for (let index = 1; index < ranges.length; index += 1) {
      const previous = ranges[index - 1]!;
      const current = ranges[index]!;
      if (current.start < previous.start || (current.start === previous.start && current.end < previous.end) || current.start < previous.end) {
        throw new Error("Reading snapshot contains unsorted or overlapping WordSense ranges.");
      }
    }
    const identities = ranges.map((range) => `${range.start}:${range.end}:${range.senseId}`);
    if (new Set(identities).size !== identities.length) throw new Error("Reading snapshot contains duplicate WordSense ranges.");
  }
}

export function validateReadingSnapshot(value: unknown): asserts value is ReadingSnapshot {
  if (!isRecord(value) || value.schemaVersion !== "1.0" || !isNonEmptyString(value.inventoryVersion) || !Array.isArray(value.readers)) {
    throw new Error("Unsupported reading snapshot metadata.");
  }
  hasOnlyFields(value, ["schemaVersion", "inventoryVersion", "readers"], "Reading snapshot");
  const knownSenseIds = new Set(vocabularySnapshot.senses.map((sense) => sense.id));
  const ids = new Set<string>();
  for (const reader of value.readers) {
    validateReader(reader, knownSenseIds);
    const id = (reader as ReadingReader).id;
    if (ids.has(id)) throw new Error("Reading snapshot contains duplicate reader IDs.");
    ids.add(id);
  }
  const readers = value.readers as readonly ReadingReader[];
  if (readers.length !== 212 || readers.filter((reader) => reader.mode === "GRADED_OBJECTIVE").length !== 112 ||
    readers.filter((reader) => reader.mode === "SUPPLIED_TEXT").length !== 100) {
    throw new Error("Reading snapshot does not contain the closed approved inventory.");
  }
}

const candidateSnapshot: unknown = rawSnapshot;
validateReadingSnapshot(candidateSnapshot);
export const readingSnapshot = candidateSnapshot;

export function getReadingReaders(selectors: ReadingCatalogSelectors = {}): readonly ReadingReader[] {
  return readingSnapshot.readers.filter((reader) =>
    (selectors.band === undefined || reader.band === selectors.band) &&
    (selectors.tier === undefined || reader.tier === selectors.tier) &&
    (selectors.topic === undefined || reader.topic === selectors.topic) &&
    (selectors.mode === undefined || reader.mode === selectors.mode),
  );
}

export function getReadingReader(readerId: string): ReadingReader | undefined {
  return readingSnapshot.readers.find((reader) => reader.id === readerId);
}

export function getReadingBands(): readonly Band[] {
  return bands.filter((band) => readingSnapshot.readers.some((reader) => reader.band === band));
}

export function getReadingTiers(band?: Band): readonly string[] {
  return [...new Set(readingSnapshot.readers
    .filter((reader) => band === undefined || reader.band === band)
    .map((reader) => reader.tier))].sort();
}

export function getReadingTopics(selectors: Pick<ReadingCatalogSelectors, "band" | "tier" | "mode"> = {}): readonly string[] {
  return [...new Set(getReadingReaders(selectors).map((reader) => reader.topic))].sort((left, right) => left.localeCompare(right));
}

export function getReadingModes(): readonly ReadingMode[] {
  return modes.filter((mode) => readingSnapshot.readers.some((reader) => reader.mode === mode));
}
