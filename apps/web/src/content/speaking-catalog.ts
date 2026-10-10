import rawSnapshot from "./generated/speaking-snapshot.json";
import { getLessonById } from "./catalog";
import type { Band, LanguageCode } from "./types";
import type { SpeakingAssessment, SpeakingProtocol, SpeakingSnapshot } from "./speaking-types";

const bands = new Set(["A1", "A2", "B1", "B2", "C1", "C2"]);
const languages = new Set<LanguageCode>(["en", "de"]);
const assessmentFields = ["overall", "grammar", "vocabulary", "fluency", "pronunciation", "coherence", "appropriacy"] as const;

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
function validateAssessment(value: unknown): asserts value is SpeakingAssessment {
  if (!isRecord(value)) throw new Error("Speaking protocol assessment is invalid.");
  hasOnlyFields(value, assessmentFields, "Speaking assessment");
  if (Object.keys(value).length !== assessmentFields.length || assessmentFields.some((field) => value[field] !== "NOT_ASSESSED")) {
    throw new Error("Speaking protocol assessment is invalid.");
  }
}

function validateProtocol(value: unknown): asserts value is SpeakingProtocol {
  if (!isRecord(value)) throw new Error("Speaking snapshot contains an invalid protocol.");
  hasOnlyFields(value, [
    "id", "language", "band", "tier", "unitId", "lessonId", "title", "topic", "instruction", "goal",
    "constraints", "checklist", "assessment", "contentStatus",
  ], "Speaking protocol");
  if (!isSafeId(value.id) || !languages.has(value.language as LanguageCode) || !bands.has(value.band as string) ||
    !isString(value.tier) || !new RegExp(`^${value.band}\\.[12]$`, "u").test(value.tier) || !isSafeId(value.unitId) ||
    !isSafeId(value.lessonId) || !isString(value.title) || !isString(value.topic) || !isString(value.instruction) ||
    value.contentStatus !== "UNREVIEWED") {
    throw new Error("Speaking snapshot contains an invalid protocol.");
  }
  if (value.language === "en") {
    if (!isString(value.goal) || !isTextList(value.constraints) || value.checklist !== undefined) {
      throw new Error("English speaking protocol must contain exact goal and constraints fields.");
    }
  } else if (!isTextList(value.checklist) || value.goal !== undefined || value.constraints !== undefined) {
    throw new Error("German speaking protocol must contain the exact checklist field.");
  }
  validateAssessment(value.assessment);
  const lesson = getLessonById(value.language as LanguageCode, value.band as Band, value.lessonId);
  if (!lesson || lesson.unitId !== value.unitId || lesson.tier !== value.tier || lesson.title !== value.title || lesson.topic !== value.topic ||
    lesson.practice?.speaking?.instruction !== value.instruction) {
    throw new Error("Speaking protocol does not resolve to its supplied lesson.");
  }
}

export function validateSpeakingSnapshot(value: unknown): asserts value is SpeakingSnapshot {
  if (!isRecord(value)) throw new Error("Speaking snapshot metadata is invalid.");
  hasOnlyFields(value, ["schemaVersion", "inventoryVersion", "protocols"], "Speaking snapshot");
  if (value.schemaVersion !== "1.0" || !isString(value.inventoryVersion) || !Array.isArray(value.protocols) || !value.protocols.length) {
    throw new Error("Speaking snapshot metadata is invalid.");
  }
  const ids = new Set<string>();
  const lessonBindings = new Set<string>();
  for (const protocol of value.protocols) {
    validateProtocol(protocol);
    if (ids.has(protocol.id)) throw new Error("Speaking snapshot contains duplicate protocol IDs.");
    const binding = `${protocol.language}:${protocol.lessonId}`;
    if (lessonBindings.has(binding)) throw new Error("Speaking snapshot contains duplicate lesson protocols.");
    ids.add(protocol.id);
    lessonBindings.add(binding);
  }
}

const candidateSnapshot: unknown = rawSnapshot;
validateSpeakingSnapshot(candidateSnapshot);
export const speakingSnapshot = candidateSnapshot;

export function getSpeakingProtocols(language: LanguageCode): readonly SpeakingProtocol[] {
  return speakingSnapshot.protocols.filter((protocol) => protocol.language === language);
}

export function getSpeakingLanguages(): readonly LanguageCode[] {
  return [...new Set(speakingSnapshot.protocols.map((protocol) => protocol.language))].sort();
}

export function getSpeakingProtocolForLesson(language: LanguageCode, lessonId: string): SpeakingProtocol | undefined {
  return getSpeakingProtocols(language).find((protocol) => protocol.lessonId === lessonId);
}
