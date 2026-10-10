"use client";

import { useEffect, useRef, useState } from "react";
import type { VocabularySense } from "@/content/vocabulary-types";

export function VocabularyReviewCard({
  sense,
  isNew,
  onStart,
  onResult,
}: {
  readonly sense: VocabularySense;
  readonly isNew: boolean;
  readonly onStart: () => void;
  readonly onResult: (correct: boolean) => void;
}) {
  const [answerVisible, setAnswerVisible] = useState(false);
  const [answer, setAnswer] = useState("");
  const [result, setResult] = useState<"correct" | "incorrect" | undefined>();
  const [started, setStarted] = useState(false);
  const inputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    setAnswerVisible(false);
    setAnswer("");
    setResult(undefined);
    setStarted(false);
  }, [sense.id]);

  function revealAnswer() {
    setAnswerVisible(true);
    requestAnimationFrame(() => inputRef.current?.focus());
  }

  function checkAnswer() {
    const normalized = answer.trim().toLocaleLowerCase("en");
    const correct = sense.acceptedAnswers.some((item) => item.toLocaleLowerCase("en") === normalized);
    setResult(correct ? "correct" : "incorrect");
    onResult(correct);
  }

  return (
    <article className="vocabulary-card" aria-labelledby={`word-${sense.id}`}>
      <p className="eyebrow">{isNew ? "New word" : "Review word"} · {sense.band} · {sense.partOfSpeech}</p>
      <h2 id={`word-${sense.id}`}>{sense.lemma}{sense.ipa ? <span className="ipa"> {sense.ipa}</span> : null}</h2>
      <p className="vocabulary-meaning">{sense.vietnameseMeaning ?? sense.definition}</p>
      <p>{sense.definition}</p>
      <dl className="vocabulary-details">
        <div><dt>Example</dt><dd>{sense.examples[0]}</dd></div>
        <div><dt>Useful phrase</dt><dd>{sense.collocations[0]}</dd></div>
      </dl>
      {isNew && !started ? (
        <button className="primary-button" type="button" onClick={() => { setStarted(true); onStart(); }}>Start learning this word</button>
      ) : !answerVisible ? (
        <button className="primary-button" type="button" onClick={revealAnswer}>Try recall</button>
      ) : (
        <div className="vocabulary-recall">
          <label htmlFor={`answer-${sense.id}`}>{sense.recallPrompt}</label>
          <input
            ref={inputRef}
            id={`answer-${sense.id}`}
            value={answer}
            onChange={(event) => setAnswer(event.target.value)}
            disabled={Boolean(result)}
            autoComplete="off"
          />
          <button className="primary-button" type="button" onClick={checkAnswer} disabled={!answer.trim() || Boolean(result)}>
            Check answer
          </button>
        </div>
      )}
      {result ? (
        <p className={result === "correct" ? "feedback-correct" : "feedback-incorrect"} aria-live="polite">
          {result === "correct" ? `Correct — ${sense.lemma}.` : `Not yet — the answer is “${sense.acceptedAnswers[0]}”.`}
        </p>
      ) : null}
    </article>
  );
}
