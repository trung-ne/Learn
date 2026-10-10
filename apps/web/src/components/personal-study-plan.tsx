"use client";

import Link from "next/link";
import { useCallback, useEffect, useMemo, useState } from "react";
import type { CourseLevel, LanguageCode } from "@/content/types";
import { grammarSnapshot } from "@/content/grammar-catalog";
import { vocabularySnapshot } from "@/content/vocabulary-catalog";
import { loadGrammarProgress, type GrammarProgress } from "@/lib/grammar-progress";
import {
  buildPersonalStudyPlan,
  type PersonalStudyPlan,
  type StudyPlanCourse,
} from "@/lib/personal-study-plan";
import { loadLearner, loadProgress, type CourseProgress } from "@/lib/progress";
import { loadReviewProgress, type ReviewProgress } from "@/lib/review-progress";
import { courseReviewHref, grammarHref, vocabularyHref } from "@/lib/routes";
import {
  BAND_ORDER,
  compareBands,
  DAILY_ALLOCATION_OPTIONS,
  loadTutorPreferences,
  saveTutorPreferences,
  type DailyAllocationMinutes,
  type TutorPreferences,
} from "@/lib/tutor-context";
import { loadVocabularyProgress, type VocabularyProgress } from "@/lib/vocabulary-progress";

interface LocalPlanState {
  readonly learnerId: string;
  readonly preferences: TutorPreferences;
  readonly courseProgress: Readonly<Record<CourseLevel, CourseProgress | undefined>>;
  readonly reviewProgress: Readonly<Record<CourseLevel, ReviewProgress | undefined>>;
  readonly vocabularyProgress?: VocabularyProgress;
  readonly grammarProgress?: GrammarProgress;
  readonly now: string;
}

export function PersonalStudyPlanWorkspace({
  language,
  courses,
}: {
  readonly language: LanguageCode;
  readonly courses: readonly StudyPlanCourse[];
}) {
  const [state, setState] = useState<LocalPlanState>();

  const refresh = useCallback(() => {
    const learner = loadLearner();
    const scope = { learnerId: learner.learnerId, language };
    const levels = courses.map((course) => course.level);
    setState({
      learnerId: learner.learnerId,
      preferences: loadTutorPreferences(scope),
      courseProgress: Object.fromEntries(levels.map((level) => [level, loadProgress({ ...scope, course: level })])),
      reviewProgress: Object.fromEntries(levels.map((level) => [level, loadReviewProgress({ ...scope, course: level })])),
      ...(language === "en" ? {
        vocabularyProgress: loadVocabularyProgress(scope, vocabularySnapshot.inventoryVersion),
        grammarProgress: loadGrammarProgress({ learnerId: learner.learnerId, language: "en" }, grammarSnapshot.inventoryVersion),
      } : {}),
      now: new Date().toISOString(),
    });
  }, [courses, language]);

  useEffect(() => {
    refresh();
    const onStorage = (event: StorageEvent) => {
      if (!event.key || event.storageArea !== window.localStorage) return;
      refresh();
    };
    window.addEventListener("focus", refresh);
    window.addEventListener("storage", onStorage);
    return () => {
      window.removeEventListener("focus", refresh);
      window.removeEventListener("storage", onStorage);
    };
  }, [refresh]);

  const plan = useMemo<PersonalStudyPlan | undefined>(() => state && buildPersonalStudyPlan({
    language,
    learnerId: state.learnerId,
    preferences: state.preferences,
    courses,
    courseProgress: state.courseProgress,
    reviewProgress: state.reviewProgress,
    vocabularyProgress: state.vocabularyProgress,
    grammarProgress: state.grammarProgress,
    reviewHref: (level) => courseReviewHref(language, level),
    ...(language === "en" ? { vocabularyHref: vocabularyHref("en"), grammarHref: grammarHref("en") } : {}),
    now: state.now,
  }), [courses, language, state]);

  function updatePreferences(update: Partial<Pick<TutorPreferences, "currentBand" | "targetBand" | "dailyAllocationMinutes">>) {
    if (!state) return;
    const currentBandChanged = Object.hasOwn(update, "currentBand");
    const next: TutorPreferences = {
      ...state.preferences,
      ...update,
      ...(currentBandChanged && (!update.currentBand || (state.preferences.targetBand && compareBands(state.preferences.targetBand, update.currentBand) <= 0))
        ? { targetBand: undefined }
        : {}),
    };
    if (!saveTutorPreferences(next)) return;
    setState((current) => current ? { ...current, preferences: next, now: new Date().toISOString() } : current);
  }

  const targetOptions = state?.preferences.currentBand
    ? BAND_ORDER.filter((band) => compareBands(band, state.preferences.currentBand!) > 0)
    : [];

  if (!state || !plan) return <p className="empty-state">Loading browser-local study-plan preferences…</p>;

  return (
    <div className="content-stack personal-study-plan" lang={language}>
      <section className="catalog-hero personal-study-plan-hero">
        <div>
          <p className="eyebrow">Browser-local planning</p>
          <h1>Personal Study Plan</h1>
          <p className="lede">Organize supplied course packets and saved review activity with your learner-reported bands and planned daily allocation.</p>
        </div>
      </section>

      <section className="study-plan-boundary" aria-labelledby="study-plan-boundary-heading">
        <h2 id="study-plan-boundary-heading">Planning boundary</h2>
        <p>Your current and goal bands are your choices, not proficiency, placement, or CEFR-attainment results. Supplied lesson durations are planning inputs, not elapsed study time, pace, completion predictions, retention, mastery, scores, diagnoses, or course access rules.</p>
      </section>

      <section className="study-plan-config" aria-labelledby="study-plan-config-heading">
        <p className="eyebrow">Learner choices</p>
        <h2 id="study-plan-config-heading">Set a supplied-curriculum plan</h2>
        <div className="study-plan-fields">
          <label>Self-reported current band
            <select aria-label="Study plan current band" value={state.preferences.currentBand ?? ""} onChange={(event) => updatePreferences({ currentBand: event.target.value ? event.target.value as CourseLevel : undefined })}>
              <option value="">Choose a band</option>
              {BAND_ORDER.map((band) => <option key={band} value={band}>{band}</option>)}
            </select>
          </label>
          <label>Aspirational target band
            <select aria-label="Study plan target band" disabled={!state.preferences.currentBand} value={state.preferences.targetBand ?? ""} onChange={(event) => updatePreferences({ targetBand: event.target.value ? event.target.value as CourseLevel : undefined })}>
              <option value="">Choose a higher goal</option>
              {targetOptions.map((band) => <option key={band} value={band}>{band}</option>)}
            </select>
          </label>
          <label>Planned minutes per day
            <select aria-label="Study plan daily allocation" value={state.preferences.dailyAllocationMinutes ?? ""} onChange={(event) => updatePreferences({ dailyAllocationMinutes: event.target.value ? Number(event.target.value) as DailyAllocationMinutes : undefined })}>
              <option value="">Choose minutes</option>
              {DAILY_ALLOCATION_OPTIONS.map((minutes) => <option key={minutes} value={minutes}>{minutes} minutes</option>)}
            </select>
          </label>
        </div>
      </section>

      {plan.status === "UNAVAILABLE" ? <section className="page-section study-plan-unavailable"><h2>Plan unavailable</h2><p>{plan.reason}</p><p>This does not mean content is locked or that a learner has not met a requirement.</p></section> : <>
        <section className="page-section" aria-labelledby="study-plan-estimate-heading">
          <div className="section-heading"><div><p className="eyebrow">Supplied curriculum allocation</p><h2 id="study-plan-estimate-heading">{plan.currentBand} remainder → {plan.targetBand}</h2></div><p>Arithmetic from the remaining supplied packet display durations and your selected daily planning allocation.</p></div>
          <dl className="progress-summary-grid">
            <div><dt>Remaining supplied packets</dt><dd>{plan.remainingLessons.length}</dd></div>
            <div><dt>Supplied display duration</dt><dd>{plan.remainingSuppliedDisplayMinutes} min</dd></div>
            <div><dt>Planned daily blocks</dt><dd>{plan.plannedDailyBlocks}</dd></div>
            <div><dt>Seven-day planning blocks</dt><dd>{plan.plannedWeeklyBlocks}</dd></div>
          </dl>
        </section>

        <section className="page-section" aria-labelledby="study-plan-today-heading">
          <div className="section-heading"><div><p className="eyebrow">Today’s planning allocation</p><h2 id="study-plan-today-heading">Daily plan</h2></div><p>{plan.reviewAllocationMinutes} minutes reserved for saved review planning; {plan.lessonAllocationMinutes} minutes for supplied packet display duration.</p></div>
          <div className="study-plan-action-grid">
            {plan.reviewQuota.length ? plan.reviewQuota.map((item) => <article key={item.source}><h3>{item.source}</h3><p>{item.itemCount} saved due or recent-review item{item.itemCount === 1 ? "" : "s"} in the local quota.</p><Link href={item.href}>Open saved review</Link></article>) : <article><h3>Review quota</h3><p>No matching saved due review item is currently available.</p></article>}
            {plan.dailyLessons.length ? plan.dailyLessons.map((lesson) => <article key={lesson.lessonId}><h3>{lesson.title}</h3><p>{lesson.level} · {lesson.durationMinutes} supplied display minutes</p><Link href={lesson.href}>Open packet</Link></article>) : <article><h3>Packet allocation</h3><p>The next supplied packet is longer than today’s packet display-duration allocation. Open it when you choose; this plan does not track or require a schedule.</p></article>}
          </div>
        </section>

        <section className="page-section" aria-labelledby="study-plan-skill-heading">
          <div className="section-heading"><div><p className="eyebrow">Available-practice rotation</p><h2 id="study-plan-skill-heading">Skill balance</h2></div><p>These are supplied activity categories, not measures of ability or scores.</p></div>
          {plan.availablePracticeFocus.length ? <ul className="study-plan-focus-list">{plan.availablePracticeFocus.map((skill) => <li key={skill}>{skill}</li>)}</ul> : <p className="empty-state">No supplied practice categories are available for this corridor.</p>}
        </section>

        <section className="page-section" aria-labelledby="study-plan-weekly-heading">
          <div className="section-heading"><div><p className="eyebrow">Sequential planning blocks</p><h2 id="study-plan-weekly-heading">Weekly targets</h2></div><p>Blocks are catalog-ordered packet groups. They have no dates, deadlines, or adherence tracking.</p></div>
          <div className="study-plan-week-list">{plan.weeklyBlocks.map((block) => <article key={block.blockNumber}><h3>Block {block.blockNumber}: {block.levels.join(" → ")}</h3><p>{block.lessons.length} supplied packet{block.lessons.length === 1 ? "" : "s"} · {block.suppliedDisplayMinutes} display minutes</p><ol>{block.lessons.map((lesson) => <li key={lesson.lessonId}><Link href={lesson.href}>{lesson.title}</Link> <span>{lesson.level} · {lesson.durationMinutes} min</span></li>)}</ol></article>)}</div>
        </section>
      </>}
      <button type="button" className="secondary-button" onClick={refresh}>Refresh local plan</button>
    </div>
  );
}
