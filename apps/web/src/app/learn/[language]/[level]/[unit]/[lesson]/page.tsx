import type { Metadata } from "next";
import Link from "next/link";
import { notFound } from "next/navigation";
import { LessonInteractions } from "@/components/lesson-interactions";
import type { ContentSection } from "@/content/types";
import { getLesson, snapshot } from "@/content/catalog";
import { getLanguageConfiguration } from "@/content/languages";
import { languageHref, learnHref, levelHref } from "@/lib/routes";

export const dynamicParams = false;

const sectionGroups = [
  { key: "vocabulary", eyebrow: "Words and phrases", heading: "Vocabulary" },
  { key: "grammar", eyebrow: "Language patterns", heading: "Grammar" },
  { key: "explanation", eyebrow: "Understand", heading: "Explanation" },
  { key: "example", eyebrow: "Models", heading: "Examples" },
  { key: "common_mistakes", eyebrow: "Watch out", heading: "Common mistakes" },
  { key: "pronunciation", eyebrow: "Say it clearly", heading: "Pronunciation" },
] as const;

function SectionCards({
  sections,
  language,
}: {
  readonly sections: readonly ContentSection[];
  readonly language: "en" | "de";
}) {
  return (
    <div className="content-stack" lang={language}>
      {sections.map((section) => (
        <article key={section.id}>
          <h3>{section.title}</h3>
          <p>{section.body}</p>
          {section.vietnameseTip && <aside className="vietnamese-tip" lang="vi"><strong>Gợi ý tiếng Việt</strong><p>{section.vietnameseTip}</p></aside>}
        </article>
      ))}
    </div>
  );
}

export function generateStaticParams() {
  return snapshot.lessons.map((item) => ({
    language: item.language,
    level: item.band,
    unit: item.unitId,
    lesson: item.lessonId,
  }));
}

export async function generateMetadata({ params }: { params: Promise<{ language: string; level: string; unit: string; lesson: string }> }): Promise<Metadata> {
  const { language, level, unit, lesson: lessonId } = await params;
  const lesson = getLesson(language, level, unit, lessonId);
  return { title: lesson?.title ?? "Lesson not found" };
}

export default async function LessonPage({ params }: { params: Promise<{ language: string; level: string; unit: string; lesson: string }> }) {
  const { language, level, unit, lesson: lessonId } = await params;
  const lesson = getLesson(language, level, unit, lessonId);
  if (!lesson) notFound();
  const configuration = getLanguageConfiguration(lesson.language);
  if (!configuration) notFound();

  const sections = lesson.sections ?? [];
  const groupedIds = new Set(sectionGroups.map((group) => group.key));
  const generalSections = sections.filter((section) => !groupedIds.has(section.type));

  return (
    <div className="page-shell lesson-page">
      <nav aria-label="Breadcrumb">
        <Link href={learnHref()}>Learn</Link><span aria-hidden="true"> / </span>
        <Link href={languageHref(lesson.language)}>{configuration.name}</Link><span aria-hidden="true"> / </span>
        <Link href={levelHref(lesson.language, lesson.band)}>{lesson.band}</Link><span aria-hidden="true"> / </span>
        <span aria-current="page">{lesson.title}</span>
      </nav>

      <header className="lesson-hero">
        <div className="lesson-kicker"><span>CEFR {lesson.band}</span><span>{lesson.durationMinutes} minutes</span></div>
        <h1 lang={lesson.language}>{lesson.title}</h1>
        {lesson.languageFocus && <p className="lede" lang={lesson.language}>{lesson.languageFocus}</p>}
        <dl className="lesson-meta"><div><dt>Topic</dt><dd lang={lesson.language}>{lesson.topic}</dd></div><div><dt>Target language</dt><dd>{configuration.nativeName}</dd></div></dl>
      </header>

      {lesson.objectives?.length ? (
        <section className="page-section objectives" aria-labelledby="objectives-heading">
          <p className="eyebrow">Lesson outcomes</p><h2 id="objectives-heading">Objectives</h2>
          <ul lang={lesson.language}>{lesson.objectives.map((objective) => <li key={objective}>{objective}</li>)}</ul>
        </section>
      ) : null}

      {sectionGroups.map((group) => {
        const matching = sections.filter((section) => section.type === group.key);
        return matching.length ? (
          <section className="page-section" aria-labelledby={`${group.key}-heading`} key={group.key}>
            <p className="eyebrow">{group.eyebrow}</p><h2 id={`${group.key}-heading`}>{group.heading}</h2>
            <SectionCards sections={matching} language={lesson.language} />
          </section>
        ) : null;
      })}

      {generalSections.length ? (
        <section className="page-section" aria-labelledby="lesson-content-heading">
          <p className="eyebrow">Read and notice</p><h2 id="lesson-content-heading">Lesson content</h2>
          <SectionCards sections={generalSections} language={lesson.language} />
        </section>
      ) : sections.length === 0 ? (
        <section className="page-section empty-state"><h2>Lesson content is not available</h2><p>This lesson packet does not currently include learner-facing explanation sections.</p></section>
      ) : null}

      <LessonInteractions lesson={lesson} />
    </div>
  );
}
