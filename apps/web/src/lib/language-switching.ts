import type { CourseSummary } from "@/content/catalog";
import type { LanguageCode } from "@/content/types";
import { languageHref, levelHref } from "@/lib/routes";

const coursePath = /^\/learn\/(en|de)\/([A-Z]\d)(?:\/|$)/u;

export function switchDestination(
  pathname: string,
  language: LanguageCode,
  courses: readonly Pick<CourseSummary, "language" | "level">[],
): string {
  const current = pathname.match(coursePath);
  const currentLevel = current?.[2];
  if (currentLevel && courses.some((course) => course.language === language && course.level === currentLevel)) {
    return levelHref(language, currentLevel);
  }
  return languageHref(language);
}
