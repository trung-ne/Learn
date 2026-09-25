import type { Metadata } from "next";
import Link from "next/link";
import { notFound } from "next/navigation";
import { getLanguage, getLanguages } from "@/content/catalog";
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

  return (
    <div className="page-shell catalog-page">
      <nav aria-label="Breadcrumb"><Link href={learnHref()}>Learn</Link><span aria-hidden="true"> / </span><span>{configuration.name}</span></nav>
      <section className="catalog-hero">
        <div>
          <p className="eyebrow">{language.toUpperCase()} · {configuration.nativeName}</p>
          <h1>{configuration.name}</h1>
          <p className="lede">{summary.lessonCount} available lessons across the current course levels.</p>
        </div>
      </section>

      <section className="level-grid" aria-label={`${configuration.name} available levels`}>
        {configuration.availableLevels.map((level) => (
          <Link className="level-card" href={levelHref(language, level)} key={level}>
            <span className="eyebrow">Course level</span>
            <h2>{level}</h2>
            <p>{summary.bands.includes(level) ? "Browse lessons and local practice." : "No lesson packets are currently available."}</p>
            <span aria-hidden="true">→</span>
          </Link>
        ))}
      </section>
    </div>
  );
}
