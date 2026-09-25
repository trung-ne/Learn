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

export function lessonHref(lesson: DisplayLesson): string {
  return `${levelHref(lesson.language, lesson.band)}/${lesson.unitId}/${lesson.lessonId}`;
}
