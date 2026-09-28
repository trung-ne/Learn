import type { DisplayLesson } from "./types";

export type EnglishDisplayLesson = DisplayLesson & { readonly language: "en" };
export type GermanDisplayLesson = DisplayLesson & { readonly language: "de" };

export function asEnglishLesson(lesson: DisplayLesson): EnglishDisplayLesson {
  if (lesson.language !== "en") throw new Error(`Lesson ${lesson.lessonId} is not in the English course.`);
  return lesson;
}

export function asGermanLesson(lesson: DisplayLesson): GermanDisplayLesson {
  if (lesson.language !== "de") throw new Error(`Lesson ${lesson.lessonId} is not in the German course.`);
  return lesson;
}

export function adaptSnapshotLesson(lesson: DisplayLesson): EnglishDisplayLesson | GermanDisplayLesson {
  return lesson.language === "en" ? asEnglishLesson(lesson) : asGermanLesson(lesson);
}
