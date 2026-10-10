"use client";

import Link from "next/link";
import { useEffect, useMemo, useState } from "react";
import { getLessonById } from "@/content/catalog";
import { getGrammarTargets, grammarSnapshot } from "@/content/grammar-catalog";
import type { Band, CourseLevel, LanguageCode } from "@/content/types";
import { getVocabularySense, getVocabularySenses, vocabularySnapshot } from "@/content/vocabulary-catalog";
import { loadGrammarProgress, emptyGrammarProgress, selectGrammarReviewQueue, type GrammarProgress } from "@/lib/grammar-progress";
import { deriveActivityOutcomePatterns } from "@/lib/mistake-weakness";
import { emptyProgress, loadLearner, loadProgress, setActiveLanguage, type CourseProgress } from "@/lib/progress";
import {
  emptyReviewProgress,
  isObjectiveExerciseType,
  isRecentIncorrect,
  loadReviewProgress,
  reviewItemId,
  selectReviewCandidates,
  type ReviewCandidate,
  type ReviewProgress,
} from "@/lib/review-progress";
import { courseMistakesHref, courseReviewHref, levelHref } from "@/lib/routes";
import {
  BAND_ORDER,
  TUTOR_GOALS,
  compareBands,
  emptyTutorPreferences,
  isCourseCompatible,
  loadTutorPreferences,
  projectTutorContext,
  saveTutorPreferences,
  serializeTutorContext,
  type TutorContextSources,
  type TutorGoal,
  type TutorPreferences,
} from "@/lib/tutor-context";
import { emptyVocabularyProgress, loadVocabularyProgress, selectVocabularyReviewQueue, type VocabularyProgress } from "@/lib/vocabulary-progress";

function labelForSense(sense: ReturnType<typeof getVocabularySense>): string | undefined {
  if (!sense) return undefined;
  const label = `${sense.lemma} (${sense.partOfSpeech}, sense ${sense.senseNumber}): ${sense.definition}`;
  return label.length <= 160 ? label : undefined;
}

function labelForGrammar(target: ReturnType<typeof getGrammarTargets>[number] | undefined): string | undefined {
  if (!target) return undefined;
  const label = `${target.title}: ${target.topic}`;
  return label.length <= 160 ? label : undefined;
}

export function TutorContextWorkspace({
  language,
  course,
}: {
  readonly language: LanguageCode;
  readonly course: CourseLevel;
}) {
  const [preferences, setPreferences] = useState<TutorPreferences>(() =>
    emptyTutorPreferences({ learnerId: "local-unavailable", language }),
  );
  const [courseProgress, setCourseProgress] = useState<CourseProgress>(() =>
    emptyProgress({ learnerId: "local-unavailable", language, course }),
  );
  const [reviewProgress, setReviewProgress] = useState<ReviewProgress>(() =>
    emptyReviewProgress({ learnerId: "local-unavailable", language, course }),
  );
  const [vocabularyProgress, setVocabularyProgress] = useState<VocabularyProgress>(() =>
    emptyVocabularyProgress({ learnerId: "local-unavailable", language }, vocabularySnapshot.inventoryVersion),
  );
  const [grammarProgress, setGrammarProgress] = useState<GrammarProgress>(() =>
    emptyGrammarProgress({ learnerId: "local-unavailable", language: "en" }, grammarSnapshot.inventoryVersion),
  );
  const [ready, setReady] = useState(false);
  const [copyStatus, setCopyStatus] = useState<"idle" | "copied" | "failed">("idle");

  useEffect(() => {
    setReady(false);
    const learner = setActiveLanguage(loadLearner(), language);
    const scope = { learnerId: learner.learnerId, language };
    setPreferences(loadTutorPreferences(scope));
    setCourseProgress(loadProgress({ ...scope, course }));
    setReviewProgress(loadReviewProgress({ ...scope, course }));
    setVocabularyProgress(loadVocabularyProgress(scope, vocabularySnapshot.inventoryVersion));
    if (language === "en") {
      setGrammarProgress(loadGrammarProgress({ learnerId: learner.learnerId, language: "en" }, grammarSnapshot.inventoryVersion));
    } else {
      setGrammarProgress(emptyGrammarProgress({ learnerId: learner.learnerId, language: "en" }, grammarSnapshot.inventoryVersion));
    }
    setCopyStatus("idle");
    setReady(true);
  }, [course, language]);

  const contextSources = useMemo<TutorContextSources>(() => {
    const now = new Date().toISOString();
    const recentLessons = Object.entries(courseProgress.lessons)
      .flatMap(([lessonId, progress]) => {
        const lesson = getLessonById(language, course, lessonId);
        return lesson && progress.lastAccessedAt ? [{ title: lesson.title, accessedAt: progress.lastAccessedAt }] : [];
      })
      .sort((left, right) => right.accessedAt.localeCompare(left.accessedAt) || left.title.localeCompare(right.title))
      .map(({ title }, recencyOrder) => ({ title, recencyOrder }));

    const vocabulary = getVocabularySenses(language).flatMap((sense, order) => {
      if (compareBands(sense.band, course) > 0) return [];
      const progress = vocabularyProgress.senses[sense.id];
      const label = labelForSense(sense);
      return progress && label ? [{ label, state: progress.state, order }] : [];
    });

    const grammar = language === "en" ? getGrammarTargets("en").flatMap((target, order) => {
      if (compareBands(target.band, course) > 0) return [];
      const progress = grammarProgress.targets[target.id];
      const label = labelForGrammar(target);
      return progress && label ? [{ label, state: progress.state, order }] : [];
    }) : [];

    const outcomePatterns = deriveActivityOutcomePatterns(reviewProgress, language, course, now).flatMap((pattern, order) => {
      const label = `${pattern.lessonTitle}: ${pattern.lessonTopic}`;
      return label.length <= 160 ? [{
        label,
        incorrectOutcomes: pattern.incorrectCount,
        reviewCount: pattern.reviewCount,
        recentIncorrect: pattern.isRecentIncorrect,
        repeatedIncorrect: pattern.hasRepeatedIncorrectOutcomes,
        order,
      }] : [];
    });

    const objectiveCandidates = Object.values(reviewProgress.items).flatMap((item, order) => {
      const lesson = getLessonById(language, course, item.lessonId);
      const exercise = lesson?.exercises?.find((candidate) => candidate.id === item.exerciseId);
      if (!lesson || !exercise || !isObjectiveExerciseType(exercise.type) || item.nextReviewAt > now) return [];
      return [{
        source: "objective_exercise" as const,
        id: reviewItemId(item.lessonId, item.exerciseId),
        dueAt: item.nextReviewAt,
        priority: isRecentIncorrect(item, now) ? "recent_incorrect" as const : "due" as const,
        order,
      }];
    });
    const vocabularyCandidates = getVocabularySenses(language).flatMap((sense, order) => {
      if (sense.band !== course || !vocabularyProgress.senses[sense.id]) return [];
      const progress = vocabularyProgress.senses[sense.id]!;
      if (progress.nextReviewAt > now) return [];
      return [{
        source: "vocabulary_sense" as const,
        id: sense.id,
        dueAt: progress.nextReviewAt,
        priority: progress.lastMistakeAt && Date.parse(progress.lastMistakeAt) >= Date.parse(now) - 7 * 24 * 60 * 60_000
          ? "recent_incorrect" as const
          : "due" as const,
        order,
      }];
    });
    const selectedReviewItems = selectReviewCandidates([...objectiveCandidates, ...vocabularyCandidates] satisfies readonly ReviewCandidate[], now)
      .flatMap((candidate, order) => {
        if (candidate.source === "vocabulary_sense") {
          const label = labelForSense(getVocabularySense(candidate.id));
          return label ? [{ label, source: "vocabulary" as const, priority: candidate.priority, order }] : [];
        }
        const separator = candidate.id.indexOf("::");
        const lesson = separator < 0 ? undefined : getLessonById(language, course, candidate.id.slice(0, separator));
        const label = lesson ? `${lesson.title}: supplied objective activity` : undefined;
        return label && label.length <= 160 ? [{ label, source: "objective_activity" as const, priority: candidate.priority, order }] : [];
      });
    const grammarReviewItems = language === "en"
      ? selectGrammarReviewQueue(
        grammarProgress,
        getGrammarTargets("en")
          .filter((target) => target.band === course)
          .map((target, introductionOrder) => ({ targetId: target.id, introductionOrder })),
        now,
      ).flatMap((targetId, order) => {
        const label = labelForGrammar(getGrammarTargets("en").find((target) => target.id === targetId));
        const targetProgress = grammarProgress.targets[targetId];
        const priority = targetProgress?.lastIncorrectAt && Date.parse(targetProgress.lastIncorrectAt) >= Date.parse(now) - 7 * 24 * 60 * 60_000
          ? "recent_incorrect" as const
          : "due" as const;
        return label ? [{ label, source: "grammar" as const, priority, order: selectedReviewItems.length + order }] : [];
      })
      : [];
    const reviewItems = [...selectedReviewItems, ...grammarReviewItems];

    return { language, course, recentLessons, vocabulary, grammar, outcomePatterns, reviewItems };
  }, [course, courseProgress.lessons, grammarProgress.targets, language, reviewProgress, vocabularyProgress.senses]);

  const context = useMemo(
    () => projectTutorContext(preferences, contextSources),
    [contextSources, preferences],
  );
  const prompt = useMemo(() => serializeTutorContext(context), [context]);
  const compatible = isCourseCompatible(preferences.currentBand, course) && Boolean(context.course);

  function updatePreferences(update: Partial<Pick<TutorPreferences, "currentBand" | "targetBand" | "goals">>) {
    const currentBandChanged = Object.hasOwn(update, "currentBand");
    const next = {
      ...preferences,
      ...update,
      ...(currentBandChanged && (!update.currentBand || (preferences.targetBand && compareBands(preferences.targetBand, update.currentBand) <= 0))
        ? { targetBand: undefined }
        : {}),
    };
    if (saveTutorPreferences(next)) setPreferences(next);
  }

  function toggleGoal(goal: TutorGoal, checked: boolean) {
    const goals = checked ? [...preferences.goals, goal] : preferences.goals.filter((item) => item !== goal);
    updatePreferences({ goals });
  }

  async function copyPrompt() {
    if (!compatible) return;
    try {
      if (!navigator.clipboard) throw new Error("Clipboard access is unavailable");
      await navigator.clipboard.writeText(prompt);
      setCopyStatus("copied");
    } catch {
      setCopyStatus("failed");
    }
  }

  function clearPreferences() {
    const cleared: TutorPreferences = {
      ...emptyTutorPreferences({ learnerId: preferences.learnerId, language }),
      ...(preferences.dailyAllocationMinutes ? { dailyAllocationMinutes: preferences.dailyAllocationMinutes } : {}),
    };
    if (!saveTutorPreferences(cleared)) return;
    setPreferences(cleared);
    setCopyStatus("idle");
  }

  const targetOptions = preferences.currentBand
    ? BAND_ORDER.filter((band) => compareBands(band, preferences.currentBand!) > 0)
    : [];

  return (
    <div className="content-stack tutor-context-workspace" lang={language}>
      <section className="catalog-hero">
        <div>
          <p className="eyebrow">Local prompt export</p>
          <h1>Tutor Context</h1>
          <p className="lede">Prepare bounded local context for an external AI tool without sending data from this app.</p>
        </div>
      </section>

      <section className="tutor-context-boundary" aria-labelledby="tutor-boundary-heading">
        <h2 id="tutor-boundary-heading">What this page does—and does not do</h2>
        <p>Your selected band is self-reported, not a placement or proficiency result. Local activity records do not establish what you know or diagnose a weakness.</p>
        <p>This app makes no provider request and stores no copied prompt or external response. Information remains in this browser until you explicitly copy it; an external tool’s terms apply after you paste it there.</p>
      </section>

      {!ready ? <p className="empty-state">Loading local Tutor Context preferences…</p> : (
        <>
          <section className="tutor-context-config" aria-labelledby="tutor-config-heading">
            <p className="eyebrow">Learner choices</p>
            <h2 id="tutor-config-heading">Set your practice boundary</h2>
            <div className="tutor-context-fields">
              <label>
                Self-reported current band
                <select
                  aria-label="Self-reported current band"
                  value={preferences.currentBand ?? ""}
                  onChange={(event) => updatePreferences({ currentBand: event.target.value ? event.target.value as Band : undefined })}
                >
                  <option value="">Choose a band</option>
                  {BAND_ORDER.map((band) => <option key={band} value={band}>{band}</option>)}
                </select>
              </label>
              <label>
                Aspirational target band
                <select
                  aria-label="Aspirational target band"
                  disabled={!preferences.currentBand}
                  value={preferences.targetBand ?? ""}
                  onChange={(event) => updatePreferences({ targetBand: event.target.value ? event.target.value as Band : undefined })}
                >
                  <option value="">No target selected</option>
                  {targetOptions.map((band) => <option key={band} value={band}>{band}</option>)}
                </select>
              </label>
              <div>
                <strong>Current course</strong>
                <p>{course} {compatible ? "is within your selected practice boundary." : "will remain outside the copied context until your selected band includes it."}</p>
              </div>
            </div>
            <fieldset>
              <legend>Current goals</legend>
              <ul className="tutor-goal-list">
                {TUTOR_GOALS.filter((goal) => language === "en" || goal !== "grammar").map((goal) => (
                  <li key={goal}>
                    <label>
                      <input
                        type="checkbox"
                        checked={preferences.goals.includes(goal)}
                        onChange={(event) => toggleGoal(goal, event.target.checked)}
                      />
                      {goal}
                    </label>
                  </li>
                ))}
              </ul>
            </fieldset>
            <button type="button" className="text-button" onClick={clearPreferences}>Clear local Tutor Context preferences</button>
          </section>

          <section className="tutor-context-preview" aria-labelledby="tutor-preview-heading">
            <p className="eyebrow">Preview</p>
            <h2 id="tutor-preview-heading">Exactly what will be copied</h2>
            {!compatible ? <p className="empty-state">Choose a self-reported band that includes this {course} course before copying a context. A target band cannot increase this course boundary.</p> : null}
            <pre>{prompt}</pre>
            <div className="tutor-context-actions">
              <button className="secondary-button" type="button" disabled={!compatible} onClick={copyPrompt}>Copy Tutor Context</button>
              <span className="tutor-context-status" aria-live="polite">
                {copyStatus === "copied" && "Copied. Paste it into your chosen external AI tool."}
                {copyStatus === "failed" && "Copying is unavailable in this browser."}
              </span>
            </div>
          </section>

          <div className="button-row">
            <Link className="secondary-button" href={levelHref(language, course)}>Return to course</Link>
            <Link className="secondary-button" href={courseReviewHref(language, course)}>Open review</Link>
            <Link className="secondary-button" href={courseMistakesHref(language, course)}>View activity outcomes</Link>
          </div>
        </>
      )}
    </div>
  );
}
