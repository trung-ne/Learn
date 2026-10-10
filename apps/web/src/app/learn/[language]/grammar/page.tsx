import type { Metadata } from "next";
import Link from "next/link";
import { notFound } from "next/navigation";
import { GrammarWorkspace } from "@/components/grammar-workspace";
import { getGrammarTargets } from "@/content/grammar-catalog";
import { isLanguageCode } from "@/content/languages";
import { languageHref, learnHref } from "@/lib/routes";

export const dynamicParams = false;

export function generateStaticParams() {
  return getGrammarTargets("en").length ? [{ language: "en" }] : [];
}

export async function generateMetadata({ params }: { params: Promise<{ language: string }> }): Promise<Metadata> {
  const { language } = await params;
  return { title: language === "en" ? "Grammar practice" : "Grammar practice not found" };
}

export default async function GrammarPage({ params }: { params: Promise<{ language: string }> }) {
  const { language } = await params;
  if (!isLanguageCode(language) || language !== "en" || !getGrammarTargets(language).length) notFound();

  return (
    <div className="page-shell catalog-page">
      <nav aria-label="Breadcrumb">
        <Link href={learnHref()}>Learn</Link><span aria-hidden="true"> / </span>
        <Link href={languageHref(language)}>English</Link><span aria-hidden="true"> / </span>
        <span aria-current="page">Grammar practice</span>
      </nav>
      <GrammarWorkspace />
    </div>
  );
}
