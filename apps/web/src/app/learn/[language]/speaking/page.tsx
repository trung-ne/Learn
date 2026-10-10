import type { Metadata } from "next";
import Link from "next/link";
import { notFound } from "next/navigation";
import { SpeakingWorkspace } from "@/components/speaking-workspace";
import { getSpeakingLanguages } from "@/content/speaking-catalog";
import { isLanguageCode } from "@/content/languages";
import { languageHref, learnHref } from "@/lib/routes";

export const dynamicParams = false;

export function generateStaticParams() {
  return getSpeakingLanguages().map((language) => ({ language }));
}

export async function generateMetadata({ params }: { params: Promise<{ language: string }> }): Promise<Metadata> {
  const { language } = await params;
  return { title: language === "en" ? "Speaking self-practice" : language === "de" ? "Sprech-Selbstübung" : "Speaking not found" };
}

export default async function SpeakingPage({ params }: { params: Promise<{ language: string }> }) {
  const { language } = await params;
  if (!isLanguageCode(language) || !getSpeakingLanguages().includes(language)) notFound();
  const languageName = language === "en" ? "English" : "German";
  return (
    <div className="page-shell catalog-page">
      <nav aria-label="Breadcrumb"><Link href={learnHref()}>Learn</Link><span aria-hidden="true"> / </span><Link href={languageHref(language)}>{languageName}</Link><span aria-hidden="true"> / </span><span aria-current="page">Speaking self-practice</span></nav>
      <SpeakingWorkspace language={language} />
    </div>
  );
}
