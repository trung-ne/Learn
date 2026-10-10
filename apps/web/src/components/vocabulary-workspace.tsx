"use client";

import { useEffect, useMemo, useState } from "react";
import { getVocabularySense, getVocabularySenses, vocabularySnapshot } from "@/content/vocabulary-catalog";
import type { LanguageCode } from "@/content/types";
import { loadLearner, setActiveLanguage } from "@/lib/progress";
import {
  emptyVocabularyProgress,
  loadVocabularyProgress,
  recordWordSenseResult,
  saveVocabularyProgress,
  selectVocabularyReviewQueue,
  startWordSense,
  type VocabularyProgress,
} from "@/lib/vocabulary-progress";
import { VocabularyReviewCard } from "./vocabulary-review-card";

const SESSION_SIZE = 10;

export function VocabularyWorkspace({ language }: { readonly language: LanguageCode }) {
  const senses = useMemo(() => getVocabularySenses(language), [language]);
  const [progress, setProgress] = useState<VocabularyProgress>(() =>
    emptyVocabularyProgress({ learnerId: "local-unavailable", language }, vocabularySnapshot.inventoryVersion),
  );
  const [ready, setReady] = useState(false);
  const [sessionIds, setSessionIds] = useState<readonly string[]>([]);
  const [currentIndex, setCurrentIndex] = useState(0);
  const [libraryFilter, setLibraryFilter] = useState<"all" | "weak" | "mastered">("all");

  useEffect(() => {
    setReady(false);
    const learner = setActiveLanguage(loadLearner(), language);
    setProgress(loadVocabularyProgress(
      { learnerId: learner.learnerId, language },
      vocabularySnapshot.inventoryVersion,
    ));
    setSessionIds([]);
    setCurrentIndex(0);
    setReady(true);
  }, [language]);

  const candidates = useMemo(() => senses.map((sense, introductionOrder) => ({ senseId: sense.id, introductionOrder })), [senses]);
  const dueIds = useMemo(
    () => selectVocabularyReviewQueue(progress, candidates, new Date().toISOString()),
    [candidates, progress],
  );
  const currentSense = getVocabularySense(sessionIds[currentIndex] ?? "");
  const knownIds = new Set(Object.keys(progress.senses));
  const nextNewIds = senses.filter((sense) => !knownIds.has(sense.id)).slice(0, SESSION_SIZE).map((sense) => sense.id);
  const activeSenses = senses.filter((sense) => knownIds.has(sense.id));
  const masteredCount = activeSenses.filter((sense) => progress.senses[sense.id]?.state === "mastered").length;
  const weakCount = activeSenses.filter((sense) => (progress.senses[sense.id]?.mistakes ?? 0) > 0).length;
  const librarySenses = senses.filter((sense) => {
    const item = progress.senses[sense.id];
    return libraryFilter === "all" ||
      (libraryFilter === "weak" && (item?.mistakes ?? 0) > 0) ||
      (libraryFilter === "mastered" && item?.state === "mastered");
  });

  function commit(next: VocabularyProgress) {
    setProgress(next);
    saveVocabularyProgress(next);
  }

  function startSession(ids: readonly string[]) {
    if (!ready || !ids.length) return;
    const now = new Date().toISOString();
    let next = progress;
    for (const senseId of ids) next = startWordSense(next, senseId, now);
    commit(next);
    setSessionIds(ids);
    setCurrentIndex(0);
  }

  function recordResult(correct: boolean) {
    if (!currentSense) return;
    commit(recordWordSenseResult(progress, currentSense.id, correct, new Date().toISOString()));
  }

  function nextWord() {
    if (currentIndex + 1 < sessionIds.length) setCurrentIndex((index) => index + 1);
    else {
      setSessionIds([]);
      setCurrentIndex(0);
    }
  }

  if (!senses.length) {
    return <p className="empty-state">No learner-facing vocabulary inventory is available for this language yet.</p>;
  }

  return (
    <div className="content-stack vocabulary-workspace" lang={language}>
      <section className="catalog-hero vocabulary-hero">
        <div>
          <p className="eyebrow">Local WordSense learning</p>
          <h1>Vocabulary</h1>
          <p className="lede">Learn each meaning separately, practise recall, and return when a local review is due.</p>
        </div>
        <dl className="vocabulary-summary" aria-label="Vocabulary progress summary">
          <div><dt>Due today</dt><dd>{dueIds.length}</dd></div>
          <div><dt>Learning</dt><dd>{activeSenses.length - masteredCount}</dd></div>
          <div><dt>Weak words</dt><dd>{weakCount}</dd></div>
          <div><dt>Mastered</dt><dd>{masteredCount}</dd></div>
        </dl>
      </section>

      {!sessionIds.length || !currentSense ? (
        <section className="page-section vocabulary-actions" aria-labelledby="vocabulary-actions-heading">
          <div className="section-heading">
            <div><p className="eyebrow">Choose a session</p><h2 id="vocabulary-actions-heading">Learn and review</h2></div>
            <p>Progress is stored only in this browser. It is a self-study aid, not a proficiency or placement result.</p>
          </div>
          <div className="button-row">
            <button type="button" className="primary-button" disabled={!ready || !dueIds.length} onClick={() => startSession(dueIds)}>
              Review due words ({dueIds.length})
            </button>
            <button type="button" className="secondary-button" disabled={!ready || !nextNewIds.length} onClick={() => startSession(nextNewIds)}>
              Start next words ({nextNewIds.length})
            </button>
          </div>
          <section className="vocabulary-library" aria-labelledby="library-heading">
            <div className="section-heading">
              <h2 id="library-heading">Word library</h2>
              <div className="library-filters" aria-label="Vocabulary library filter">
                {(["all", "weak", "mastered"] as const).map((filter) => (
                  <button key={filter} type="button" className="text-button" aria-pressed={libraryFilter === filter} onClick={() => setLibraryFilter(filter)}>
                    {filter === "all" ? "All words" : filter === "weak" ? "Weak words" : "Mastered"}
                  </button>
                ))}
              </div>
            </div>
            {librarySenses.length ? <ul>
              {librarySenses.map((sense) => {
                const state = progress.senses[sense.id]?.state ?? "new";
                return <li key={sense.id}><strong>{sense.lemma}</strong><span>{sense.vietnameseMeaning ?? sense.definition}</span><em>{state}</em></li>;
              })}
            </ul> : <p className="empty-state">No words match this local view yet.</p>}
          </section>
        </section>
      ) : (
        <section className="page-section" aria-label="Vocabulary review session">
          <p className="eyebrow">Word {currentIndex + 1} of {sessionIds.length}</p>
          <VocabularyReviewCard
            sense={currentSense}
            isNew={progress.senses[currentSense.id]?.attempts === 0}
            onStart={() => commit(startWordSense(progress, currentSense.id, new Date().toISOString()))}
            onResult={recordResult}
          />
          <button className="secondary-button" type="button" onClick={nextWord}>Next word</button>
        </section>
      )}
    </div>
  );
}
