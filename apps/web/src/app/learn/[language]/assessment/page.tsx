import type { Metadata } from "next";
import { notFound } from "next/navigation";
import { AssessmentHub } from "@/components/assessment-hub";

export const dynamicParams = false;

export function generateStaticParams() {
  return [{ language: "en" }];
}

export async function generateMetadata({ params }: { params: Promise<{ language: string }> }): Promise<Metadata> {
  const { language } = await params;
  return { title: language === "en" ? "English assessment" : "Assessment not found" };
}

export default async function AssessmentPage({ params }: { params: Promise<{ language: string }> }) {
  const { language } = await params;
  if (language !== "en") notFound();
  return <div className="page-shell"><AssessmentHub /></div>;
}
