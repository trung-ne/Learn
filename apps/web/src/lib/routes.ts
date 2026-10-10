import type { DisplayLesson, LanguageCode } from "@/content/types";

export function learnHref(): string {
  return "/learn";
}

export function languageHref(language: LanguageCode): string {
  return `${learnHref()}/${language}`;
}

export function levelHref(language: LanguageCode, level: string): string {
  return `${languageHref(language)}/${level}`;
}

export function progressDashboardHref(language: LanguageCode): string {
  return `${languageHref(language)}/progress`;
}

export function personalStudyPlanHref(language: LanguageCode): string {
  return `${languageHref(language)}/plan`;
}

export function vocabularyHref(language: LanguageCode): string {
  return `${languageHref(language)}/vocabulary`;
}

export function dictionaryHref(language: "en" = "en"): string {
  return `${languageHref(language)}/dictionary`;
}

export function grammarHref(language: "en"): string {
  return `${languageHref(language)}/grammar`;
}

export function listeningHref(language: "en"): string {
  return `${languageHref(language)}/listening`;
}

export function pronunciationHref(language: LanguageCode): string {
  return `${languageHref(language)}/pronunciation`;
}

export function speakingHref(language: LanguageCode): string {
  return `${languageHref(language)}/speaking`;
}

export function readingHref(language: "en"): string {
  return `${languageHref(language)}/reading`;
}

export function writingHref(language: "en"): string {
  return `${languageHref(language)}/writing`;
}

export function courseReviewHref(language: LanguageCode, level: string): string {
  return `${levelHref(language, level)}/review`;
}

export function courseMistakesHref(language: LanguageCode, level: string): string {
  return `${levelHref(language, level)}/mistakes`;
}

export function assessmentHref(language: "en" = "en"): string {
  return `${languageHref(language)}/assessment`;
}

export function assessmentPackageHref(assessmentId: string): string {
  return `${assessmentHref()}/${assessmentId}`;
}

export function tutorHref(language: LanguageCode, level: string): string {
  return `${levelHref(language, level)}/tutor`;
}

export function lessonPacketHref(
  language: LanguageCode,
  level: string,
  unitId: string,
  lessonId: string,
): string {
  return `${levelHref(language, level)}/${unitId}/${lessonId}`;
}

export function lessonHref(lesson: DisplayLesson): string {
  return lessonPacketHref(lesson.language, lesson.band, lesson.unitId, lesson.lessonId);
}
