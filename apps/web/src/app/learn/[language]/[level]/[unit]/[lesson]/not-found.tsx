import Link from "next/link";
import { learnHref } from "@/lib/routes";

export default function LessonNotFound() {
  return (
    <div className="page-shell empty-page">
      <p className="eyebrow">Lesson unavailable</p>
      <h1>This lesson is not in the current course.</h1>
      <p className="lede">Choose from the available languages and course levels to continue learning.</p>
      <Link className="primary-link" href={learnHref()}>Browse available courses</Link>
    </div>
  );
}
