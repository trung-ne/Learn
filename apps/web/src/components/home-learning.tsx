"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import type { CourseAvailability, CourseLevel, LanguageCode } from "@/content/types";
import { getLanguageConfiguration } from "@/content/languages";
import { languageHref } from "@/lib/routes";
import {
  loadLearner,
  loadProgress,
  setActiveLanguage,
  summarizeCourseProgress,
  type CourseLessonInventory,
  type CourseProgressSummary,
  type LocalLearner,
} from "@/lib/progress";

export interface HomeCourse {
  readonly language: LanguageCode;
  readonly level: CourseLevel;
  readonly lessonCount: number;
  readonly availability: CourseAvailability;
  readonly firstLessonHref: string;
  readonly lessons: readonly CourseLessonInventory[];
  readonly lessonHrefs: Readonly<Record<string, string>>;
}

interface HomeLearningProps {
  readonly courses: readonly HomeCourse[];
}

interface CourseDashboard {
  readonly course: HomeCourse;
  readonly summary: CourseProgressSummary;
  readonly continueHref?: string;
}

function loadDashboards(learner: LocalLearner, courses: readonly HomeCourse[]): readonly CourseDashboard[] {
  return courses.map((course) => {
    const progress = loadProgress({ learnerId: learner.learnerId, language: course.language, course: course.level });
    const summary = summarizeCourseProgress(progress, course.lessons);
    const continueHref = summary.currentLessonId
      ? course.lessonHrefs[summary.currentLessonId]
      : undefined;
    return { course, summary, continueHref };
  });
}

function latestDashboard(dashboards: readonly CourseDashboard[]): CourseDashboard | undefined {
  return dashboards
    .filter((dashboard) => dashboard.continueHref && dashboard.summary.lastAccessedAt)
    .sort((left, right) => {
      const timestampOrder = right.summary.lastAccessedAt!.localeCompare(left.summary.lastAccessedAt!);
      if (timestampOrder !== 0) return timestampOrder;
      return `${left.course.language}-${left.course.level}`.localeCompare(`${right.course.language}-${right.course.level}`);
    })[0];
}

export function HomeLearning({ courses }: HomeLearningProps) {
  const [learner, setLearner] = useState<LocalLearner>();
  const [dashboards, setDashboards] = useState<readonly CourseDashboard[]>([]);

  useEffect(() => {
    const current = loadLearner();
    setLearner(current);
    setDashboards(loadDashboards(current, courses));
  }, [courses]);

  function chooseLanguage(language: LanguageCode) {
    const current = learner ?? loadLearner();
    setLearner(setActiveLanguage(current, language));
  }

  const latest = latestDashboard(dashboards);

  return (
    <section className="home-learning" aria-labelledby="start-learning-heading">
      <div className="section-heading">
        <div><p className="eyebrow">Available courses</p><h2 id="start-learning-heading">Start or continue learning</h2></div>
        <p>Progress stays only in this browser. No account is created.</p>
      </div>

      {latest ? (
        <aside className="continue-card" aria-live="polite">
          <div><p className="eyebrow">Continue learning</p><strong>{getLanguageConfiguration(latest.course.language)?.name} {latest.course.level}</strong></div>
          <Link className="primary-link" href={latest.continueHref!} onClick={() => chooseLanguage(latest.course.language)}>Continue learning</Link>
        </aside>
      ) : (
        <p className="empty-resume">Choose a course to begin. A continue link appears after you open a lesson.</p>
      )}

      <div className="home-course-grid">
        {dashboards.map(({ course, summary, continueHref }) => {
          const configuration = getLanguageConfiguration(course.language);
          if (!configuration) return null;
          return (
            <article className="home-course-card" key={`${course.language}-${course.level}`}>
              <p className="eyebrow">{configuration.nativeName} · {course.level}</p>
              <h3>{configuration.name} {course.level}</h3>
              <p>{summary.totalLessons} available lessons{course.availability === "PILOT" ? " in this pilot" : ""}.</p>
              <p className="course-progress">{summary.completedLessons} / {summary.totalLessons} lessons locally complete.</p>
              <div className="course-actions">
                <Link href={languageHref(course.language)} onClick={() => chooseLanguage(course.language)}>View course</Link>
                <Link
                  className="primary-link"
                  href={continueHref ?? course.firstLessonHref}
                  onClick={() => chooseLanguage(course.language)}
                >
                  {continueHref ? "Continue learning" : "Start lesson"}
                </Link>
              </div>
            </article>
          );
        })}
      </div>
    </section>
  );
}
