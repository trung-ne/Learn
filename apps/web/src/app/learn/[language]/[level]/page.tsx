import type { Metadata } from "next";
import Link from "next/link";
import { notFound } from "next/navigation";
import { CatalogProgress } from "@/components/catalog-progress";
import { ReviewNotice } from "@/components/review-notice";
import {
  getAvailableCourses,
  getLanguages,
  getLessonsForLanguageLevel,
  groupLessonsByTierAndUnit,
  isAvailableCourse,
  isLanguageCode,
} from "@/content/catalog";
import { getLanguageConfiguration } from "@/content/languages";
import { languageHref, learnHref, lessonHref } from "@/lib/routes";

export const dynamicParams = false;

export function generateStaticParams() {
  return getLanguages().flatMap((language) =>
    language.bands.map((level) => ({ language: language.code, level })),
  );
}

export async function generateMetadata({ params }: { params: Promise<{ language: string; level: string }> }): Promise<Metadata> {
  const { language, level } = await params;
  const configuration = getLanguageConfiguration(language);
  return { title: configuration && isLanguageCode(language) && isAvailableCourse(language, level) ? `${configuration.name} ${level}` : "Course level not found" };
}

function unitLabel(unitId: string): string {
  const match = unitId.match(/-u(\d+)$/iu);
  return match ? `Unit ${Number(match[1])}` : unitId;
}

export default async function LevelCatalogPage({ params }: { params: Promise<{ language: string; level: string }> }) {
  const { language, level } = await params;
  if (!isLanguageCode(language) || !isAvailableCourse(language, level)) notFound();
  const configuration = getLanguageConfiguration(language);
  if (!configuration) notFound();
  const lessons = getLessonsForLanguageLevel(language, level);
  const course = getAvailableCourses(language).find((item) => item.level === level);
  if (lessons.length === 0 || !course) notFound();
  const grouped = groupLessonsByTierAndUnit(lessons);

  return (
    <div className="page-shell catalog-page">
      <nav aria-label="Breadcrumb">
        <Link href={learnHref()}>Learn</Link><span aria-hidden="true"> / </span>
        <Link href={languageHref(language)}>{configuration.name}</Link><span aria-hidden="true"> / </span>
        <span aria-current="page">{level}</span>
      </nav>
      <section className="catalog-hero">
        <div>
          <p className="eyebrow">{configuration.nativeName} · course level {level}</p>
          <h1>{configuration.name} {level}</h1>
          <p className="lede">{lessons.length} available lesson packets, grouped by internal curriculum tier and unit.{course.availability === "PILOT" ? " This is a limited pilot, not a complete course level." : ""}</p>
        </div>
        <CatalogProgress
          language={language}
          course={level}
          languageName={configuration.name}
          lessons={lessons.map((lesson) => ({ lessonId: lesson.lessonId, unitId: lesson.unitId }))}
        />
      </section>

      {[...grouped.entries()].map(([tier, units]) => (
        <section className="tier-section" key={tier} aria-labelledby={`tier-${tier.replace(".", "-")}`}>
          <div className="tier-heading"><h2 id={`tier-${tier.replace(".", "-")}`}>{tier}</h2><span>Internal curriculum tier</span></div>
          {[...units.entries()].map(([unitId, unitLessons]) => (
            <section className="unit-section" key={unitId} aria-labelledby={unitId}>
              <h3 id={unitId}>{unitLabel(unitId)}</h3>
              <ol className="lesson-list">
                {unitLessons.map((lesson) => (
                  <li key={lesson.lessonId}>
                    <Link href={lessonHref(lesson)}>
                      <span className="lesson-number">{String(lesson.sequence).padStart(2, "0")}</span>
                      <span><strong>{lesson.title}</strong><small>{lesson.topic} · {lesson.durationMinutes} min</small></span>
                      <span aria-hidden="true">→</span>
                    </Link>
                  </li>
                ))}
              </ol>
            </section>
          ))}
        </section>
      ))}

      <ReviewNotice />
    </div>
  );
}
