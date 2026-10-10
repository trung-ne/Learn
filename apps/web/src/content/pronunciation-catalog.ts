import rawSnapshot from "./generated/pronunciation-snapshot.json";
import { getLessonById } from "./catalog";
import type { Band, LanguageCode } from "./types";
import type { PronunciationProtocol, PronunciationSnapshot } from "./pronunciation-types";

const bands = new Set(["A1", "A2", "B1", "B2", "C1", "C2"]);
const languages = new Set<LanguageCode>(["en", "de"]);

function isRecord(value: unknown): value is Record<string, unknown> {
  return Boolean(value) && typeof value === "object" && !Array.isArray(value);
}
function isString(value: unknown): value is string { return typeof value === "string" && value.trim().length > 0; }
function isSafeId(value: unknown): value is string { return typeof value === "string" && /^[a-z][a-z0-9-]*$/u.test(value); }
function isTextList(value: unknown): value is readonly string[] {
  return Array.isArray(value) && value.length > 0 && value.every(isString) && new Set(value).size === value.length;
}
function hasOnlyFields(value: Record<string, unknown>, fields: readonly string[], label: string): void {
  if (Object.keys(value).some((field) => !fields.includes(field))) throw new Error(`${label} contains unsupported learner-facing fields.`);
}

function validateProtocol(value: unknown): asserts value is PronunciationProtocol {
  if (!isRecord(value)) throw new Error("Pronunciation snapshot contains an invalid protocol.");
  hasOnlyFields(value, [
    "id", "language", "band", "tier", "unitId", "lessonId", "title", "topic", "instruction", "goal", "target",
    "constraints", "checklist", "examples", "explanation", "assessmentAvailability", "contentStatus",
  ], "Pronunciation protocol");
  if (!isSafeId(value.id) || !languages.has(value.language as LanguageCode) || !bands.has(value.band as string) ||
    !isString(value.tier) || !new RegExp(`^${value.band}\\.[12]$`, "u").test(value.tier) || !isSafeId(value.unitId) ||
    !isSafeId(value.lessonId) || !isString(value.title) || !isString(value.topic) || !isString(value.instruction) ||
    (value.goal !== undefined && !isString(value.goal)) || (value.target !== undefined && !isString(value.target)) ||
    (value.constraints !== undefined && !isTextList(value.constraints)) || (value.checklist !== undefined && !isTextList(value.checklist)) ||
    (value.examples !== undefined && !isTextList(value.examples)) || (value.explanation !== undefined && !isString(value.explanation)) ||
    value.assessmentAvailability !== "NOT_ASSESSED" || value.contentStatus !== "UNREVIEWED") {
    throw new Error("Pronunciation snapshot contains an invalid protocol.");
  }
  const lesson = getLessonById(value.language as LanguageCode, value.band as Band, value.lessonId);
  if (!lesson || lesson.unitId !== value.unitId || lesson.tier !== value.tier || lesson.title !== value.title || lesson.topic !== value.topic ||
    lesson.practice?.pronunciation?.instruction !== value.instruction) {
    throw new Error("Pronunciation protocol does not resolve to its supplied lesson.");
  }
}

export function validatePronunciationSnapshot(value: unknown): asserts value is PronunciationSnapshot {
  if (!isRecord(value)) throw new Error("Pronunciation snapshot metadata is invalid.");
  hasOnlyFields(value, ["schemaVersion", "inventoryVersion", "protocols"], "Pronunciation snapshot");
  if (value.schemaVersion !== "1.0" || !isString(value.inventoryVersion) || !Array.isArray(value.protocols) || !value.protocols.length) {
    throw new Error("Pronunciation snapshot metadata is invalid.");
  }
  const ids = new Set<string>();
  const lessonBindings = new Set<string>();
  for (const protocol of value.protocols) {
    validateProtocol(protocol);
    if (ids.has(protocol.id)) throw new Error("Pronunciation snapshot contains duplicate protocol IDs.");
    const binding = `${protocol.language}:${protocol.lessonId}`;
    if (lessonBindings.has(binding)) throw new Error("Pronunciation snapshot contains duplicate lesson protocols.");
    ids.add(protocol.id);
    lessonBindings.add(binding);
  }
}

const candidateSnapshot: unknown = rawSnapshot;
validatePronunciationSnapshot(candidateSnapshot);
export const pronunciationSnapshot = candidateSnapshot;

export function getPronunciationProtocols(language: LanguageCode): readonly PronunciationProtocol[] {
  return pronunciationSnapshot.protocols.filter((protocol) => protocol.language === language);
}

export function getPronunciationLanguages(): readonly LanguageCode[] {
  return [...new Set(pronunciationSnapshot.protocols.map((protocol) => protocol.language))].sort();
}

export function getPronunciationProtocolForLesson(language: LanguageCode, lessonId: string): PronunciationProtocol | undefined {
  return getPronunciationProtocols(language).find((protocol) => protocol.lessonId === lessonId);
}
