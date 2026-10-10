import type { Metadata } from "next";
import Link from "next/link";
import { notFound } from "next/navigation";
import { AssessmentRunner } from "@/components/assessment-runner";
import { getAssessmentPackage, getAssessmentPackages } from "@/content/assessment-catalog";
import { assessmentHref, learnHref } from "@/lib/routes";

export const dynamicParams = false;

export function generateStaticParams() {
  return getAssessmentPackages().map((assessment) => ({ language: "en", assessmentId: assessment.id }));
}

export async function generateMetadata({ params }: { params: Promise<{ language: string; assessmentId: string }> }): Promise<Metadata> {
  const { language, assessmentId } = await params;
  const assessment = language === "en" ? getAssessmentPackage(assessmentId) : undefined;
  return { title: assessment ? `${assessment.type.replaceAll("_", " ")} · English assessment` : "Assessment not found" };
}

export default async function AssessmentPackagePage({ params }: { params: Promise<{ language: string; assessmentId: string }> }) {
  const { language, assessmentId } = await params;
  const assessment = language === "en" ? getAssessmentPackage(assessmentId) : undefined;
  if (!assessment) {
    notFound();
    return null;
  }
  return <div className="page-shell">
    <nav aria-label="Breadcrumb"><Link href={learnHref()}>Learn</Link><span aria-hidden="true"> / </span><Link href={assessmentHref()}>English assessment</Link><span aria-hidden="true"> / </span><span aria-current="page">{assessment.type.replaceAll("_", " ")}</span></nav>
    <AssessmentRunner assessment={assessment} />
  </div>;
}
