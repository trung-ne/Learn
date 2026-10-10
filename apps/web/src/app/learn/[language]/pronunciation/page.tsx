import type { Metadata } from "next";
import Link from "next/link";
import { notFound } from "next/navigation";
import { PronunciationWorkspace } from "@/components/pronunciation-workspace";
import { getPronunciationLanguages } from "@/content/pronunciation-catalog";
import { isLanguageCode } from "@/content/languages";
import { languageHref, learnHref } from "@/lib/routes";

export const dynamicParams = false;

export function generateStaticParams() {
  return getPronunciationLanguages().map((language) => ({ language }));
}

export async function generateMetadata({ params }: { params: Promise<{ language: string }> }): Promise<Metadata> {
  const { language } = await params;
  return { title: language === "en" ? "Pronunciation self-practice" : language === "de" ? "Aussprache-Selbstübung" : "Pronunciation not found" };
}

export default async function PronunciationPage({ params }: { params: Promise<{ language: string }> }) {
  const { language } = await params;
  if (!isLanguageCode(language) || !getPronunciationLanguages().includes(language)) notFound();
  const languageName = language === "en" ? "English" : "German";
  return (
    <div className="page-shell catalog-page">
      <nav aria-label="Breadcrumb"><Link href={learnHref()}>Learn</Link><span aria-hidden="true"> / </span><Link href={languageHref(language)}>{languageName}</Link><span aria-hidden="true"> / </span><span aria-current="page">Pronunciation self-practice</span></nav>
      <PronunciationWorkspace language={language} />
    </div>
  );
}
