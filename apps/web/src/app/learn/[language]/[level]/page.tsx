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
import { getUnitTest } from "@/content/assessment-catalog";
import { getLanguageConfiguration } from "@/content/languages";
import { assessmentHref, assessmentPackageHref, languageHref, learnHref, lessonHref, progressDashboardHref, tutorHref } from "@/lib/routes";

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

      <section className="progress-dashboard-notice" aria-labelledby="course-progress-heading">
        <div>
          <p className="eyebrow">Browser-local activity</p>
          <h2 id="course-progress-heading">See progress across supplied course levels</h2>
          <p>Course completion and local evidence are shown separately from proficiency, CEFR attainment, and lesson access.</p>
        </div>
        <Link className="secondary-button" href={progressDashboardHref(language)}>Open progress dashboard</Link>
      </section>

      <section className="tutor-course-notice" aria-labelledby="tutor-context-heading">
        <div>
          <p className="eyebrow">Tutor Context</p>
          <h2 id="tutor-context-heading">Prepare a bounded AI practice prompt</h2>
          <p>Choose a self-reported band and local practice goals, then explicitly copy a minimized context into an external AI tool.</p>
        </div>
        <Link className="secondary-button" href={tutorHref(language, level)}>Open Tutor Context</Link>
      </section>

      {language === "en" && <section className="assessment-course-notice" aria-labelledby="assessment-heading">
        <div>
          <p className="eyebrow">Assessment</p>
          <h2 id="assessment-heading">Build local evidence beyond lesson completion</h2>
          <p>Use supplied quizzes and checkpoints for factual browser-local results. They do not unlock, certify, or diagnose this level.</p>
        </div>
        <Link className="secondary-button" href={assessmentHref()}>Open assessment</Link>
      </section>}

      {[...grouped.entries()].map(([tier, units]) => (
        <section className="tier-section" key={tier} aria-labelledby={`tier-${tier.replace(".", "-")}`}>
          <div className="tier-heading"><h2 id={`tier-${tier.replace(".", "-")}`}>{tier}</h2><span>Internal curriculum tier</span></div>
          {[...units.entries()].map(([unitId, unitLessons]) => {
            const unitTest = language === "en" ? getUnitTest(unitId) : undefined;
            return <section className="unit-section" key={unitId} aria-labelledby={unitId}>
              <div className="unit-heading-row">
                <h3 id={unitId}>{unitLabel(unitId)}</h3>
                {unitTest && <Link className="text-button" href={assessmentPackageHref(unitTest.id)}>Unit checkpoint</Link>}
              </div>
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
            </section>;
          })}
        </section>
      ))}

      <ReviewNotice language={language} course={level} />
    </div>
  );
}
