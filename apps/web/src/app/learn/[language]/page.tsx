import type { Metadata } from "next";
import Link from "next/link";
import { notFound } from "next/navigation";
import { getAvailableCourses, getLanguage, getLanguages } from "@/content/catalog";
import { getLanguageConfiguration, isLanguageCode } from "@/content/languages";
import { learnHref, levelHref } from "@/lib/routes";

export const dynamicParams = false;

export function generateStaticParams() {
  return getLanguages().map((language) => ({ language: language.code }));
}

export async function generateMetadata({ params }: { params: Promise<{ language: string }> }): Promise<Metadata> {
  const { language } = await params;
  const configuration = getLanguageConfiguration(language);
  return { title: configuration ? `${configuration.name} course` : "Language not found" };
}

export default async function LanguageCoursePage({ params }: { params: Promise<{ language: string }> }) {
  const { language } = await params;
  if (!isLanguageCode(language)) notFound();
  const summary = getLanguage(language);
  const configuration = getLanguageConfiguration(language);
  if (!summary || !configuration) notFound();
  const courses = getAvailableCourses(language);

  return (
    <div className="page-shell catalog-page">
      <nav aria-label="Breadcrumb"><Link href={learnHref()}>Learn</Link><span aria-hidden="true"> / </span><span aria-current="page">{configuration.name}</span></nav>
      <section className="catalog-hero">
        <div>
          <p className="eyebrow">{language.toUpperCase()} · {configuration.nativeName}</p>
          <h1>{configuration.name}</h1>
          <p className="lede">{summary.lessonCount} available lessons across the current course levels.</p>
        </div>
      </section>

      <section className="level-grid" aria-label={`${configuration.name} available levels`}>
        {courses.length ? courses.map((course) => (
          <Link className="level-card" href={levelHref(language, course.level)} key={course.level}>
            <span className="eyebrow">{course.availability === "PILOT" ? "Limited pilot" : "Course level"}</span>
            <div>
              <h2>{course.level}</h2>
              <p>{course.lessonCount} available lessons{course.availability === "PILOT" ? "; this is a limited pilot." : " with local practice."}</p>
            </div>
            <span aria-hidden="true">→</span>
          </Link>
        )) : <p className="empty-state">No lesson packets are available for this language yet.</p>}
      </section>
    </div>
  );
}
