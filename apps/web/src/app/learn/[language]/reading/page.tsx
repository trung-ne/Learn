import type { Metadata } from "next";
import Link from "next/link";
import { notFound } from "next/navigation";
import { ReadingWorkspace } from "@/components/reading-workspace";
import { languageHref, learnHref } from "@/lib/routes";

export const dynamicParams = false;

export function generateStaticParams() {
  return [{ language: "en" }];
}

export async function generateMetadata({ params }: { params: Promise<{ language: string }> }): Promise<Metadata> {
  const { language } = await params;
  return { title: language === "en" ? "Reading" : "Reading not found" };
}

export default async function ReadingPage({ params }: { params: Promise<{ language: string }> }) {
  const { language } = await params;
  if (language !== "en") notFound();
  return (
    <div className="page-shell catalog-page">
      <nav aria-label="Breadcrumb"><Link href={learnHref()}>Learn</Link><span aria-hidden="true"> / </span><Link href={languageHref("en")}>English</Link><span aria-hidden="true"> / </span><span aria-current="page">Reading</span></nav>
      <ReadingWorkspace />
    </div>
  );
}
