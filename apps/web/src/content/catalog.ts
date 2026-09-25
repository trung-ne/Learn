import rawSnapshot from "./generated/curriculum-snapshot.json";
import { getLanguageConfiguration, isAvailableLevel, isLanguageCode, languages } from "./languages";
import type {
  Band,
  CurriculumSnapshot,
  DisplayLesson,
  LanguageCode,
  LanguageSummary,
} from "./types";

function validateSnapshot(value: unknown): asserts value is CurriculumSnapshot {
  if (!value || typeof value !== "object") throw new Error("Curriculum snapshot must be an object.");
  const candidate = value as Partial<CurriculumSnapshot>;
  if (candidate.schemaVersion !== "1.0" || candidate.contentStatus !== "UNREVIEWED") {
    throw new Error("Unsupported curriculum snapshot metadata.");
  }
  if (!Array.isArray(candidate.lessons) || candidate.lessons.length !== 310) {
    throw new Error("Curriculum snapshot must contain exactly 310 lessons.");
  }
  if (!Array.isArray(candidate.languages) || candidate.languages.length !== Object.keys(languages).length) {
    throw new Error("Curriculum snapshot language inventory is unsupported.");
  }

  const identities = new Set<string>();
  for (const summary of candidate.languages) {
    if (!isLanguageCode(summary.code)) throw new Error("Curriculum snapshot has an unsupported language.");
    const configuration = getLanguageConfiguration(summary.code);
    if (!configuration || summary.name !== configuration.name) {
      throw new Error("Curriculum snapshot language metadata drifted.");
    }
  }
  for (const lesson of candidate.lessons) {
    if (!isLanguageCode(lesson.language) || lesson.contentStatus !== "UNREVIEWED") {
      throw new Error("Curriculum snapshot contains an unsupported lesson.");
    }
    if (!isAvailableLevel(lesson.language, lesson.band)) {
      throw new Error(`Lesson ${lesson.lessonId} has an unavailable level.`);
    }
    const identity = `${lesson.language}:${lesson.lessonId}`;
    if (identities.has(identity)) throw new Error(`Duplicate lesson identity: ${identity}`);
    identities.add(identity);
  }
}

const candidateSnapshot: unknown = rawSnapshot;
validateSnapshot(candidateSnapshot);
export const snapshot = candidateSnapshot;

export function getLanguages(): readonly LanguageSummary[] {
  return snapshot.languages;
}

export function getLanguage(code: string): LanguageSummary | undefined {
  if (!isLanguageCode(code)) return undefined;
  return snapshot.languages.find((language) => language.code === code);
}

export function getLessonsForLanguage(code: LanguageCode): readonly DisplayLesson[] {
  return snapshot.lessons.filter((lesson) => lesson.language === code);
}

export function getLessonsForLanguageLevel(
  language: LanguageCode,
  level: Band,
): readonly DisplayLesson[] {
  return snapshot.lessons.filter((lesson) => lesson.language === language && lesson.band === level);
}

export function getLesson(
  language: string,
  level: string,
  unitId: string,
  lessonId: string,
): DisplayLesson | undefined {
  if (!isLanguageCode(language) || !isAvailableLevel(language, level)) return undefined;
  return snapshot.lessons.find(
    (lesson) =>
      lesson.language === language &&
      lesson.band === level &&
      lesson.unitId === unitId &&
      lesson.lessonId === lessonId,
  );
}

export function groupLessonsByTierAndUnit(
  lessons: readonly DisplayLesson[],
): ReadonlyMap<string, ReadonlyMap<string, readonly DisplayLesson[]>> {
  const tiers = new Map<string, Map<string, DisplayLesson[]>>();
  for (const lesson of lessons) {
    const units = tiers.get(lesson.tier) ?? new Map<string, DisplayLesson[]>();
    const unitLessons = units.get(lesson.unitId) ?? [];
    unitLessons.push(lesson);
    units.set(lesson.unitId, unitLessons);
    tiers.set(lesson.tier, units);
  }
  return tiers;
}

export { isAvailableLevel, isLanguageCode };
