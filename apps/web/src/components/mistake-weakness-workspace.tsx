"use client";

import Link from "next/link";
import { useEffect, useMemo, useState } from "react";
import type { CourseLevel, LanguageCode } from "@/content/types";
import { deriveActivityOutcomePatterns } from "@/lib/mistake-weakness";
import { loadLearner, setActiveLanguage } from "@/lib/progress";
import { emptyReviewProgress, loadReviewProgress, type ReviewProgress } from "@/lib/review-progress";
import { courseReviewHref, lessonPacketHref } from "@/lib/routes";

export function MistakeWeaknessWorkspace({
  language,
  course,
}: {
  readonly language: LanguageCode;
  readonly course: CourseLevel;
}) {
  const [progress, setProgress] = useState<ReviewProgress>(() =>
    emptyReviewProgress({ learnerId: "local-unavailable", language, course }),
  );
  const [ready, setReady] = useState(false);

  useEffect(() => {
    setReady(false);
    const learner = setActiveLanguage(loadLearner(), language);
    setProgress(loadReviewProgress({ learnerId: learner.learnerId, language, course }));
    setReady(true);
  }, [course, language]);

  const now = new Date().toISOString();
  const patterns = useMemo(
    () => deriveActivityOutcomePatterns(progress, language, course, now),
    [course, language, now, progress],
  );

  return (
    <div className="content-stack mistake-workspace" lang={language}>
      <section className="catalog-hero mistake-hero">
        <div>
          <p className="eyebrow">Local activity record</p>
          <h1>Activity outcome patterns</h1>
          <p className="lede">See repeated objectively checked outcomes, then return to the supplied lesson or review activity.</p>
        </div>
        <dl className="vocabulary-summary" aria-label="Activity outcome summary">
          <div><dt>Activities shown</dt><dd>{patterns.length}</dd></div>
          <div><dt>Repeated outcomes</dt><dd>{patterns.filter((pattern) => pattern.hasRepeatedIncorrectOutcomes).length}</dd></div>
        </dl>
      </section>

      {!ready ? <p className="empty-state">Loading local activity records…</p> : patterns.length ? (
        <section className="page-section mistake-pattern-list" aria-labelledby="patterns-heading">
          <div className="section-heading">
            <div><p className="eyebrow">Observed outcomes</p><h2 id="patterns-heading">Supplied activities to revisit</h2></div>
            <p>These counts are local activity records, not a learning diagnosis or proficiency result.</p>
          </div>
          <ol>
            {patterns.map((pattern) => (
              <li key={pattern.id} className="mistake-pattern-card">
                <div>
                  <p className="eyebrow">{pattern.lessonTopic} · activity record</p>
                  <h3>{pattern.lessonTitle}</h3>
                  <p><strong>Incorrect outcomes recorded:</strong> {pattern.incorrectCount} of {pattern.reviewCount} ({pattern.incorrectOutcomePercent}%).</p>
                  {pattern.hasRepeatedIncorrectOutcomes ? <p className="outcome-flag">Repeated incorrect outcomes</p> : null}
                  <p>Latest checked result: <strong>{pattern.lastResult}</strong></p>
                  {pattern.associatedObjectives.length ? (
                    <details>
                      <summary>Associated lesson objectives</summary>
                      <ul>{pattern.associatedObjectives.map((objective) => <li key={objective}>{objective}</li>)}</ul>
                    </details>
                  ) : null}
                </div>
                <div className="button-row">
                  <Link className="secondary-button" href={lessonPacketHref(language, course, pattern.unitId, pattern.lessonId)}>Open lesson</Link>
                  <Link className="secondary-button" href={courseReviewHref(language, course)}>Open review</Link>
                </div>
              </li>
            ))}
          </ol>
        </section>
      ) : (
        <section className="page-section" aria-labelledby="patterns-empty-heading">
          <p className="eyebrow">No current pattern</p>
          <h2 id="patterns-empty-heading">No incorrect objective outcomes are recorded for this course.</h2>
          <p>When an objectively checked supplied activity records an incorrect result, its local aggregate outcome may appear here.</p>
          <Link className="secondary-button" href={courseReviewHref(language, course)}>Open review</Link>
        </section>
      )}
    </div>
  );
}
