"use client";

import { useEffect, useState } from "react";
import type { DisplayLesson } from "@/content/types";
import { getLanguageConfiguration } from "@/content/languages";
import { getVocabularySenseIdsForExercise, vocabularySnapshot } from "@/content/vocabulary-catalog";
import { getGrammarTargetIdsForExercise, grammarSnapshot } from "@/content/grammar-catalog";
import { LessonVocabularyPanel } from "./lesson-vocabulary-panel";
import {
  emptyVocabularyProgress,
  loadVocabularyProgress,
  recordWordSenseResult,
  saveVocabularyProgress,
  type VocabularyProgress,
} from "@/lib/vocabulary-progress";
import {
  emptyGrammarProgress,
  loadGrammarProgress,
  recordGrammarTargetResult,
  saveGrammarProgress,
  type GrammarProgress,
} from "@/lib/grammar-progress";
import {
  emptyReviewProgress,
  isObjectiveExerciseType,
  loadReviewProgress,
  recordObjectiveReviewOutcome,
  saveReviewProgress,
  type ReviewProgress,
} from "@/lib/review-progress";
import { ExerciseList } from "./exercise-list";
import { PracticePanels, type Modality } from "./practice-panels";
import {
  emptyProgress,
  loadLearner,
  loadProgress,
  resetExerciseRunner,
  saveProgress,
  setActiveLanguage,
  updateLessonProgress,
  type CourseProgress,
  type ExerciseRunnerState,
} from "@/lib/progress";

export function LessonInteractions({ lesson }: { readonly lesson: DisplayLesson }) {
  const [progress, setProgress] = useState<CourseProgress>(() =>
    emptyProgress({
      learnerId: "local-unavailable",
      language: lesson.language,
      course: lesson.band,
    }),
  );
  const [ready, setReady] = useState(false);
  const [reviewProgress, setReviewProgress] = useState<ReviewProgress>(() =>
    emptyReviewProgress({ learnerId: "local-unavailable", language: lesson.language, course: lesson.band }),
  );
  const [vocabularyProgress, setVocabularyProgress] = useState<VocabularyProgress>(() =>
    emptyVocabularyProgress({ learnerId: "local-unavailable", language: lesson.language }, vocabularySnapshot.inventoryVersion),
  );
  const [grammarProgress, setGrammarProgress] = useState<GrammarProgress>(() =>
    emptyGrammarProgress({ learnerId: "local-unavailable", language: "en" }, grammarSnapshot.inventoryVersion),
  );

  useEffect(() => {
    setReady(false);
    const learner = loadLearner();
    setActiveLanguage(learner, lesson.language);
    const loaded = loadProgress({
      learnerId: learner.learnerId,
      language: lesson.language,
      course: lesson.band,
    });
    const accessed = updateLessonProgress(loaded, lesson.lessonId, {
      lastAccessedAt: new Date().toISOString(),
    });
    setProgress(accessed);
    saveProgress(accessed);
    setVocabularyProgress(loadVocabularyProgress(
      { learnerId: learner.learnerId, language: lesson.language },
      vocabularySnapshot.inventoryVersion,
    ));
    if (lesson.language === "en") {
      setGrammarProgress(loadGrammarProgress(
        { learnerId: learner.learnerId, language: "en" },
        grammarSnapshot.inventoryVersion,
      ));
    }
    setReviewProgress(loadReviewProgress({
      learnerId: learner.learnerId,
      language: lesson.language,
      course: lesson.band,
    }));
    setReady(true);
  }, [lesson.band, lesson.language, lesson.lessonId]);

  const exercises = lesson.exercises ?? [];
  const practice = lesson.practice ?? {};
  const hasPractice = Object.keys(practice).length > 0;
  const languageName = getLanguageConfiguration(lesson.language)?.name ?? lesson.language;
  const lessonProgress = progress.lessons[lesson.lessonId] ?? {
    completed: false,
    attempts: {},
    protocols: {},
    drafts: {},
  };

  function commit(next: CourseProgress) {
    setProgress(next);
    saveProgress(next);
  }

  function commitVocabulary(next: VocabularyProgress) {
    setVocabularyProgress(next);
    saveVocabularyProgress(next);
  }

  function commitGrammar(next: GrammarProgress) {
    setGrammarProgress(next);
    saveGrammarProgress(next);
  }

  function commitReview(next: ReviewProgress) {
    setReviewProgress(next);
    saveReviewProgress(next);
  }

  function timestamp(): string {
    return new Date().toISOString();
  }

  function currentRunner(): ExerciseRunnerState {
    return lessonProgress.exerciseRunner ?? {
      currentExerciseId: exercises[0]?.id,
      finished: false,
      exercises: {},
    };
  }

  function updateRunner(runner: ExerciseRunnerState) {
    commit(
      updateLessonProgress(progress, lesson.lessonId, {
        exerciseRunner: runner,
        lastAccessedAt: timestamp(),
      }),
    );
  }

  function recordCheck(exerciseId: string, result: "correct" | "incorrect") {
    const runner = currentRunner();
    const attempts = {
      ...lessonProgress.attempts,
      [exerciseId]: (lessonProgress.attempts[exerciseId] ?? 0) + 1,
    };
    const checkedAt = timestamp();
    commit(
      updateLessonProgress(progress, lesson.lessonId, {
        attempts,
        lastAccessedAt: checkedAt,
        exerciseRunner: {
          ...runner,
          currentExerciseId: exerciseId,
          finished: false,
          exercises: {
            ...runner.exercises,
            [exerciseId]: { lastResult: result, completed: result === "correct" },
          },
        },
      }),
    );
    const exercise = exercises.find((item) => item.id === exerciseId);
    if (exercise && isObjectiveExerciseType(exercise.type)) {
      commitReview(recordObjectiveReviewOutcome(reviewProgress, {
        lessonId: lesson.lessonId,
        exerciseId,
        result,
        reviewedAt: checkedAt,
      }));
      if (lesson.language === "en") {
        const grammarTargetIds = getGrammarTargetIdsForExercise("en", lesson.lessonId, exerciseId);
        if (grammarTargetIds.length) {
          let nextGrammar = grammarProgress;
          for (const targetId of grammarTargetIds) {
            nextGrammar = recordGrammarTargetResult(nextGrammar, targetId, result === "correct", checkedAt);
          }
          commitGrammar(nextGrammar);
        }
      }
    }
    const senseIds = getVocabularySenseIdsForExercise(lesson.language, lesson.lessonId, exerciseId);
    if (senseIds.length) {
      let nextVocabulary = vocabularyProgress;
      for (const senseId of senseIds) {
        nextVocabulary = recordWordSenseResult(nextVocabulary, senseId, result === "correct", checkedAt);
      }
      commitVocabulary(nextVocabulary);
    }
  }

  function advance(nextExerciseId: string | undefined) {
    const runner = currentRunner();
    updateRunner({ ...runner, currentExerciseId: nextExerciseId, finished: !nextExerciseId });
  }

  function recordSelfPractice(exerciseId: string, nextExerciseId: string | undefined) {
    const runner = currentRunner();
    updateRunner({
      ...runner,
      currentExerciseId: nextExerciseId,
      finished: !nextExerciseId,
      exercises: {
        ...runner.exercises,
        [exerciseId]: { lastResult: "self_practice", completed: true },
      },
    });
  }

  function restartExercises() {
    const cleared = resetExerciseRunner(progress, lesson.lessonId);
    commit(updateLessonProgress(cleared, lesson.lessonId, { lastAccessedAt: timestamp() }));
  }

  function setProtocol(modality: Modality, completed: boolean) {
    commit(
      updateLessonProgress(progress, lesson.lessonId, {
        protocols: { ...lessonProgress.protocols, [modality]: completed },
        lastAccessedAt: timestamp(),
      }),
    );
  }

  return (
    <>
      <LessonVocabularyPanel language={lesson.language} lessonId={lesson.lessonId} />
      <section className="page-section" aria-labelledby="exercise-heading">
        <div className="section-heading">
          <div>
            <p className="eyebrow">Local practice</p>
            <h2 id="exercise-heading">Exercises</h2>
          </div>
          <p>Answers remain hidden until checked. Browser concealment is not an answer-security boundary.</p>
        </div>
        <div lang={lesson.language}>
          <ExerciseList
            exercises={exercises}
            runner={lessonProgress.exerciseRunner}
            onCheck={recordCheck}
            onAdvance={advance}
            onSelfPractice={recordSelfPractice}
            onRestart={restartExercises}
          />
        </div>
      </section>

      <section className="page-section" aria-labelledby="practice-heading">
        <div className="section-heading">
          <div>
            <p className="eyebrow">Stored prompt tools</p>
            <h2 id="practice-heading">AI practice</h2>
          </div>
          <p>Copy a lesson-specific stored prompt into your preferred AI or voice-AI tool.</p>
        </div>
        {hasPractice ? (
          <div lang={lesson.language}>
            <PracticePanels
              practice={practice}
              language={lesson.language}
              targetLevel={lesson.band}
              completed={lessonProgress.protocols}
              onProtocolComplete={setProtocol}
            />
          </div>
        ) : (
          <p className="empty-state">No AI practice protocol is available for this lesson yet.</p>
        )}
      </section>

      <section className="completion-card">
        <div>
          <h2>Lesson completion</h2>
          <p>Saved only in this browser for {languageName}. It is not certification or curriculum authority.</p>
        </div>
        <button
          type="button"
          className={lessonProgress.completed ? "secondary-button" : "primary-button"}
          aria-pressed={lessonProgress.completed}
          disabled={!ready}
          onClick={() =>
            commit(
              updateLessonProgress(progress, lesson.lessonId, {
                completed: !lessonProgress.completed,
                lastAccessedAt: timestamp(),
              }),
            )
          }
        >
          {lessonProgress.completed ? "Mark as not complete" : "Mark lesson complete"}
        </button>
        <strong aria-live="polite">{lessonProgress.completed ? "Locally complete" : "Not complete"}</strong>
      </section>
    </>
  );
}
