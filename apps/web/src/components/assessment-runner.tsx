"use client";

import { useEffect, useMemo, useState } from "react";
import type { AssessmentPackage } from "@/content/assessment-types";
import {
  assessmentDraft,
  emptyAssessmentProgress,
  latestAssessmentAttempt,
  loadAssessmentProgress,
  saveAssessmentDraft,
  saveAssessmentProgress,
  submitAssessment,
  type AssessmentProgress,
  type AssessmentResponse,
} from "@/lib/assessment-progress";
import { loadLearner } from "@/lib/progress";

function titleFor(type: AssessmentPackage["type"]): string {
  return { PLACEMENT: "Placement", LESSON_QUIZ: "Lesson quiz", UNIT_TEST: "Unit checkpoint", LEVEL_TEST: "Level test" }[type];
}
function responseComplete(assessment: AssessmentPackage, responses: Readonly<Record<string, AssessmentResponse>>): boolean {
  return assessment.items.every((item) => {
    const response = responses[item.id];
    if (item.type === "matching") return response !== null && typeof response === "object" && !Array.isArray(response) &&
      "pairs" in item.answerContract && item.answerContract.pairs.every((pair) => typeof response[pair.left] === "string" && response[pair.left].trim().length > 0);
    if (item.type === "ordering") return Array.isArray(response) && "correctOrder" in item.answerContract && response.length === item.answerContract.correctOrder.length;
    return typeof response === "string" && response.trim().length > 0;
  });
}

export function AssessmentRunner({ assessment }: { readonly assessment: AssessmentPackage }) {
  const [progress, setProgress] = useState<AssessmentProgress>(() => emptyAssessmentProgress({ learnerId: "local-unavailable", language: "en" }));
  const [responses, setResponses] = useState<Readonly<Record<string, AssessmentResponse>>>({});
  const [ready, setReady] = useState(false);
  const [retaking, setRetaking] = useState(false);

  useEffect(() => {
    const learner = loadLearner();
    const loaded = loadAssessmentProgress({ learnerId: learner.learnerId, language: "en" });
    setProgress(loaded);
    setResponses(assessmentDraft(loaded, assessment));
    setRetaking(false);
    setReady(true);
  }, [assessment]);

  const latest = latestAssessmentAttempt(progress, assessment);
  const showForm = !latest || retaking;
  const complete = responseComplete(assessment, responses);
  const index = useMemo(() => new Map(assessment.items.map((item, position) => [item.id, position + 1])), [assessment.items]);

  function update(itemId: string, response: AssessmentResponse) {
    const next = { ...responses, [itemId]: response };
    setResponses(next);
    const nextProgress = saveAssessmentDraft(progress, assessment, next);
    setProgress(nextProgress);
    saveAssessmentProgress(nextProgress);
  }
  function submit() {
    if (!complete) return;
    const next = submitAssessment(progress, assessment, responses, new Date().toISOString());
    if (next === progress) return;
    setProgress(next);
    saveAssessmentProgress(next);
    setRetaking(false);
  }
  function retake() {
    const next = saveAssessmentDraft(progress, assessment, {});
    setProgress(next);
    saveAssessmentProgress(next);
    setResponses({});
    setRetaking(true);
  }

  return (
    <div className="content-stack assessment-runner">
      <section className="catalog-hero">
        <div>
          <p className="eyebrow">{titleFor(assessment.type)} · local deterministic result</p>
          <h1>{titleFor(assessment.type)}</h1>
          <p className="lede">{assessment.items.length} supplied objective item{assessment.items.length === 1 ? "" : "s"}. This package remains UNREVIEWED and does not certify proficiency or CEFR attainment.</p>
        </div>
      </section>
      <section className="assessment-boundary" aria-label="Assessment boundary">
        <p>Results stay only in this browser. They do not unlock content, diagnose ability, or measure speaking, writing, pronunciation, or audio listening.</p>
        {assessment.type === "PLACEMENT" && <p>The suggested starting tier is a fixed local heuristic, not a validated placement diagnosis.</p>}
      </section>
      {!ready ? <p className="empty-state">Loading local assessment records…</p> : latest && !showForm ? (
        <section className="assessment-result" aria-live="polite">
          <p className="eyebrow">Latest local attempt</p>
          <h2>{latest.correctCount} / {latest.itemCount}</h2>
          <p>Submitted {new Date(latest.submittedAt).toLocaleString()}.</p>
          {latest.suggestedStartTier && <p><strong>Suggested course starting point: {latest.suggestedStartTier}</strong> — a fixed local heuristic only.</p>}
          <ol className="assessment-item-results">
            {latest.itemResults.map((result) => <li key={result.itemId}>{result.correct ? "Correct" : "Not yet"}: item {index.get(result.itemId)}</li>)}
          </ol>
          <button type="button" className="secondary-button" onClick={retake}>Start a new local attempt</button>
        </section>
      ) : (
        <>
          <ol className="assessment-item-list">
            {assessment.items.map((item) => (
              <li key={item.id}>
                <AssessmentItemInput item={item} number={index.get(item.id) ?? 0} response={responses[item.id]} onChange={(response) => update(item.id, response)} />
              </li>
            ))}
          </ol>
          <button type="button" className="primary-button" disabled={!complete} onClick={submit}>Submit local assessment</button>
          {!complete && <p className="empty-state">Complete every supplied item before submitting.</p>}
        </>
      )}
    </div>
  );
}

function AssessmentItemInput({
  item, number, response, onChange,
}: {
  readonly item: AssessmentPackage["items"][number];
  readonly number: number;
  readonly response: AssessmentResponse | undefined;
  readonly onChange: (response: AssessmentResponse) => void;
}) {
  const record = response !== null && typeof response === "object" && !Array.isArray(response) ? response : {};
  const order = Array.isArray(response) ? response : item.items ?? [];
  const rightOptions = item.type === "matching" && "pairs" in item.answerContract ? item.answerContract.pairs.map((pair) => pair.right).reverse() : [];
  return (
    <article className="exercise-card assessment-item">
      <p className="eyebrow">Item {number} · {item.type.replaceAll("_", " ")}</p>
      <h2>{item.prompt}</h2>
      {item.stimulus && <blockquote>{item.stimulus}</blockquote>}
      {item.question && <p><strong>{item.question}</strong></p>}
      {item.type === "multiple_choice" && item.options ? (
        <fieldset><legend>Choose one answer</legend>{item.options.map((option) => <label className="choice" key={option}><input type="radio" name={item.id} checked={response === option} onChange={() => onChange(option)} />{option}</label>)}</fieldset>
      ) : item.type === "matching" && "pairs" in item.answerContract ? (
        <div className="matching-grid">{item.answerContract.pairs.map((pair) => <label key={pair.left}><span>{pair.left}</span><select value={typeof record[pair.left] === "string" ? record[pair.left] : ""} onChange={(event) => onChange({ ...record, [pair.left]: event.target.value })}><option value="">Choose</option>{rightOptions.map((option) => <option key={option} value={option}>{option}</option>)}</select></label>)}</div>
      ) : item.type === "ordering" && item.items ? (
        <ol className="ordering-list">{order.map((entry, position) => <li key={`${entry}-${position}`}><span>{entry}</span><span className="order-actions"><button type="button" disabled={position === 0} aria-label={`Move ${entry} up`} onClick={() => onChange(swap(order, position, position - 1))}>Up</button><button type="button" disabled={position === order.length - 1} aria-label={`Move ${entry} down`} onClick={() => onChange(swap(order, position, position + 1))}>Down</button></span></li>)}</ol>
      ) : (
        <label>Answer<input value={typeof response === "string" ? response : ""} onChange={(event) => onChange(event.target.value)} /></label>
      )}
    </article>
  );
}

function swap(values: readonly string[], first: number, second: number): readonly string[] {
  const next = [...values];
  [next[first], next[second]] = [next[second]!, next[first]!];
  return next;
}
