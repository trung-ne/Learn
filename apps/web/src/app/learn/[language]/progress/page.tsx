import type { Metadata } from "next";
import Link from "next/link";
import { notFound } from "next/navigation";
import { ProgressDashboard } from "@/components/progress-dashboard";
import { getAvailableCourses, getLanguages, getLessonsForLanguageLevel, isLanguageCode } from "@/content/catalog";
import { getLanguageConfiguration } from "@/content/languages";
import { languageHref, learnHref } from "@/lib/routes";

export const dynamicParams = false;

export function generateStaticParams() {
  return getLanguages().map((language) => ({ language: language.code }));
}

export async function generateMetadata({ params }: { params: Promise<{ language: string }> }): Promise<Metadata> {
  const { language } = await params;
  const configuration = getLanguageConfiguration(language);
  return { title: configuration && isLanguageCode(language) ? `${configuration.name} progress` : "Progress dashboard not found" };
}

export default async function LanguageProgressPage({ params }: { params: Promise<{ language: string }> }) {
  const { language } = await params;
  if (!isLanguageCode(language)) notFound();
  const configuration = getLanguageConfiguration(language);
  if (!configuration) notFound();
  const courses = getAvailableCourses(language).map((course) => ({
    language,
    level: course.level,
    lessons: getLessonsForLanguageLevel(language, course.level).map((lesson) => ({
      lessonId: lesson.lessonId,
      unitId: lesson.unitId,
    })),
  }));

  return (
    <div className="page-shell catalog-page">
      <nav aria-label="Breadcrumb"><Link href={learnHref()}>Learn</Link><span aria-hidden="true"> / </span><Link href={languageHref(language)}>{configuration.name}</Link><span aria-hidden="true"> / </span><span aria-current="page">Progress</span></nav>
      <ProgressDashboard language={language} courses={courses} />
    </div>
  );
}
