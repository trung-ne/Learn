"use client";

import Link from "next/link";
import { useEffect, useMemo, useState } from "react";
import { getAssessmentPackages } from "@/content/assessment-catalog";
import {
  aggregateAssessmentEvidence,
  emptyAssessmentProgress,
  latestAssessmentAttempt,
  loadAssessmentProgress,
  type AssessmentProgress,
} from "@/lib/assessment-progress";
import { loadLearner } from "@/lib/progress";
import { assessmentPackageHref } from "@/lib/routes";

interface EvidenceRow {
  readonly label: string;
  readonly key?: string;
  readonly limitation?: string;
}

const evidenceRows: readonly EvidenceRow[] = [
  { label: "Vocabulary", key: "vocabulary_senses", limitation: "Only items explicitly tagged with vocabulary-sense targets count." },
  { label: "Grammar", key: "grammar", limitation: "Only items explicitly tagged with grammar targets count." },
  { label: "Reading", key: "item:reading", limitation: "Only submitted supplied reading items count." },
  { label: "Listening", key: "item:listening", limitation: "These are transcript-only items, not audio-listening assessment." },
  { label: "Writing", limitation: "NOT_ASSESSED: the current browser tools do not score learner writing." },
  { label: "Speaking", limitation: "NOT_ASSESSED: the current browser tools do not capture or score speech." },
  { label: "Pronunciation", limitation: "NOT_ASSESSED: the current browser tools do not analyse or score audio." },
  { label: "Retention", limitation: "No retention score is available. Existing review scheduling is not a retention measurement." },
];

function percentage(correct: number, total: number): string { return `${Math.round((correct / total) * 100)}%`; }

export function AssessmentDashboard() {
  const [progress, setProgress] = useState<AssessmentProgress>(() => emptyAssessmentProgress({ learnerId: "local-unavailable", language: "en" }));
  const [ready, setReady] = useState(false);
  const packages = getAssessmentPackages();

  useEffect(() => {
    const learner = loadLearner();
    setProgress(loadAssessmentProgress({ learnerId: learner.learnerId, language: "en" }));
    setReady(true);
  }, []);

  const attempts = useMemo(() => packages.flatMap((assessment) => {
    const attempt = latestAssessmentAttempt(progress, assessment);
    return attempt ? [{ assessment, attempt }] : [];
  }), [packages, progress]);
  const evidence = useMemo(() => aggregateAssessmentEvidence(progress), [progress]);
  const completedByType = useMemo(() => packages.reduce<Record<string, number>>((result, assessment) => ({ ...result, [assessment.type]: (result[assessment.type] ?? 0) + 1 }), {}), [packages]);
  const submittedByType = useMemo(() => attempts.reduce<Record<string, number>>((result, entry) => ({ ...result, [entry.assessment.type]: (result[entry.assessment.type] ?? 0) + 1 }), {}), [attempts]);
  const measuredRows = evidenceRows.filter((row) => row.key && evidence[row.key]?.total).map((row) => ({ ...row, total: evidence[row.key!].total, correct: evidence[row.key!].correct }));
  const missingCheckpoints = (["PLACEMENT", "LESSON_QUIZ", "UNIT_TEST", "LEVEL_TEST"] as const).filter((type) => !submittedByType[type]);
  const lowest = [...measuredRows].sort((left, right) => left.correct / left.total - right.correct / right.total)[0];

  return (
    <section className="assessment-dashboard" aria-labelledby="assessment-evidence-heading">
      <div className="section-heading">
        <div><p className="eyebrow">Local evidence dashboard</p><h2 id="assessment-evidence-heading">Assessment evidence, not course unlocks</h2></div>
        <p>Local lesson completion does not prove language ability. This page shows only supplied deterministic assessment results.</p>
      </div>
      {!ready ? <p className="empty-state">Loading local assessment evidence…</p> : (
        <>
          <dl className="assessment-stage-summary">
            <div><dt>Placement</dt><dd>{submittedByType.PLACEMENT ?? 0} / {completedByType.PLACEMENT ?? 0} submitted</dd></div>
            <div><dt>Lesson quizzes</dt><dd>{submittedByType.LESSON_QUIZ ?? 0} / {completedByType.LESSON_QUIZ ?? 0} submitted</dd></div>
            <div><dt>Unit checkpoints</dt><dd>{submittedByType.UNIT_TEST ?? 0} / {completedByType.UNIT_TEST ?? 0} submitted</dd></div>
            <div><dt>Level tests</dt><dd>{submittedByType.LEVEL_TEST ?? 0} / {completedByType.LEVEL_TEST ?? 0} submitted</dd></div>
          </dl>
          <div className="assessment-evidence-grid">
            {evidenceRows.map((row) => {
              const total = row.key ? evidence[row.key] : undefined;
              return <article key={row.label} className="assessment-evidence-card"><h3>{row.label}</h3>{total?.total ? <><strong>{percentage(total.correct, total.total)}</strong><p>{total.correct} / {total.total} supplied submitted items.</p><small>{row.limitation}</small></> : <><strong>NOT_ASSESSED</strong><p>{row.key ? "No submitted applicable local evidence." : row.limitation}</p>{row.key && <small>{row.limitation}</small>}</>}</article>;
            })}
          </div>
          <section className="assessment-bottlenecks" aria-labelledby="assessment-next-heading">
            <h3 id="assessment-next-heading">What needs evidence next</h3>
            {missingCheckpoints.length > 0 ? <p>Missing local checkpoint evidence: {missingCheckpoints.map((type) => type.replaceAll("_", " ").toLowerCase()).join(", ")}.</p> : lowest ? <p>Among directly measured local rows, the lowest current result is {lowest.label}: {percentage(lowest.correct, lowest.total)} ({lowest.correct} / {lowest.total}). This is a factual result, not a diagnosis.</p> : <p>No directly measured local skill evidence is available yet.</p>}
            <p>Skill checkpoint and comprehensive assessment are unavailable because the current immutable inventory cannot validly assess all requested skills.</p>
          </section>
          {attempts.length > 0 && <section className="assessment-recent-results" aria-labelledby="assessment-recent-heading"><h3 id="assessment-recent-heading">Recent submitted local results</h3><ul>{[...attempts].sort((left, right) => right.attempt.submittedAt.localeCompare(left.attempt.submittedAt)).slice(0, 8).map(({ assessment, attempt }) => <li key={`${assessment.id}-${attempt.attemptId}`}><Link href={assessmentPackageHref(assessment.id)}>{assessment.type.replaceAll("_", " ")}</Link>: {attempt.correctCount} / {attempt.itemCount}</li>)}</ul></section>}
        </>
      )}
    </section>
  );
}
