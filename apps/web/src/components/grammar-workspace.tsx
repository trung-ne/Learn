"use client";

import Link from "next/link";
import { useEffect, useMemo, useState } from "react";
import { getLessonById } from "@/content/catalog";
import { getGrammarTargets, grammarSnapshot } from "@/content/grammar-catalog";
import type { GrammarTarget } from "@/content/grammar-types";
import { activeGrammarTargetIds, isGrammarTargetDue, loadGrammarProgress, type GrammarProgress } from "@/lib/grammar-progress";
import { loadLearner, setActiveLanguage } from "@/lib/progress";
import { lessonPacketHref } from "@/lib/routes";

const filters = ["all", "practising", "locally_consolidated", "due"] as const;
type GrammarFilter = typeof filters[number];

export function GrammarWorkspace() {
  const [progress, setProgress] = useState<GrammarProgress>(() => ({
    version: 1, learnerId: "local-unavailable", language: "en", inventoryVersion: grammarSnapshot.inventoryVersion, targets: {},
  }));
  const [ready, setReady] = useState(false);
  const [filter, setFilter] = useState<GrammarFilter>("all");

  useEffect(() => {
    setReady(false);
    const learner = setActiveLanguage(loadLearner(), "en");
    setProgress(loadGrammarProgress({ learnerId: learner.learnerId, language: "en" }, grammarSnapshot.inventoryVersion));
    setReady(true);
  }, []);

  const now = new Date().toISOString();
  const targets = getGrammarTargets("en");
  const knownTargetIds = useMemo(() => new Set(targets.map((target) => target.id)), [targets]);
  const activeTargetIds = activeGrammarTargetIds(progress, knownTargetIds);
  const activeTargets = new Set(activeTargetIds);
  const dueTargetIds = new Set(targets.filter((target) => {
    const item = progress.targets[target.id];
    return item && isGrammarTargetDue(item, now);
  }).map((target) => target.id));
  const locallyConsolidatedCount = targets.filter((target) => progress.targets[target.id]?.state === "locally_consolidated").length;
  const displayedTargets = targets.filter((target) => matchesFilter(target, filter, progress, dueTargetIds));

  return (
    <div className="content-stack grammar-workspace" lang="en">
      <section className="catalog-hero grammar-hero">
        <div>
          <p className="eyebrow">English A1–C2</p>
          <h1>Grammar practice progress</h1>
          <p className="lede">Track only outcomes from explicitly linked, objectively checked supplied activities.</p>
        </div>
        <dl className="vocabulary-summary" aria-label="Grammar practice summary">
          <div><dt>Linked targets</dt><dd>{targets.length}</dd></div>
          <div><dt>Practised</dt><dd>{activeTargets.size}</dd></div>
          <div><dt>Due</dt><dd>{dueTargetIds.size}</dd></div>
          <div><dt>Locally consolidated</dt><dd>{locallyConsolidatedCount}</dd></div>
        </dl>
      </section>

      <section className="page-section grammar-boundary" aria-labelledby="grammar-boundary-heading">
        <h2 id="grammar-boundary-heading">Local practice indicator</h2>
        <p>These browser-local counts use explicit activity links. They do not diagnose grammar, determine proficiency or CEFR level, or provide placement.</p>
        <p>A supplied activity can contribute the same result to more than one explicitly linked grammar target. The record does not decide which target caused an incorrect outcome.</p>
      </section>

      <section className="page-section grammar-target-list" aria-labelledby="grammar-targets-heading">
        <div className="section-heading">
          <div><p className="eyebrow">Explicitly linked targets</p><h2 id="grammar-targets-heading">Grammar activities</h2></div>
          <div className="filter-row" aria-label="Filter grammar targets">
            {filters.map((candidate) => (
              <button
                key={candidate}
                className={filter === candidate ? "filter-button is-active" : "filter-button"}
                type="button"
                aria-pressed={filter === candidate}
                onClick={() => setFilter(candidate)}
              >
                {filterLabel(candidate)}
              </button>
            ))}
          </div>
        </div>
        {!ready ? <p className="empty-state">Loading local grammar practice records…</p> : displayedTargets.length ? (
          <ol>
            {displayedTargets.map((target) => <GrammarTargetCard key={target.id} target={target} progress={progress.targets[target.id]} />)}
          </ol>
        ) : (
          <p className="empty-state">No grammar targets match this local filter.</p>
        )}
      </section>
    </div>
  );
}

function matchesFilter(
  target: GrammarTarget,
  filter: GrammarFilter,
  progress: GrammarProgress,
  dueTargetIds: ReadonlySet<string>,
): boolean {
  if (filter === "all") return true;
  if (filter === "due") return dueTargetIds.has(target.id);
  return progress.targets[target.id]?.state === filter;
}

function GrammarTargetCard({ target, progress }: { readonly target: GrammarTarget; readonly progress: GrammarProgress["targets"][string] | undefined }) {
  const prerequisites = target.prerequisiteIds
    .map((id) => getGrammarTargets("en").find((candidate) => candidate.id === id))
    .filter((item): item is GrammarTarget => Boolean(item));
  return (
    <li className="grammar-target-card">
      <div>
        <p className="eyebrow">{target.tier} · {target.topic}</p>
        <h3>{target.title}</h3>
        {progress ? (
          <>
            <p><strong>Local activity outcomes:</strong> {progress.correctAttempts} correct and {progress.incorrectOutcomes} incorrect of {progress.attempts}.</p>
            <p><strong>Local schedule:</strong> {progress.state.replaceAll("_", " ")} · next review {new Date(progress.nextReviewAt).toLocaleDateString()}.</p>
          </>
        ) : <p>No explicitly linked objective activity has been checked in this browser yet.</p>}
        {prerequisites.length ? <p><strong>Linked grammar prerequisites:</strong> {prerequisites.map((item) => item.title).join("; ")}</p> : null}
        <details>
          <summary>Linked supplied activities ({target.exerciseBindings.length})</summary>
          <ul>
            {target.exerciseBindings.map((binding) => {
              const lesson = getLessonById("en", target.band, binding.lessonId);
              return lesson ? (
                <li key={`${binding.lessonId}-${binding.exerciseId}`}>
                  <Link href={lessonPacketHref("en", target.band, lesson.unitId, binding.lessonId)}>{lesson.title} · {binding.exerciseId}</Link>
                </li>
              ) : null;
            })}
          </ul>
        </details>
      </div>
    </li>
  );
}

function filterLabel(filter: GrammarFilter): string {
  if (filter === "locally_consolidated") return "Locally consolidated";
  return filter[0].toUpperCase() + filter.slice(1);
}
