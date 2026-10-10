import type { Metadata } from "next";
import Link from "next/link";
import { notFound } from "next/navigation";
import { PersonalStudyPlanWorkspace } from "@/components/personal-study-plan";
import { getAvailableCourses, getLanguages, getLessonsForLanguageLevel, isLanguageCode } from "@/content/catalog";
import { getLanguageConfiguration } from "@/content/languages";
import { isObjectiveExerciseType } from "@/lib/review-progress";
import { languageHref, learnHref, lessonHref } from "@/lib/routes";

export const dynamicParams = false;

export function generateStaticParams() {
  return getLanguages().map((language) => ({ language: language.code }));
}

export async function generateMetadata({ params }: { params: Promise<{ language: string }> }): Promise<Metadata> {
  const { language } = await params;
  const configuration = getLanguageConfiguration(language);
  return { title: configuration && isLanguageCode(language) ? `${configuration.name} study plan` : "Study plan not found" };
}

export default async function PersonalStudyPlanPage({ params }: { params: Promise<{ language: string }> }) {
  const { language } = await params;
  if (!isLanguageCode(language)) notFound();
  const configuration = getLanguageConfiguration(language);
  if (!configuration) notFound();
  const courses = getAvailableCourses(language).map((course) => ({
    language,
    level: course.level,
    lessons: getLessonsForLanguageLevel(language, course.level).map((lesson) => ({
      lessonId: lesson.lessonId,
      title: lesson.title,
      level: lesson.band,
      sequence: lesson.sequence,
      durationMinutes: lesson.durationMinutes,
      href: lessonHref(lesson),
      exerciseTypes: lesson.exercises?.map((exercise) => exercise.type) ?? [],
      objectiveExerciseIds: lesson.exercises?.filter((exercise) => isObjectiveExerciseType(exercise.type)).map((exercise) => exercise.id) ?? [],
      practiceModalities: Object.keys(lesson.practice ?? {}) as ("listening" | "speaking" | "pronunciation" | "writing")[],
    })),
  }));

  return (
    <div className="page-shell catalog-page">
      <nav aria-label="Breadcrumb"><Link href={learnHref()}>Learn</Link><span aria-hidden="true"> / </span><Link href={languageHref(language)}>{configuration.name}</Link><span aria-hidden="true"> / </span><span aria-current="page">Study plan</span></nav>
      <PersonalStudyPlanWorkspace language={language} courses={courses} />
    </div>
  );
}
