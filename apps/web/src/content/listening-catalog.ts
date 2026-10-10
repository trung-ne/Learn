import rawSnapshot from "./generated/listening-snapshot.json";
import { getLessonById } from "./catalog";
import type { Band } from "./types";
import type { ListeningSession, ListeningSnapshot } from "./listening-types";

const bands = new Set(["A1", "A2", "B1", "B2", "C1", "C2"]);
const mimeKinds: Readonly<Record<string, string>> = {
  "audio/mpeg": "audio", "audio/ogg": "audio", "audio/wav": "audio",
  "video/mp4": "video", "video/webm": "video",
};

function isRecord(value: unknown): value is Record<string, unknown> {
  return Boolean(value) && typeof value === "object" && !Array.isArray(value);
}
function isString(value: unknown): value is string { return typeof value === "string" && value.trim().length > 0; }
function isSafeId(value: unknown): value is string { return typeof value === "string" && /^[a-z][a-z0-9-]*$/u.test(value); }
function isAnonymousSpeaker(value: unknown): value is string { return typeof value === "string" && /^SPEAKER_[0-9]{2,}$/u.test(value); }
function isStringArray(value: unknown): value is readonly string[] { return Array.isArray(value) && value.every(isString) && new Set(value).size === value.length; }
function hasOnlyFields(value: Record<string, unknown>, fields: readonly string[], label: string): void {
  if (Object.keys(value).some((field) => !fields.includes(field))) throw new Error(`${label} contains unsupported learner-facing fields.`);
}

function validateSession(value: unknown): asserts value is ListeningSession {
  if (!isRecord(value)) throw new Error("Listening snapshot contains an invalid session.");
  hasOnlyFields(value, [
    "id", "language", "band", "tier", "unitId", "lessonId", "title", "topic", "mediaKind", "mimeType", "assetPath", "assetHash",
    "durationSeconds", "accent", "speakerLabels", "speed", "grammar", "vocabulary", "phoneticFeatures", "meaningPrompt",
    "acceptedMeaningAnswers", "dictationPrompt", "transcript", "sentences", "contentStatus",
  ], "Listening session");
  if (!isSafeId(value.id) || value.language !== "en" || !bands.has(value.band as string) ||
    !isString(value.tier) || !isSafeId(value.unitId) || !isSafeId(value.lessonId) || !isString(value.title) || !isString(value.topic) ||
    (value.mediaKind !== "audio" && value.mediaKind !== "video") || !isString(value.mimeType) || mimeKinds[value.mimeType] !== value.mediaKind ||
    !isString(value.assetPath) || !new RegExp(`^/listening-lab/${value.id}/[a-zA-Z0-9._-]+$`, "u").test(value.assetPath) ||
    !isString(value.assetHash) || !/^[a-f0-9]{64}$/u.test(value.assetHash) ||
    typeof value.durationSeconds !== "number" || !Number.isFinite(value.durationSeconds) || value.durationSeconds <= 0 ||
    !isString(value.accent) || !isStringArray(value.speakerLabels) || !value.speakerLabels.every(isAnonymousSpeaker) ||
    !isString(value.speed) || !isStringArray(value.grammar) || !isStringArray(value.vocabulary) || !isStringArray(value.phoneticFeatures) ||
    !isString(value.meaningPrompt) || !isStringArray(value.acceptedMeaningAnswers) || !isString(value.dictationPrompt) ||
    !isString(value.transcript) || !Array.isArray(value.sentences) || !value.sentences.length || value.contentStatus !== "UNREVIEWED") {
    throw new Error("Listening snapshot contains an invalid session.");
  }
  let previousEnd = 0;
  const sentenceIds = new Set<string>();
  for (const sentence of value.sentences) {
    if (!isRecord(sentence) || !isSafeId(sentence.id) || sentenceIds.has(sentence.id) ||
      typeof sentence.startSeconds !== "number" || !Number.isFinite(sentence.startSeconds) || sentence.startSeconds < previousEnd ||
      typeof sentence.endSeconds !== "number" || !Number.isFinite(sentence.endSeconds) || sentence.endSeconds <= sentence.startSeconds ||
      sentence.endSeconds > value.durationSeconds || !isString(sentence.text) || !isAnonymousSpeaker(sentence.speaker) ||
      !value.speakerLabels.includes(sentence.speaker)) {
      throw new Error("Listening snapshot contains invalid sentence timing or speaker metadata.");
    }
    sentenceIds.add(sentence.id);
    previousEnd = sentence.endSeconds;
  }
  const lesson = getLessonById("en", value.band as Band, value.lessonId);
  if (!lesson || lesson.unitId !== value.unitId || lesson.topic !== value.topic || lesson.band !== value.band) {
    throw new Error("Listening session does not resolve to its supplied English lesson.");
  }
}

export function validateListeningSnapshot(value: unknown): asserts value is ListeningSnapshot {
  if (!isRecord(value)) throw new Error("Listening snapshot metadata is invalid.");
  hasOnlyFields(value, ["schemaVersion", "inventoryVersion", "availability", "sessions"], "Listening snapshot");
  if (value.schemaVersion !== "1.0" || !isString(value.inventoryVersion) ||
    (value.availability !== "NO_AUTHORIZED_MEDIA" && value.availability !== "AUTHORIZED_MEDIA_AVAILABLE") || !Array.isArray(value.sessions)) {
    throw new Error("Listening snapshot metadata is invalid.");
  }
  if ((value.availability === "NO_AUTHORIZED_MEDIA" && value.sessions.length !== 0) ||
    (value.availability === "AUTHORIZED_MEDIA_AVAILABLE" && value.sessions.length === 0)) {
    throw new Error("Listening snapshot availability does not match its supplied sessions.");
  }
  const ids = new Set<string>();
  for (const session of value.sessions) {
    validateSession(session);
    if (ids.has(session.id)) throw new Error("Listening snapshot contains duplicate session IDs.");
    ids.add(session.id);
  }
}

const candidateSnapshot: unknown = rawSnapshot;
validateListeningSnapshot(candidateSnapshot);
export const listeningSnapshot = candidateSnapshot;

export function getListeningSessions(language: "en"): readonly ListeningSession[] {
  return listeningSnapshot.sessions.filter((session) => session.language === language);
}

export function getListeningSessionForLesson(language: "en", lessonId: string): ListeningSession | undefined {
  return getListeningSessions(language).find((session) => session.lessonId === lessonId);
}
