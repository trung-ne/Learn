import type { DisplayLesson } from "./types";

export type EnglishDisplayLesson = DisplayLesson & {
  readonly language: "en";
  readonly packetFamily: "english-full";
};

export type GermanDisplayLesson = DisplayLesson & {
  readonly language: "de";
  readonly packetFamily: "german-pilot";
};

export function asEnglishLesson(lesson: DisplayLesson): EnglishDisplayLesson {
  if (lesson.packetFamily !== "english-full") {
    throw new Error(`Lesson ${lesson.lessonId} is not an English Full packet projection.`);
  }
  return lesson as EnglishDisplayLesson;
}

export function asGermanLesson(lesson: DisplayLesson): GermanDisplayLesson {
  if (lesson.packetFamily !== "german-pilot") {
    throw new Error(`Lesson ${lesson.lessonId} is not a German pilot packet projection.`);
  }
  return lesson as GermanDisplayLesson;
}

export function adaptSnapshotLesson(lesson: DisplayLesson): EnglishDisplayLesson | GermanDisplayLesson {
  return lesson.packetFamily === "english-full" ? asEnglishLesson(lesson) : asGermanLesson(lesson);
}
