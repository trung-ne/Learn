import type { Metadata } from "next";
import Link from "next/link";
import { notFound } from "next/navigation";
import { TutorContextWorkspace } from "@/components/tutor-context-workspace";
import { getAvailableCourses, isAvailableCourse, isLanguageCode } from "@/content/catalog";
import { getLanguageConfiguration } from "@/content/languages";
import { languageHref, levelHref } from "@/lib/routes";

export const dynamicParams = false;

export function generateStaticParams() {
  return getAvailableCourses().map((course) => ({ language: course.language, level: course.level }));
}

export async function generateMetadata({ params }: { readonly params: Promise<{ language: string; level: string }> }): Promise<Metadata> {
  const { language, level } = await params;
  const configuration = getLanguageConfiguration(language);
  return {
    title: configuration && isLanguageCode(language) && isAvailableCourse(language, level)
      ? `${configuration.name} ${level} Tutor Context`
      : "Tutor Context not found",
  };
}

export default async function TutorContextPage({ params }: { readonly params: Promise<{ language: string; level: string }> }) {
  const { language, level } = await params;
  if (!isLanguageCode(language) || !isAvailableCourse(language, level)) notFound();
  const configuration = getLanguageConfiguration(language);
  if (!configuration) notFound();

  return (
    <main className="page-shell catalog-page">
      <nav aria-label="Breadcrumb">
        <Link href={languageHref(language)}>{configuration.name}</Link><span aria-hidden="true"> / </span>
        <Link href={levelHref(language, level)}>{level}</Link><span aria-hidden="true"> / </span>
        <span aria-current="page">Tutor Context</span>
      </nav>
      <TutorContextWorkspace language={language} course={level} />
    </main>
  );
}
