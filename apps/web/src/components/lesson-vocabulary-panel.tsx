"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { getVocabularyForLesson, vocabularySnapshot } from "@/content/vocabulary-catalog";
import type { LanguageCode } from "@/content/types";
import { vocabularyHref } from "@/lib/routes";
import { loadLearner, setActiveLanguage } from "@/lib/progress";
import {
  emptyVocabularyProgress,
  loadVocabularyProgress,
  saveVocabularyProgress,
  startWordSense,
  type VocabularyProgress,
} from "@/lib/vocabulary-progress";

export function LessonVocabularyPanel({
  language,
  lessonId,
}: {
  readonly language: LanguageCode;
  readonly lessonId: string;
}) {
  const senses = getVocabularyForLesson(language, lessonId);
  const [progress, setProgress] = useState<VocabularyProgress>(() =>
    emptyVocabularyProgress({ learnerId: "local-unavailable", language }, vocabularySnapshot.inventoryVersion),
  );
  const [ready, setReady] = useState(false);

  useEffect(() => {
    if (!senses.length) return;
    const learner = setActiveLanguage(loadLearner(), language);
    setProgress(loadVocabularyProgress({ learnerId: learner.learnerId, language }, vocabularySnapshot.inventoryVersion));
    setReady(true);
  }, [language, lessonId, senses.length]);

  if (!senses.length) return null;

  function startSense(senseId: string) {
    const next = startWordSense(progress, senseId, new Date().toISOString());
    setProgress(next);
    saveVocabularyProgress(next);
  }

  return (
    <section className="page-section lesson-vocabulary-panel" aria-labelledby="lesson-vocabulary-heading">
      <div className="section-heading">
        <div><p className="eyebrow">Word senses from this lesson</p><h2 id="lesson-vocabulary-heading">Vocabulary</h2></div>
        <Link href={vocabularyHref(language)}>Open vocabulary learning</Link>
      </div>
      <ul className="lesson-vocabulary-list">
        {senses.map((sense) => {
          const state = progress.senses[sense.id]?.state;
          return <li key={sense.id}>
            <div><strong>{sense.lemma}</strong>{sense.ipa ? <span className="ipa"> {sense.ipa}</span> : null}<span>{sense.vietnameseMeaning ?? sense.definition}</span></div>
            {state ? <em>{state}</em> : <button type="button" className="secondary-button" disabled={!ready} onClick={() => startSense(sense.id)}>Start learning</button>}
          </li>;
        })}
      </ul>
    </section>
  );
}
