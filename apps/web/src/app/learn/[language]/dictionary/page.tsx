import type { Metadata } from "next";
import Link from "next/link";
import { notFound } from "next/navigation";
import { DictionaryWorkspace } from "@/components/dictionary-workspace";
import { getLanguageConfiguration } from "@/content/languages";
import { dictionaryHref, languageHref, learnHref } from "@/lib/routes";

export const dynamicParams = false;

export function generateStaticParams() {
  return [{ language: "en" }];
}

export async function generateMetadata({ params }: { params: Promise<{ language: string }> }): Promise<Metadata> {
  const { language } = await params;
  return { title: language === "en" ? "English Dictionary / Language Library" : "Dictionary not found" };
}

export default async function DictionaryPage({ params }: { params: Promise<{ language: string }> }) {
  const { language } = await params;
  if (language !== "en") notFound();
  const configuration = getLanguageConfiguration("en");
  if (!configuration) notFound();
  return <div className="page-shell catalog-page">
    <nav aria-label="Breadcrumb"><Link href={learnHref()}>Learn</Link><span aria-hidden="true"> / </span><Link href={languageHref("en")}>{configuration.name}</Link><span aria-hidden="true"> / </span><Link href={dictionaryHref()}>Dictionary</Link></nav>
    <DictionaryWorkspace />
  </div>;
}
