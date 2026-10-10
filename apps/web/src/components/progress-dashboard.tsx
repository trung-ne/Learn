"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import type { LanguageCode } from "@/content/types";
import { assessmentHref, grammarHref, levelHref, personalStudyPlanHref, vocabularyHref } from "@/lib/routes";
import { grammarSnapshot } from "@/content/grammar-catalog";
import { vocabularySnapshot } from "@/content/vocabulary-catalog";
import {
  buildProgressDashboard,
  type ProgressDashboardCourse,
  type ProgressDashboardSummary,
} from "@/lib/progress-dashboard";
import { loadAssessmentProgress } from "@/lib/assessment-progress";
import { loadGrammarProgress } from "@/lib/grammar-progress";
import { loadLearner, loadProgress } from "@/lib/progress";
import { loadReviewProgress } from "@/lib/review-progress";
import { loadVocabularyProgress } from "@/lib/vocabulary-progress";

function percentage(correct: number, total: number): string {
  return `${Math.round((correct / total) * 100)}%`;
}

export function ProgressDashboard({
  language,
  courses,
}: {
  readonly language: LanguageCode;
  readonly courses: readonly ProgressDashboardCourse[];
}) {
  const [summary, setSummary] = useState<ProgressDashboardSummary>();

  useEffect(() => {
    const learner = loadLearner();
    const courseProgress = Object.fromEntries(courses.map((course) => [
      course.level,
      loadProgress({ learnerId: learner.learnerId, language, course: course.level }),
    ]));
    const reviewProgress = Object.fromEntries(courses.map((course) => [
      course.level,
      loadReviewProgress({ learnerId: learner.learnerId, language, course: course.level }),
    ]));
    setSummary(buildProgressDashboard({
      learnerId: learner.learnerId,
      language,
      courses,
      courseProgress,
      reviewProgress,
      vocabularyProgress: loadVocabularyProgress({ learnerId: learner.learnerId, language }, vocabularySnapshot.inventoryVersion),
      ...(language === "en" ? {
        grammarProgress: loadGrammarProgress({ learnerId: learner.learnerId, language: "en" }, grammarSnapshot.inventoryVersion),
        assessmentProgress: loadAssessmentProgress({ learnerId: learner.learnerId, language: "en" }),
      } : {}),
      now: new Date().toISOString(),
    }));
  }, [courses, language]);

  if (!summary) return <p className="empty-state">Loading browser-local progress…</p>;

  return (
    <div className="content-stack progress-dashboard" lang={language}>
      <section className="catalog-hero progress-dashboard-hero">
        <div>
          <p className="eyebrow">Browser-local progress</p>
          <h1>Progress dashboard</h1>
          <p className="lede">This summary uses activity saved in this browser. It is not a proficiency record, CEFR result, diagnosis, certification, or course unlock.</p>
        </div>
      </section>

      <section className="progress-dashboard-notice" aria-labelledby="study-plan-link-heading">
        <div>
          <p className="eyebrow">Browser-local planning</p>
          <h2 id="study-plan-link-heading">Personal Study Plan</h2>
          <p>Organize supplied course packets and saved reviews with a learner-selected daily planning allocation. It is not a prediction or proficiency result.</p>
        </div>
        <Link className="secondary-button" href={personalStudyPlanHref(language)}>Open study plan</Link>
      </section>

      <section className="page-section" aria-labelledby="course-progress-heading">
        <div className="section-heading">
          <div><p className="eyebrow">Course packets</p><h2 id="course-progress-heading">Available course activity</h2></div>
          <p>Course labels organize supplied packets; completing packets does not establish CEFR attainment.</p>
        </div>
        <div className="progress-course-list">
          {summary.courses.map((course) => (
            <article className="progress-course-card" key={course.level}>
              <div><h3>{course.level}</h3><p>{course.completedLessons} / {course.suppliedLessons} supplied lessons locally complete.</p></div>
              <div className="progress-course-meter"><progress value={course.completedLessons} max={course.suppliedLessons} aria-label={`${course.level} locally complete lessons`} /><strong>{course.completionPercent}%</strong></div>
              <Link className="secondary-button" href={levelHref(language, course.level)}>Open {course.level}</Link>
            </article>
          ))}
        </div>
      </section>

      <section className="page-section" aria-labelledby="skill-evidence-heading">
        <div className="section-heading">
          <div><p className="eyebrow">Direct local evidence</p><h2 id="skill-evidence-heading">Skills</h2></div>
          <p>Only supplied objective activity results are shown as results. Self-marked practice is listed separately and is not a skill score.</p>
        </div>
        <div className="progress-skill-grid">
          {summary.directSkillEvidence.map((skill) => (
            <article className="progress-skill-card" key={skill.label}>
              <h3>{skill.label}</h3>
              {skill.status === "AVAILABLE" ? <><strong>{percentage(skill.correct!, skill.total!)}</strong><p>{skill.correct} / {skill.total} submitted supplied items.</p></> : <><strong>{skill.status}</strong><p>{skill.limitation}</p></>}
              {skill.status === "AVAILABLE" && <small>{skill.limitation}</small>}
              {skill.label === "Vocabulary" && language === "en" && <Link href={vocabularyHref("en")}>Open vocabulary</Link>}
              {skill.label === "Grammar" && language === "en" && <Link href={grammarHref("en")}>Open grammar</Link>}
              {skill.label === "Reading" && language === "en" && <Link href={assessmentHref()}>Open assessment</Link>}
              {skill.label === "Listening" && language === "en" && <Link href={assessmentHref()}>Open assessment</Link>}
            </article>
          ))}
        </div>
      </section>

      <section className="page-section" aria-labelledby="practice-activity-heading">
        <div className="section-heading">
          <div><p className="eyebrow">Self-marked supplied practice</p><h2 id="practice-activity-heading">Practice activity</h2></div>
          <p>These are local completion markers only. They do not score speaking, writing, pronunciation, or audio listening.</p>
        </div>
        <dl className="progress-summary-grid">
          <div><dt>Listening prompts</dt><dd>{summary.practiceActivity.listeningProtocolsMarkedComplete}</dd></div>
          <div><dt>Speaking prompts</dt><dd>{summary.practiceActivity.speakingProtocolsMarkedComplete}</dd></div>
          <div><dt>Pronunciation prompts</dt><dd>{summary.practiceActivity.pronunciationProtocolsMarkedComplete}</dd></div>
          <div><dt>Writing prompts</dt><dd>{summary.practiceActivity.writingProtocolsMarkedComplete}</dd></div>
        </dl>
      </section>

      <section className="progress-state-grid" aria-label="Vocabulary and grammar local state">
        <article className="page-section progress-state-card">
          <div className="section-heading"><div><p className="eyebrow">Vocabulary</p><h2>Local WordSense state</h2></div>{language === "en" && <Link href={vocabularyHref("en")}>Open vocabulary</Link>}</div>
          {summary.vocabulary.availability === "AVAILABLE" ? <dl className="progress-summary-grid">
            <div><dt>Supplied senses</dt><dd>{summary.vocabulary.suppliedSenses}</dd></div>
            <div><dt>Locally mastered</dt><dd>{summary.vocabulary.locallyMasteredSenses}</dd></div>
            <div><dt>Learning or reviewing</dt><dd>{summary.vocabulary.activeSenses}</dd></div>
            <div><dt>Recorded mistakes</dt><dd>{summary.vocabulary.sensesWithRecordedMistakes}</dd></div>
            <div><dt>Due now</dt><dd>{summary.vocabulary.dueSenses}</dd></div>
          </dl> : <p className="empty-state">No supplied browser-local vocabulary inventory is available for this language.</p>}
        </article>

        <article className="page-section progress-state-card">
          <div className="section-heading"><div><p className="eyebrow">Grammar</p><h2>Local target state</h2></div>{language === "en" && <Link href={grammarHref("en")}>Open grammar</Link>}</div>
          {summary.grammar.availability === "AVAILABLE" ? <dl className="progress-summary-grid">
            <div><dt>Supplied targets</dt><dd>{summary.grammar.suppliedTargets}</dd></div>
            <div><dt>Locally consolidated</dt><dd>{summary.grammar.locallyConsolidatedTargets}</dd></div>
            <div><dt>Practising or reviewing</dt><dd>{summary.grammar.activeTargets}</dd></div>
            <div><dt>Recorded incorrect outcomes</dt><dd>{summary.grammar.targetsWithRecordedIncorrectOutcomes}</dd></div>
            <div><dt>Due now</dt><dd>{summary.grammar.dueTargets}</dd></div>
          </dl> : <p className="empty-state">No supplied browser-local grammar inventory is available for this language.</p>}
        </article>
      </section>

      <section className="page-section" aria-labelledby="review-outcomes-heading">
        <div className="section-heading"><div><p className="eyebrow">Objective review records</p><h2 id="review-outcomes-heading">Local review outcomes</h2></div><p>Review scheduling and correct outcomes are not a retention measurement.</p></div>
        <dl className="progress-summary-grid">
          <div><dt>Reviewed activities</dt><dd>{summary.review.reviewedActivities}</dd></div>
          <div><dt>Review outcomes</dt><dd>{summary.review.reviewOutcomes}</dd></div>
          <div><dt>Correct outcomes</dt><dd>{summary.review.correctOutcomes}</dd></div>
          <div><dt>Incorrect outcomes</dt><dd>{summary.review.incorrectOutcomes}</dd></div>
          <div><dt>Due activities</dt><dd>{summary.review.dueActivities}</dd></div>
          <div><dt>Latest incorrect in seven days</dt><dd>{summary.review.recentIncorrectActivities}</dd></div>
        </dl>
      </section>

      <section className="progress-limitations-grid" aria-label="Unavailable progress measures">
        <article><p className="eyebrow">Review retention</p><h2>{summary.retentionStatus}</h2><p>The app records review scheduling and objective outcomes, not a delayed-retention measurement.</p></article>
        <article><p className="eyebrow">Study time</p><h2>{summary.studyTimeStatus}</h2><p>Lesson duration and timestamps are not elapsed study-time records.</p></article>
        <article><p className="eyebrow">Mistake trends</p><h2>{summary.mistakeTrendStatus}</h2><p>The app retains aggregate outcomes, not a timestamped history for daily or weekly trend lines.</p></article>
      </section>

      <section className="page-section" aria-labelledby="mistake-pattern-heading">
        <div className="section-heading"><div><p className="eyebrow">Current objective outcome patterns</p><h2 id="mistake-pattern-heading">Recorded mistakes</h2></div><p>These are aggregate local outcomes, not causal explanations or a learning diagnosis.</p></div>
        <dl className="progress-summary-grid">
          <div><dt>Activities with incorrect outcomes</dt><dd>{summary.activityOutcomes.activitiesWithRecordedIncorrectOutcomes}</dd></div>
          <div><dt>Repeated incorrect patterns</dt><dd>{summary.activityOutcomes.repeatedIncorrectOutcomePatterns}</dd></div>
          <div><dt>Recent incorrect patterns</dt><dd>{summary.activityOutcomes.recentIncorrectOutcomePatterns}</dd></div>
        </dl>
      </section>
    </div>
  );
}
