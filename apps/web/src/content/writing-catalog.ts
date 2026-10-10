import rawSnapshot from "./generated/writing-snapshot.json";
import { getLessonById } from "./catalog";
import type { Band } from "./types";
import type { WritingProtocol, WritingSnapshot } from "./writing-types";

const bands = new Set<Band>(["A1", "A2", "B1", "B2", "C1", "C2"]);
const protocolFields = [
  "id", "language", "band", "tier", "unitId", "lessonId", "title", "topic", "goal",
  "instruction", "constraints", "feedbackBoundary", "contentStatus",
] as const;

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

function validateProtocol(value: unknown): asserts value is WritingProtocol {
  if (!isRecord(value)) throw new Error("Writing snapshot contains an invalid protocol.");
  hasOnlyFields(value, protocolFields, "Writing protocol");
  if (
    !isSafeId(value.id) || value.language !== "en" || !bands.has(value.band as Band) ||
    !isString(value.tier) || !new RegExp(`^${value.band}\\.[12]$`, "u").test(value.tier) ||
    !isSafeId(value.unitId) || !isSafeId(value.lessonId) || !isString(value.title) ||
    !isString(value.topic) || !isString(value.goal) || !isString(value.instruction) ||
    !isTextList(value.constraints) || value.feedbackBoundary !== "FEEDBACK_ONLY_NO_REPLACEMENT" ||
    value.contentStatus !== "UNREVIEWED"
  ) {
    throw new Error("Writing snapshot contains an invalid protocol.");
  }
  const lesson = getLessonById("en", value.band as Band, value.lessonId);
  const sourceProtocol = lesson?.practice?.writing;
  if (
    !lesson || !sourceProtocol || lesson.unitId !== value.unitId || lesson.tier !== value.tier ||
    lesson.title !== value.title || lesson.topic !== value.topic ||
    sourceProtocol.goal !== value.goal || sourceProtocol.instruction !== value.instruction ||
    sourceProtocol.constraints?.length !== value.constraints.length ||
    sourceProtocol.constraints?.some((constraint, index) => constraint !== value.constraints[index]) ||
    sourceProtocol.feedback_boundary !== "FEEDBACK_ONLY_NO_REPLACEMENT"
  ) {
    throw new Error("Writing protocol does not resolve to its supplied lesson.");
  }
}

export function validateWritingSnapshot(value: unknown): asserts value is WritingSnapshot {
  if (!isRecord(value)) throw new Error("Writing snapshot metadata is invalid.");
  hasOnlyFields(value, ["schemaVersion", "inventoryVersion", "protocols"], "Writing snapshot");
  if (value.schemaVersion !== "1.0" || !isString(value.inventoryVersion) || !Array.isArray(value.protocols) || value.protocols.length !== 300) {
    throw new Error("Writing snapshot metadata is invalid.");
  }
  const ids = new Set<string>();
  const lessonIds = new Set<string>();
  const counts = new Map<Band, number>();
  for (const protocol of value.protocols) {
    validateProtocol(protocol);
    if (ids.has(protocol.id) || lessonIds.has(protocol.lessonId)) throw new Error("Writing snapshot contains duplicate protocol bindings.");
    ids.add(protocol.id);
    lessonIds.add(protocol.lessonId);
    counts.set(protocol.band, (counts.get(protocol.band) ?? 0) + 1);
  }
  for (const band of bands) {
    if (counts.get(band) !== 50) throw new Error("Writing snapshot has an incomplete band inventory.");
  }
}

const candidateSnapshot: unknown = rawSnapshot;
validateWritingSnapshot(candidateSnapshot);
export const writingSnapshot = candidateSnapshot;

export function getWritingProtocols(filters: Partial<Pick<WritingProtocol, "band" | "tier" | "unitId" | "topic" | "lessonId">> = {}): readonly WritingProtocol[] {
  return writingSnapshot.protocols.filter((protocol) => Object.entries(filters).every(([field, value]) => protocol[field as keyof WritingProtocol] === value));
}

export function getWritingBands(): readonly Band[] {
  return [...new Set(writingSnapshot.protocols.map((protocol) => protocol.band))];
}

export function getWritingTiers(band?: Band): readonly string[] {
  return [...new Set(getWritingProtocols(band ? { band } : {}).map((protocol) => protocol.tier))];
}

export function getWritingProtocol(protocolId: string): WritingProtocol | undefined {
  return writingSnapshot.protocols.find((protocol) => protocol.id === protocolId);
}

export function getWritingProtocolForLesson(lessonId: string): WritingProtocol | undefined {
  return writingSnapshot.protocols.find((protocol) => protocol.lessonId === lessonId);
}
