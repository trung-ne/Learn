import type { Metadata } from "next";
import Link from "next/link";
import { notFound } from "next/navigation";
import { UnifiedReviewWorkspace } from "@/components/unified-review-workspace";
import { OfflineReviewControl } from "@/components/pwa-manager";
import { getAvailableCourses, isAvailableCourse, isLanguageCode } from "@/content/catalog";
import { getLanguageConfiguration } from "@/content/languages";
import { languageHref, levelHref } from "@/lib/routes";

export const dynamicParams = false;

export function generateStaticParams() {
  return getAvailableCourses().map((course) => ({ language: course.language, level: course.level }));
}

export async function generateMetadata({ params }: { params: Promise<{ language: string; level: string }> }): Promise<Metadata> {
  const { language, level } = await params;
  const configuration = getLanguageConfiguration(language);
  return {
    title: configuration && isLanguageCode(language) && isAvailableCourse(language, level)
      ? `${configuration.name} ${level} review`
      : "Review not found",
  };
}

export default async function CourseReviewPage({ params }: { params: Promise<{ language: string; level: string }> }) {
  const { language, level } = await params;
  if (!isLanguageCode(language) || !isAvailableCourse(language, level)) notFound();
  const configuration = getLanguageConfiguration(language);
  if (!configuration) notFound();

  return (
    <main className="page-shell catalog-page">
      <nav aria-label="Breadcrumb">
        <Link href={languageHref(language)}>{configuration.name}</Link><span aria-hidden="true"> / </span>
        <Link href={levelHref(language, level)}>{level}</Link><span aria-hidden="true"> / </span>
        <span aria-current="page">Review</span>
      </nav>
      <UnifiedReviewWorkspace language={language} course={level} />
      <OfflineReviewControl />
    </main>
  );
}
