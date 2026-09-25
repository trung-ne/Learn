"use client";

import { useMemo, useState } from "react";
import type { DisplayExercise } from "@/content/types";
import { arraysMatch, matchesAnyAnswer } from "@/lib/answers";

const objectiveTypes = new Set([
  "multiple_choice",
  "fill_blank",
  "matching",
  "ordering",
  "reading",
  "listening",
  "selection",
  "completion",
]);

interface ExerciseListProps {
  readonly exercises: readonly DisplayExercise[];
  readonly onAttempt: (exerciseId: string) => void;
}

export function ExerciseList({ exercises, onAttempt }: ExerciseListProps) {
  return (
    <div className="exercise-list">
      {exercises.map((exercise, index) =>
        objectiveTypes.has(exercise.type) ? (
          <ObjectiveExercise key={exercise.id} exercise={exercise} number={index + 1} onAttempt={onAttempt} />
        ) : (
          <SelfPracticeExercise key={exercise.id} exercise={exercise} number={index + 1} />
        ),
      )}
    </div>
  );
}

function Feedback({ correct }: { readonly correct: boolean }) {
  return (
    <p className={correct ? "feedback correct" : "feedback incorrect"} role="status">
      <strong>{correct ? "Correct." : "Not yet."}</strong>{" "}
      {correct ? "Your answer matches the supplied answer key." : "Review the lesson and try again."}
    </p>
  );
}

function ObjectiveExercise({
  exercise,
  number,
  onAttempt,
}: {
  readonly exercise: DisplayExercise;
  readonly number: number;
  readonly onAttempt: (exerciseId: string) => void;
}) {
  const [answer, setAnswer] = useState("");
  const [checked, setChecked] = useState<boolean | null>(null);
  const [order, setOrder] = useState<readonly string[]>(exercise.items ?? []);
  const [matches, setMatches] = useState<Record<string, string>>({});
  const [questionAnswers, setQuestionAnswers] = useState<Record<number, string>>({});
  const rightOptions = useMemo(() => [...(exercise.pairs ?? [])].map((pair) => pair.right).reverse(), [exercise.pairs]);

  function evaluate(): boolean {
    if (exercise.type === "matching") {
      return (exercise.pairs ?? []).every((pair) => matches[pair.left] === pair.right);
    }
    if (exercise.type === "ordering") return arraysMatch(order, exercise.correct_order ?? []);
    if (exercise.type === "reading" || exercise.type === "listening") {
      return (exercise.questions ?? []).every((question, index) =>
        matchesAnyAnswer(questionAnswers[index] ?? "", question.acceptable_answers),
      );
    }
    const expected = exercise.correct_answer
      ? [exercise.correct_answer]
      : exercise.acceptable_answers ?? (exercise.answer ? [exercise.answer] : []);
    return matchesAnyAnswer(answer, expected);
  }

  function check() {
    setChecked(evaluate());
    onAttempt(exercise.id);
  }

  const canCheck =
    exercise.type === "matching"
      ? (exercise.pairs ?? []).every((pair) => matches[pair.left])
      : exercise.type === "ordering"
        ? order.length > 0
        : exercise.type === "reading" || exercise.type === "listening"
          ? (exercise.questions ?? []).every((_, index) => questionAnswers[index]?.trim())
          : answer.trim().length > 0;

  return (
    <article className="exercise-card">
      <p className="eyebrow">Activity {number} · {exercise.type.replaceAll("_", " ")}</p>
      <h3>{exercise.prompt}</h3>
      {exercise.stimulus && <blockquote>{exercise.stimulus}</blockquote>}

      {exercise.type === "multiple_choice" && exercise.options ? (
        <fieldset>
          <legend>Choose one answer</legend>
          {exercise.options.map((option) => (
            <label className="choice" key={option}>
              <input type="radio" name={exercise.id} value={option} checked={answer === option} onChange={(event) => { setAnswer(event.target.value); setChecked(null); }} />
              <span>{option}</span>
            </label>
          ))}
        </fieldset>
      ) : exercise.type === "matching" ? (
        <div className="matching-grid">
          {(exercise.pairs ?? []).map((pair) => (
            <label key={pair.left}>
              <span>{pair.left}</span>
              <select value={matches[pair.left] ?? ""} onChange={(event) => { setMatches({ ...matches, [pair.left]: event.target.value }); setChecked(null); }}>
                <option value="">Choose a match</option>
                {rightOptions.map((right) => <option key={right} value={right}>{right}</option>)}
              </select>
            </label>
          ))}
        </div>
      ) : exercise.type === "ordering" ? (
        <ol className="ordering-list">
          {order.map((item, index) => (
            <li key={`${item}-${index}`}>
              <span>{item}</span>
              <span className="order-actions">
                <button type="button" disabled={index === 0} aria-label={`Move ${item} up`} onClick={() => { const next = [...order]; [next[index - 1], next[index]] = [next[index]!, next[index - 1]!]; setOrder(next); setChecked(null); }}>↑</button>
                <button type="button" disabled={index === order.length - 1} aria-label={`Move ${item} down`} onClick={() => { const next = [...order]; [next[index], next[index + 1]] = [next[index + 1]!, next[index]!]; setOrder(next); setChecked(null); }}>↓</button>
              </span>
            </li>
          ))}
        </ol>
      ) : exercise.type === "reading" || exercise.type === "listening" ? (
        <div className="question-list">
          {(exercise.questions ?? []).map((question, index) => (
            <label key={question.question}>
              <span>{question.question}</span>
              <input value={questionAnswers[index] ?? ""} onChange={(event) => { setQuestionAnswers({ ...questionAnswers, [index]: event.target.value }); setChecked(null); }} />
            </label>
          ))}
        </div>
      ) : (
        <label>
          <span>Your answer</span>
          <input value={answer} onChange={(event) => { setAnswer(event.target.value); setChecked(null); }} autoComplete="off" />
        </label>
      )}

      <button className="primary-button" type="button" disabled={!canCheck} onClick={check}>Check answer</button>
      {checked !== null && <Feedback correct={checked} />}
    </article>
  );
}

function SelfPracticeExercise({ exercise, number }: { readonly exercise: DisplayExercise; readonly number: number }) {
  const criteria = typeof exercise.rubric === "string" ? [exercise.rubric] : exercise.rubric?.criteria ?? [];
  return (
    <article className="exercise-card self-practice">
      <p className="eyebrow">Activity {number} · self-practice</p>
      <h3>{exercise.prompt}</h3>
      <p className="boundary-note">This activity is not automatically scored.</p>
      {criteria.length > 0 && (
        <ul>{criteria.map((criterion) => <li key={criterion}>{criterion}</li>)}</ul>
      )}
    </article>
  );
}
