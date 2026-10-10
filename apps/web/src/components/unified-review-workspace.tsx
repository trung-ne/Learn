"use client";

import { useEffect, useMemo, useState } from "react";
import { ExerciseList } from "@/components/exercise-list";
import { VocabularyReviewCard } from "@/components/vocabulary-review-card";
import { getLessonById } from "@/content/catalog";
import { getGrammarTargetIdsForExercise, grammarSnapshot } from "@/content/grammar-catalog";
import { getVocabularySense, getVocabularySenses, vocabularySnapshot } from "@/content/vocabulary-catalog";
import type { CourseLevel, DisplayExercise, LanguageCode } from "@/content/types";
import {
  emptyGrammarProgress,
  loadGrammarProgress,
  recordGrammarTargetResult,
  saveGrammarProgress,
  type GrammarProgress,
} from "@/lib/grammar-progress";
import { loadLearner, setActiveLanguage } from "@/lib/progress";
import {
  emptyReviewProgress,
  isObjectiveExerciseType,
  isRecentIncorrect,
  isReviewItemDue,
  loadReviewProgress,
  recordObjectiveReviewOutcome,
  resetReviewProgress,
  reviewItemId,
  saveReviewProgress,
  selectReviewCandidates,
  type ReviewCandidate,
  type ReviewProgress,
} from "@/lib/review-progress";
import {
  emptyVocabularyProgress,
  hasRecentVocabularyMistake,
  isDue,
  loadVocabularyProgress,
  recordWordSenseResult,
  saveVocabularyProgress,
  type VocabularyProgress,
} from "@/lib/vocabulary-progress";

export function UnifiedReviewWorkspace({
  language,
  course,
}: {
  readonly language: LanguageCode;
  readonly course: CourseLevel;
}) {
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
  const [session, setSession] = useState<readonly ReviewCandidate[]>([]);
  const [currentIndex, setCurrentIndex] = useState(0);

  useEffect(() => {
    setReady(false);
    const learner = setActiveLanguage(loadLearner(), language);
    setReviewProgress(loadReviewProgress({ learnerId: learner.learnerId, language, course }));
    setVocabularyProgress(loadVocabularyProgress(
      { learnerId: learner.learnerId, language },
      vocabularySnapshot.inventoryVersion,
    ));
    if (language === "en") {
      setGrammarProgress(loadGrammarProgress(
        { learnerId: learner.learnerId, language: "en" },
        grammarSnapshot.inventoryVersion,
      ));
    }
    setSession([]);
    setCurrentIndex(0);
    setReady(true);
  }, [course, language]);

  const now = new Date().toISOString();
  const candidates = useMemo(() => {
    const objectiveCandidates = Object.values(reviewProgress.items).flatMap((item, order) => {
      const lesson = getLessonById(language, course, item.lessonId);
      const exercise = lesson?.exercises?.find((candidate) => candidate.id === item.exerciseId);
      if (!lesson || !exercise || !isObjectiveExerciseType(exercise.type)) return [];
      return [{
        source: "objective_exercise" as const,
        id: reviewItemId(item.lessonId, item.exerciseId),
        dueAt: item.nextReviewAt,
        priority: isRecentIncorrect(item, now) ? "recent_incorrect" as const : "due" as const,
        order,
      }];
    }).filter((candidate) => candidate.dueAt <= now);

    const vocabularyCandidates = getVocabularySenses(language)
      .filter((sense) => sense.band === course)
      .flatMap((sense, order) => {
        const item = vocabularyProgress.senses[sense.id];
        if (!item) return [];
        const recentMistake = hasRecentVocabularyMistake(item, now);
        if (!isDue(item, now)) return [];
        return [{
          source: "vocabulary_sense" as const,
          id: sense.id,
          dueAt: item.nextReviewAt,
          priority: recentMistake ? "recent_incorrect" as const : "due" as const,
          order,
        }];
      });

    return selectReviewCandidates([...objectiveCandidates, ...vocabularyCandidates], now);
  }, [course, language, now, reviewProgress.items, vocabularyProgress.senses]);

  const current = session[currentIndex];
  const currentExercise = current?.source === "objective_exercise" ? exerciseFor(current.id) : undefined;
  const currentSense = current?.source === "vocabulary_sense" ? getVocabularySense(current.id) : undefined;

  function commitReview(next: ReviewProgress) {
    setReviewProgress(next);
    saveReviewProgress(next);
  }

  function commitVocabulary(next: VocabularyProgress) {
    setVocabularyProgress(next);
    saveVocabularyProgress(next);
  }

  function commitGrammar(next: GrammarProgress) {
    setGrammarProgress(next);
    saveGrammarProgress(next);
  }

  function startSession() {
    if (!ready || !candidates.length) return;
    setSession(candidates);
    setCurrentIndex(0);
  }

  function nextItem() {
    if (currentIndex + 1 < session.length) setCurrentIndex((index) => index + 1);
    else {
      setSession([]);
      setCurrentIndex(0);
    }
  }

  function recordExerciseResult(result: "correct" | "incorrect") {
    if (!currentExercise) return;
    const checkedAt = new Date().toISOString();
    commitReview(recordObjectiveReviewOutcome(reviewProgress, {
      lessonId: currentExercise.lessonId,
      exerciseId: currentExercise.exercise.id,
      result,
      reviewedAt: checkedAt,
    }));
    if (language === "en") {
      const grammarTargetIds = getGrammarTargetIdsForExercise("en", currentExercise.lessonId, currentExercise.exercise.id);
      if (grammarTargetIds.length) {
        let nextGrammar = grammarProgress;
        for (const targetId of grammarTargetIds) {
          nextGrammar = recordGrammarTargetResult(nextGrammar, targetId, result === "correct", checkedAt);
        }
        commitGrammar(nextGrammar);
      }
    }
  }

  function recordVocabularyResult(correct: boolean) {
    if (!currentSense) return;
    commitVocabulary(recordWordSenseResult(
      vocabularyProgress,
      currentSense.id,
      correct,
      new Date().toISOString(),
    ));
  }

  function clearObjectiveReview() {
    const scope = { learnerId: reviewProgress.learnerId, language, course };
    resetReviewProgress(scope);
    setReviewProgress(emptyReviewProgress(scope));
    setSession([]);
    setCurrentIndex(0);
  }

  const objectiveCount = candidates.filter((candidate) => candidate.source === "objective_exercise").length;
  const vocabularyCount = candidates.filter((candidate) => candidate.source === "vocabulary_sense").length;

  return (
    <div className="content-stack unified-review-workspace" lang={language}>
      <section className="catalog-hero review-hero">
        <div>
          <p className="eyebrow">Local review schedule</p>
          <h1>Review</h1>
          <p className="lede">Revisit supplied activities using outcomes and schedules saved in this browser.</p>
        </div>
        <dl className="vocabulary-summary" aria-label="Review summary">
          <div><dt>Ready now</dt><dd>{candidates.length}</dd></div>
          <div><dt>Activities</dt><dd>{objectiveCount}</dd></div>
          <div><dt>Word senses</dt><dd>{vocabularyCount}</dd></div>
        </dl>
      </section>

      {!session.length || (!currentExercise && !currentSense) ? (
        <section className="page-section review-actions" aria-labelledby="review-actions-heading">
          <div className="section-heading">
            <div><p className="eyebrow">Choose a session</p><h2 id="review-actions-heading">Scheduled review</h2></div>
            <p>This local record is not a learning diagnosis, proficiency result, or placement decision.</p>
          </div>
          {candidates.length ? (
            <button type="button" className="primary-button" disabled={!ready} onClick={startSession}>
              Start review ({candidates.length})
            </button>
          ) : (
            <p className="empty-state">No locally scheduled review is ready for this course. Complete an objectively scored activity or return when a review is due.</p>
          )}
          {Object.keys(reviewProgress.items).length ? (
            <button type="button" className="text-button" onClick={clearObjectiveReview}>
              Reset local activity review history
            </button>
          ) : null}
        </section>
      ) : (
        <section className="page-section" aria-label="Review session">
          <p className="eyebrow">Review {currentIndex + 1} of {session.length} · {current.source === "objective_exercise" ? "Supplied activity" : "Word sense"}</p>
          {currentExercise ? (
            <ExerciseList
              exercises={[currentExercise.exercise]}
              onCheck={(_exerciseId, result) => recordExerciseResult(result)}
              onAdvance={nextItem}
              onSelfPractice={() => undefined}
              onRestart={() => undefined}
            />
          ) : currentSense ? (
            <>
              <VocabularyReviewCard
                sense={currentSense}
                isNew={vocabularyProgress.senses[currentSense.id]?.attempts === 0}
                onStart={() => undefined}
                onResult={recordVocabularyResult}
              />
              <button className="secondary-button" type="button" onClick={nextItem}>Next item</button>
            </>
          ) : null}
        </section>
      )}
    </div>
  );

  function exerciseFor(id: string): { readonly lessonId: string; readonly exercise: DisplayExercise } | undefined {
    const separator = id.indexOf("::");
    if (separator < 0) return undefined;
    const lessonId = id.slice(0, separator);
    const exerciseId = id.slice(separator + 2);
    const lesson = getLessonById(language, course, lessonId);
    const exercise = lesson?.exercises?.find((candidate) => candidate.id === exerciseId);
    return lesson && exercise && isObjectiveExerciseType(exercise.type) ? { lessonId, exercise } : undefined;
  }
}
