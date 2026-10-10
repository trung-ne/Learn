"use client";

import { useEffect, useMemo, useRef, useState, type RefObject } from "react";
import type { DisplayExercise } from "@/content/types";
import { arraysMatch, matchesAnyAnswer } from "@/lib/answers";
import { isObjectiveExerciseType } from "@/lib/review-progress";
import type { ExerciseResult, ExerciseRunnerState } from "@/lib/progress";

const selfPracticeTypes = new Set(["speaking", "writing"]);

interface ExerciseListProps {
  readonly exercises: readonly DisplayExercise[];
  readonly runner?: ExerciseRunnerState;
  readonly onCheck: (exerciseId: string, result: "correct" | "incorrect") => void;
  readonly onAdvance: (nextExerciseId: string | undefined) => void;
  readonly onSelfPractice: (exerciseId: string, nextExerciseId: string | undefined) => void;
  readonly onRestart: () => void;
}

export function ExerciseList({
  exercises,
  runner,
  onCheck,
  onAdvance,
  onSelfPractice,
  onRestart,
}: ExerciseListProps) {
  const currentIndex = currentExerciseIndex(exercises, runner?.currentExerciseId);
  const focusTarget = useRef<HTMLHeadingElement>(null);
  const [shouldMoveFocus, setShouldMoveFocus] = useState(false);

  useEffect(() => {
    if (!shouldMoveFocus) return;
    focusTarget.current?.focus();
    setShouldMoveFocus(false);
  }, [runner?.currentExerciseId, runner?.finished, shouldMoveFocus]);

  function advance(nextExerciseId: string | undefined) {
    setShouldMoveFocus(true);
    onAdvance(nextExerciseId);
  }

  function selfPractice(exerciseId: string, nextExerciseId: string | undefined) {
    setShouldMoveFocus(true);
    onSelfPractice(exerciseId, nextExerciseId);
  }

  function restart() {
    setShouldMoveFocus(true);
    onRestart();
  }

  if (!exercises.length) {
    return <p className="empty-state">No exercises are available for this lesson yet.</p>;
  }

  if (runner?.finished) {
    return (
      <section className="exercise-finish" aria-live="polite">
        <h3 ref={focusTarget} tabIndex={-1}>Practice set complete</h3>
        <p>You have reached the end of the supplied activities.</p>
        <button className="secondary-button" type="button" onClick={restart}>
          Restart practice
        </button>
      </section>
    );
  }

  const exercise = exercises[currentIndex]!;
  const nextExerciseId = exercises[currentIndex + 1]?.id;
  const isFinal = nextExerciseId === undefined;

  return (
    <div className="exercise-runner">
      <div className="exercise-progress" aria-live="polite">
        <span>
          Activity {currentIndex + 1} of {exercises.length}
        </span>
        <progress
          aria-label={`Activity ${currentIndex + 1} of ${exercises.length}`}
          max={exercises.length}
          value={currentIndex + 1}
        >
          Activity {currentIndex + 1} of {exercises.length}
        </progress>
      </div>
      {isObjectiveExerciseType(exercise.type) ? (
        <ObjectiveExercise
          key={exercise.id}
          focusTarget={focusTarget}
          exercise={exercise}
          number={currentIndex + 1}
          onCheck={onCheck}
          onAdvance={advance}
          nextExerciseId={nextExerciseId}
          savedResult={runner?.exercises[exercise.id]?.lastResult}
          isFinal={isFinal}
        />
      ) : selfPracticeTypes.has(exercise.type) ? (
        <SelfPracticeExercise
          key={exercise.id}
          focusTarget={focusTarget}
          exercise={exercise}
          number={currentIndex + 1}
          onSelfPractice={selfPractice}
          nextExerciseId={nextExerciseId}
          isFinal={isFinal}
        />
      ) : (
        <UnsupportedExercise
          focusTarget={focusTarget}
          exercise={exercise}
          number={currentIndex + 1}
          onAdvance={advance}
          nextExerciseId={nextExerciseId}
          isFinal={isFinal}
        />
      )}
    </div>
  );
}

function currentExerciseIndex(
  exercises: readonly DisplayExercise[],
  currentExerciseId: string | undefined,
): number {
  if (!currentExerciseId) return 0;
  const index = exercises.findIndex((exercise) => exercise.id === currentExerciseId);
  return index >= 0 ? index : 0;
}

function Feedback({
  correct,
  explanation,
}: {
  readonly correct: boolean;
  readonly explanation?: string;
}) {
  return (
    <div className={correct ? "feedback correct" : "feedback incorrect"} role="status">
      <strong>{correct ? "Correct." : "Not yet."}</strong>{" "}
      {correct
        ? "Your response matches the supplied answer data."
        : "Review the activity and try again."}
      {explanation && <p>{explanation}</p>}
    </div>
  );
}

function ObjectiveExercise({
  focusTarget,
  exercise,
  number,
  onCheck,
  onAdvance,
  nextExerciseId,
  savedResult,
  isFinal,
}: {
  readonly focusTarget: RefObject<HTMLHeadingElement | null>;
  readonly exercise: DisplayExercise;
  readonly number: number;
  readonly onCheck: (exerciseId: string, result: "correct" | "incorrect") => void;
  readonly onAdvance: (nextExerciseId: string | undefined) => void;
  readonly nextExerciseId: string | undefined;
  readonly savedResult: ExerciseResult | undefined;
  readonly isFinal: boolean;
}) {
  const [answer, setAnswer] = useState("");
  const [checked, setChecked] = useState<boolean | null>(
    savedResult === "correct" ? true : savedResult === "incorrect" ? false : null,
  );
  const [order, setOrder] = useState<readonly string[]>(exercise.items ?? []);
  const [matches, setMatches] = useState<Record<string, string>>({});
  const [questionAnswers, setQuestionAnswers] = useState<Record<number, string>>({});
  const rightOptions = useMemo(
    () => [...(exercise.pairs ?? [])].map((pair) => pair.right).reverse(),
    [exercise.pairs],
  );

  function evaluate(): boolean {
    if (exercise.type === "matching") {
      const pairs = exercise.pairs ?? [];
      return pairs.length > 0 && pairs.every((pair) => matches[pair.left] === pair.right);
    }
    if (exercise.type === "ordering") {
      return (
        (exercise.correct_order?.length ?? 0) > 0 &&
        arraysMatch(order, exercise.correct_order ?? [])
      );
    }
    if (exercise.type === "reading" || exercise.type === "listening") {
      const questions = exercise.questions ?? [];
      return (
        questions.length > 0 &&
        questions.every((question, index) =>
          matchesAnyAnswer(questionAnswers[index] ?? "", question.acceptable_answers),
        )
      );
    }
    const expected = exercise.correct_answer
      ? [exercise.correct_answer]
      : exercise.acceptable_answers ?? (exercise.answer ? [exercise.answer] : []);
    return expected.length > 0 && matchesAnyAnswer(answer, expected);
  }

  function reset() {
    setAnswer("");
    setOrder(exercise.items ?? []);
    setMatches({});
    setQuestionAnswers({});
    setChecked(null);
  }

  function check() {
    const correct = evaluate();
    setChecked(correct);
    onCheck(exercise.id, correct ? "correct" : "incorrect");
  }

  const canCheck =
    exercise.type === "matching"
      ? (exercise.pairs?.length ?? 0) > 0 &&
        (exercise.pairs ?? []).every((pair) => matches[pair.left])
      : exercise.type === "ordering"
        ? order.length > 0
        : exercise.type === "reading" || exercise.type === "listening"
          ? (exercise.questions?.length ?? 0) > 0 &&
            (exercise.questions ?? []).every((_, index) => questionAnswers[index]?.trim())
          : answer.trim().length > 0;

  return (
    <article className="exercise-card">
      <p className="eyebrow">
        Activity {number} · {exercise.type.replaceAll("_", " ")}
      </p>
      <h3 ref={focusTarget} tabIndex={-1}>{exercise.prompt}</h3>
      {exercise.stimulus && <blockquote>{exercise.stimulus}</blockquote>}

      {exercise.type === "multiple_choice" && exercise.options ? (
        <fieldset>
          <legend>Choose one answer</legend>
          {exercise.options.map((option) => (
            <label className="choice" key={option}>
              <input
                type="radio"
                name={exercise.id}
                checked={answer === option}
                onChange={() => setAnswer(option)}
              />
              {option}
            </label>
          ))}
        </fieldset>
      ) : exercise.type === "matching" && exercise.pairs ? (
        <div className="matching-grid">
          {exercise.pairs.map((pair) => (
            <label key={pair.left}>
              <span>{pair.left}</span>
              <select
                value={matches[pair.left] ?? ""}
                onChange={(event) =>
                  setMatches((current) => ({ ...current, [pair.left]: event.target.value }))
                }
              >
                <option value="">Choose</option>
                {rightOptions.map((option) => (
                  <option key={option} value={option}>
                    {option}
                  </option>
                ))}
              </select>
            </label>
          ))}
        </div>
      ) : exercise.type === "ordering" && exercise.items ? (
        <ol className="ordering-list">
          {order.map((item, index) => (
            <li key={`${item}-${index}`}>
              <span>{item}</span>
              <span className="order-actions">
                <button
                  type="button"
                  aria-label={`Move ${item} up`}
                  disabled={index === 0}
                  onClick={() => setOrder((items) => swap(items, index, index - 1))}
                >
                  Up
                </button>
                <button
                  type="button"
                  aria-label={`Move ${item} down`}
                  disabled={index === order.length - 1}
                  onClick={() => setOrder((items) => swap(items, index, index + 1))}
                >
                  Down
                </button>
              </span>
            </li>
          ))}
        </ol>
      ) : exercise.type === "reading" || exercise.type === "listening" ? (
        <div className="question-list">
          {(exercise.questions ?? []).map((question, index) => (
            <label key={question.question}>
              <span>{question.question}</span>
              <input
                value={questionAnswers[index] ?? ""}
                onChange={(event) =>
                  setQuestionAnswers((current) => ({ ...current, [index]: event.target.value }))
                }
              />
            </label>
          ))}
        </div>
      ) : (
        <label>
          <span>Your answer</span>
          <input value={answer} onChange={(event) => setAnswer(event.target.value)} />
        </label>
      )}

      {checked === null ? (
        <button className="primary-button" type="button" disabled={!canCheck} onClick={check}>
          Check answer
        </button>
      ) : (
        <div className="exercise-actions">
          <Feedback correct={checked} explanation={exercise.explanation} />
          <button className="secondary-button" type="button" onClick={reset}>
            Retry
          </button>
          <button className="primary-button" type="button" onClick={() => onAdvance(nextExerciseId)}>
            {isFinal ? "Finish practice" : "Next activity"}
          </button>
        </div>
      )}
    </article>
  );
}

function SelfPracticeExercise({
  focusTarget,
  exercise,
  number,
  onSelfPractice,
  nextExerciseId,
  isFinal,
}: {
  readonly focusTarget: RefObject<HTMLHeadingElement | null>;
  readonly exercise: DisplayExercise;
  readonly number: number;
  readonly onSelfPractice: (exerciseId: string, nextExerciseId: string | undefined) => void;
  readonly nextExerciseId: string | undefined;
  readonly isFinal: boolean;
}) {
  const criteria =
    typeof exercise.rubric === "string" ? [exercise.rubric] : exercise.rubric?.criteria ?? [];
  return (
    <article className="exercise-card">
      <p className="eyebrow">Activity {number} · self-practice</p>
      <h3 ref={focusTarget} tabIndex={-1}>{exercise.prompt}</h3>
      <p className="boundary-note">
        This activity is not automatically scored. Use the supplied guidance to review your own response.
      </p>
      {criteria.length > 0 && (
        <>
          <h4>Guidance</h4>
          <ul>{criteria.map((criterion) => <li key={criterion}>{criterion}</li>)}</ul>
        </>
      )}
      <button
        className="primary-button"
        type="button"
        onClick={() => onSelfPractice(exercise.id, nextExerciseId)}
      >
        {isFinal ? "Finish practice" : "Next activity"}
      </button>
    </article>
  );
}

function UnsupportedExercise({
  focusTarget,
  exercise,
  number,
  onAdvance,
  nextExerciseId,
  isFinal,
}: {
  readonly focusTarget: RefObject<HTMLHeadingElement | null>;
  readonly exercise: DisplayExercise;
  readonly number: number;
  readonly onAdvance: (nextExerciseId: string | undefined) => void;
  readonly nextExerciseId: string | undefined;
  readonly isFinal: boolean;
}) {
  return (
    <article className="exercise-card">
      <p className="eyebrow">Activity {number}</p>
      <h3 ref={focusTarget} tabIndex={-1}>This activity is not available in the current learner interface.</h3>
      <p className="boundary-note">Its supplied exercise type is not supported by this local runner.</p>
      <button className="secondary-button" type="button" onClick={() => onAdvance(nextExerciseId)}>
        {isFinal ? "Finish practice" : "Skip unavailable activity"}
      </button>
    </article>
  );
}

function swap(items: readonly string[], first: number, second: number): readonly string[] {
  const next = [...items];
  [next[first], next[second]] = [next[second]!, next[first]!];
  return next;
}
