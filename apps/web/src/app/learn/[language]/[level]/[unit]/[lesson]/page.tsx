import type { Metadata } from "next";
import Link from "next/link";
import { notFound } from "next/navigation";
import { LessonInteractions } from "@/components/lesson-interactions";
import { getLesson, snapshot } from "@/content/catalog";
import { getLanguageConfiguration } from "@/content/languages";
import { languageHref, learnHref, levelHref } from "@/lib/routes";

export const dynamicParams = false;

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
  const manifest = snapshot.sourceManifests.find((source) => source.language === lesson.language && source.band === lesson.band);

  return (
    <div className="page-shell lesson-page">
      <nav aria-label="Breadcrumb">
        <Link href={learnHref()}>Learn</Link><span aria-hidden="true"> / </span>
        <Link href={languageHref(lesson.language)}>{configuration.name}</Link><span aria-hidden="true"> / </span>
        <Link href={levelHref(lesson.language, lesson.band)}>{lesson.band}</Link><span aria-hidden="true"> / </span>
        <span>{lesson.title}</span>
      </nav>

      <header className="lesson-hero">
        <div className="lesson-kicker"><span>{lesson.tier}</span><span>{lesson.durationMinutes} minutes</span><span>{lesson.contentStatus}</span></div>
        <h1>{lesson.title}</h1>
        <p className="lede">{lesson.languageFocus}</p>
        <dl className="lesson-meta">
          <div><dt>Topic</dt><dd>{lesson.topic}</dd></div>
          <div><dt>Lesson ID</dt><dd><code>{lesson.lessonId}</code></dd></div>
          <div><dt>Prerequisites</dt><dd>{lesson.prerequisites.length ? lesson.prerequisites.join(", ") : "None"}</dd></div>
        </dl>
      </header>

      <section className="page-section objectives" aria-labelledby="objectives-heading">
        <p className="eyebrow">Lesson outcomes</p><h2 id="objectives-heading">Objectives</h2>
        <ul>{lesson.objectives.map((objective) => <li key={objective}>{objective}</li>)}</ul>
      </section>

      <section className="page-section" aria-labelledby="lesson-content-heading">
        <p className="eyebrow">Read and notice</p><h2 id="lesson-content-heading">Lesson content</h2>
        <div className="content-stack">
          {lesson.sections.map((section) => (
            <article key={section.id}><span className="section-type">{section.type}</span><h3>{section.title}</h3><p>{section.body}</p></article>
          ))}
        </div>
      </section>

      <LessonInteractions lesson={lesson} />

      <details className="lineage">
        <summary>Content lineage and status</summary>
        <dl>
          <div><dt>Packet family</dt><dd>{lesson.packetFamily}</dd></div>
          <div><dt>Record type</dt><dd>{lesson.recordType}</dd></div>
          <div><dt>Packet path</dt><dd><code>{lesson.packetPath}</code></dd></div>
          <div><dt>Packet SHA-256</dt><dd><code>{lesson.packetSha256}</code></dd></div>
          {manifest && <><div><dt>Source manifest</dt><dd><code>{manifest.path}</code></dd></div><div><dt>Manifest identity</dt><dd><code>{manifest.declaredManifestSha256}</code></dd></div></>}
          <div><dt>Status</dt><dd>{lesson.contentStatus}</dd></div>
        </dl>
      </details>
    </div>
  );
}
