"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import type { HomeCourse } from "@/components/home-learning";
import { assessmentSnapshot } from "@/content/assessment-catalog";
import { grammarSnapshot } from "@/content/grammar-catalog";
import { vocabularySnapshot } from "@/content/vocabulary-catalog";
import {
  buildTodayRecommendations,
  type TodayRecommendation,
} from "@/lib/adaptive-learning";
import { loadAssessmentProgress } from "@/lib/assessment-progress";
import { loadGrammarProgress } from "@/lib/grammar-progress";
import type { CourseProgress, LocalLearner } from "@/lib/progress";
import { loadVocabularyProgress } from "@/lib/vocabulary-progress";

export function TodayRecommendations({
  learner,
  course,
  courseProgress,
}: {
  readonly learner: LocalLearner;
  readonly course: HomeCourse;
  readonly courseProgress: CourseProgress;
}) {
  const [recommendations, setRecommendations] = useState<readonly TodayRecommendation[]>();

  useEffect(() => {
    const vocabularyProgress = course.language === "en"
      ? loadVocabularyProgress({ learnerId: learner.learnerId, language: "en" }, vocabularySnapshot.inventoryVersion)
      : undefined;
    const grammarProgress = course.language === "en"
      ? loadGrammarProgress({ learnerId: learner.learnerId, language: "en" }, grammarSnapshot.inventoryVersion)
      : undefined;
    const assessmentProgress = course.language === "en"
      ? loadAssessmentProgress({ learnerId: learner.learnerId, language: "en" })
      : undefined;
    setRecommendations(buildTodayRecommendations({
      course,
      courseProgress,
      now: new Date().toISOString(),
      vocabularyProgress,
      grammarProgress,
      assessmentProgress,
    }));
  }, [course, courseProgress, learner]);

  if (!recommendations) return null;

  return (
    <section className="today-recommendations" aria-labelledby="today-heading" aria-live="polite">
      <div className="section-heading">
        <div><p className="eyebrow">Today</p><h2 id="today-heading">TODAY</h2></div>
        <p>Suggestions use activity saved in this browser. They are not proficiency or mastery ratings.</p>
      </div>
      {recommendations.length ? (
        <ol className="today-recommendation-list">
          {recommendations.map((recommendation) => (
            <li key={recommendation.category}>
              <article className="today-recommendation-card">
                <div>
                  <p className="eyebrow">{recommendation.category.replaceAll("_", " ")}</p>
                  <h3>{recommendation.title}</h3>
                  <p>{recommendation.detail}</p>
                  {recommendation.durationMinutes && <small>Supplied lesson duration: {recommendation.durationMinutes} minutes.</small>}
                </div>
                <Link className="secondary-button" href={recommendation.href}>{recommendation.actionLabel}</Link>
              </article>
            </li>
          ))}
        </ol>
      ) : <p className="empty-state">Open an available lesson to create local learning activity.</p>}
    </section>
  );
}
