"use client";

import { useEffect, useState } from "react";
import type { DisplayLesson } from "@/content/types";
import { getLanguageConfiguration } from "@/content/languages";
import { ExerciseList } from "./exercise-list";
import { PracticePanels, type Modality } from "./practice-panels";
import {
  emptyProgress,
  loadProgress,
  saveProgress,
  updateLessonProgress,
  type LanguageProgress,
} from "@/lib/progress";

export function LessonInteractions({ lesson }: { readonly lesson: DisplayLesson }) {
  const [progress, setProgress] = useState<LanguageProgress>(() => emptyProgress(lesson.language));
  const [ready, setReady] = useState(false);

  useEffect(() => {
    setProgress(loadProgress(lesson.language));
    setReady(true);
  }, [lesson.language]);

  const languageName = getLanguageConfiguration(lesson.language)?.name ?? lesson.language;
  const lessonProgress = progress.lessons[lesson.lessonId] ?? {
    completed: false,
    attempts: {},
    protocols: {},
    drafts: {},
  };

  function commit(next: LanguageProgress) {
    setProgress(next);
    saveProgress(next);
  }

  function recordAttempt(exerciseId: string) {
    const attempts = {
      ...lessonProgress.attempts,
      [exerciseId]: (lessonProgress.attempts[exerciseId] ?? 0) + 1,
    };
    commit(updateLessonProgress(progress, lesson.lessonId, { attempts }));
  }

  function setProtocol(modality: Modality, completed: boolean) {
    commit(updateLessonProgress(progress, lesson.lessonId, {
      protocols: { ...lessonProgress.protocols, [modality]: completed },
    }));
  }

  function setDraft(draft: string) {
    commit(updateLessonProgress(progress, lesson.lessonId, {
      drafts: { ...lessonProgress.drafts, writing: draft },
    }));
  }

  return (
    <>
      <section className="page-section" aria-labelledby="exercise-heading">
        <div className="section-heading">
          <div><p className="eyebrow">Local practice</p><h2 id="exercise-heading">Exercises</h2></div>
          <p>Answers remain hidden until checked. Browser concealment is not an answer-security boundary.</p>
        </div>
        <ExerciseList exercises={lesson.exercises} onAttempt={recordAttempt} />
      </section>

      <section className="page-section" aria-labelledby="practice-heading">
        <div className="section-heading">
          <div><p className="eyebrow">Four bounded modes</p><h2 id="practice-heading">Practice protocols</h2></div>
          <p>These are static, local instructions—not live AI, media processing, or assessment.</p>
        </div>
        <PracticePanels
          practice={lesson.practice}
          completed={lessonProgress.protocols}
          writingDraft={lessonProgress.drafts.writing ?? ""}
          onProtocolComplete={setProtocol}
          onDraftChange={setDraft}
        />
      </section>

      <section className="completion-card" aria-live="polite">
        <div>
          <h2>Lesson completion</h2>
          <p>Saved only in this browser for {languageName}. It is not certification or curriculum authority.</p>
        </div>
        <button
          type="button"
          className={lessonProgress.completed ? "secondary-button" : "primary-button"}
          disabled={!ready}
          onClick={() => commit(updateLessonProgress(progress, lesson.lessonId, { completed: !lessonProgress.completed }))}
        >
          {lessonProgress.completed ? "Mark as not complete" : "Mark lesson complete"}
        </button>
        <strong>{lessonProgress.completed ? "Locally complete" : "Not complete"}</strong>
      </section>
    </>
  );
}
