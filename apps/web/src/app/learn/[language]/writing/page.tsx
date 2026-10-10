import { notFound } from "next/navigation";
import { WritingWorkspace } from "@/components/writing-workspace";

export const dynamicParams = false;

export function generateStaticParams() {
  return [{ language: "en" }];
}

export default async function WritingPage({ params }: { readonly params: Promise<{ language: string }> }) {
  const { language } = await params;
  if (language !== "en") notFound();
  return <WritingWorkspace />;
}
