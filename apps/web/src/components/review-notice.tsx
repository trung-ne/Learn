import Link from "next/link";
import type { CourseLevel, LanguageCode } from "@/content/types";
import { courseMistakesHref, courseReviewHref } from "@/lib/routes";

export function ReviewNotice({
  language,
  course,
}: {
  readonly language: LanguageCode;
  readonly course: CourseLevel;
}) {
  return (
    <section className="review-notice" aria-labelledby="review-heading">
      <p className="eyebrow">Review</p>
      <h2 id="review-heading">Return to scheduled practice</h2>
      <p>Review uses locally stored activity outcomes and word schedules. It is not a learning diagnosis or placement result.</p>
      <div className="button-row">
        <Link className="secondary-button" href={courseReviewHref(language, course)}>Open review</Link>
        <Link className="text-button" href={courseMistakesHref(language, course)}>View activity outcomes</Link>
      </div>
    </section>
  );
}
