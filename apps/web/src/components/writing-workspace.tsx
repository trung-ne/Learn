"use client";

import Link from "next/link";
import { useEffect, useMemo, useState } from "react";
import { getWritingBands, getWritingProtocols, getWritingTiers, writingSnapshot } from "@/content/writing-catalog";
import type { WritingProtocol } from "@/content/writing-types";
import { loadLearner, loadProgress, setActiveLanguage } from "@/lib/progress";
import {
  forkWritingRevision,
  getLatestWritingAttempt,
  importLegacyWritingDraft,
  loadWritingProgress,
  saveWritingDraft,
  saveWritingProgress,
  type WritingProgress,
} from "@/lib/writing-progress";
import { lessonPacketHref } from "@/lib/routes";

const allFilter = "all";
const writingOrientation = [
  ["A1", "Short guided messages with familiar details and basic sentence patterns."],
  ["A2", "Connected everyday messages, descriptions, invitations, and simple accounts."],
  ["B1", "Clear practical writing that explains experiences, opinions, and options."],
  ["B2", "Structured arguments, comparisons, reports, and audience-aware writing."],
  ["C1", "Flexible, well-organized extended writing with controlled register and nuanced development."],
  ["C2", "Precise, sophisticated writing adapted to demanding academic or professional purposes."],
] as const;

export function WritingWorkspace() {
  const protocols = useMemo(() => getWritingProtocols(), []);
  const [bandFilter, setBandFilter] = useState<string>(allFilter);
  const [tierFilter, setTierFilter] = useState<string>(allFilter);
  const [progress, setProgress] = useState<WritingProgress>();

  useEffect(() => {
    const learner = setActiveLanguage(loadLearner(), "en");
    let next = loadWritingProgress({ learnerId: learner.learnerId, language: "en" }, writingSnapshot.inventoryVersion, protocols);
    const courses = new Map(protocols.map((protocol) => [protocol.band, loadProgress({ learnerId: learner.learnerId, language: "en", course: protocol.band })]));
    for (const protocol of protocols) {
      const legacyDraft = courses.get(protocol.band)?.lessons[protocol.lessonId]?.drafts.writing;
      next = importLegacyWritingDraft(next, protocol, legacyDraft, new Date().toISOString());
    }
    setProgress(next);
    saveWritingProgress(next);
  }, [protocols]);

  const bands = getWritingBands();
  const tiers = useMemo(() => getWritingTiers(bandFilter === allFilter ? undefined : bandFilter as WritingProtocol["band"]), [bandFilter]);
  const displayed = useMemo(() => getWritingProtocols({
    ...(bandFilter === allFilter ? {} : { band: bandFilter as WritingProtocol["band"] }),
    ...(tierFilter === allFilter ? {} : { tier: tierFilter }),
  }), [bandFilter, tierFilter]);
  const attemptCount = progress ? Object.keys(progress.attempts).length : undefined;

  function updateDraft(protocol: WritingProtocol, draft: string, attemptId?: string) {
    if (!progress) return;
    const next = saveWritingDraft(progress, protocol, draft, new Date().toISOString(), attemptId);
    setProgress(next);
    saveWritingProgress(next);
  }

  function tryAgain(attemptId: string) {
    if (!progress) return;
    const next = forkWritingRevision(progress, attemptId, new Date().toISOString());
    setProgress(next);
    saveWritingProgress(next);
  }

  return (
    <div className="content-stack writing-workspace" lang="en">
      <section className="catalog-hero writing-hero">
        <div>
          <p className="eyebrow">English supplied writing inventory</p>
          <h1>Writing</h1>
          <p className="lede">Use the supplied writing tasks, keep learner-authored drafts in this browser, and revise your own work. No evaluator is connected.</p>
        </div>
        <dl className="vocabulary-summary" aria-label="Writing availability summary">
          <div><dt>Supplied tasks</dt><dd>{protocols.length}</dd></div>
          <div><dt>Local drafts</dt><dd>{attemptCount ?? "—"}</dd></div>
          <div><dt>Feedback</dt><dd>Unavailable</dd></div>
          <div><dt>Content state</dt><dd>Unreviewed</dd></div>
        </dl>
      </section>

      <section className="page-section writing-boundary" aria-labelledby="writing-boundary-heading">
        <h2 id="writing-boundary-heading">Local writing and feedback boundary</h2>
        <p>Tasks are supplied lesson protocols. Drafts and revisions stay in this browser. No provider, AI correction, score, grammar diagnosis, vocabulary diagnosis, naturalness or coherence evaluation, replacement text, or writing result is available.</p>
        <p>Writing drafts do not update Review, grammar, vocabulary, Mistake/Weakness, assessment/mastery, or a Weakness Engine.</p>
      </section>

      <section className="page-section writing-orientation" aria-labelledby="writing-orientation-heading">
        <p className="eyebrow">Application-authored navigation</p>
        <h2 id="writing-orientation-heading">Writing self-practice orientation</h2>
        <p>This map organizes self-practice navigation only. It does not classify an individual task, assess a draft, or establish learner or CEFR attainment.</p>
        <dl className="speaking-progression-list">{writingOrientation.map(([band, focus]) => <div key={band}><dt>{band}</dt><dd>{focus}</dd></div>)}</dl>
      </section>

      <section className="page-section writing-protocol-list" aria-labelledby="writing-protocols-heading">
        <div className="section-heading">
          <div><p className="eyebrow">Lesson-bound guidance</p><h2 id="writing-protocols-heading">Writing tasks</h2></div>
          <div className="filter-row" aria-label="Filter writing tasks">
            <label>Band<select value={bandFilter} onChange={(event) => { setBandFilter(event.target.value); setTierFilter(allFilter); }}><option value={allFilter}>All bands</option>{bands.map((band) => <option key={band} value={band}>{band}</option>)}</select></label>
            <label>Tier<select value={tierFilter} onChange={(event) => setTierFilter(event.target.value)}><option value={allFilter}>All tiers</option>{tiers.map((tier) => <option key={tier} value={tier}>{tier}</option>)}</select></label>
          </div>
        </div>
        {!progress ? <p className="empty-state">Loading local writing drafts…</p> : displayed.length ? <ol>{displayed.map((protocol) => <WritingTaskCard key={protocol.id} protocol={protocol} progress={progress} onDraftChange={updateDraft} onTryAgain={tryAgain} />)}</ol> : <p className="empty-state">No supplied writing tasks match this filter.</p>}
      </section>
    </div>
  );
}

function WritingTaskCard({
  protocol,
  progress,
  onDraftChange,
  onTryAgain,
}: {
  readonly protocol: WritingProtocol;
  readonly progress: WritingProgress;
  readonly onDraftChange: (protocol: WritingProtocol, draft: string, attemptId?: string) => void;
  readonly onTryAgain: (attemptId: string) => void;
}) {
  const attempt = getLatestWritingAttempt(progress, protocol.id);
  return (
    <li className="writing-protocol-card">
      <div className="section-heading"><div><p className="eyebrow">{protocol.band} · {protocol.tier} · {protocol.topic}</p><h3>{protocol.title}</h3></div><span className="status-pill">Feedback unavailable</span></div>
      <p><strong>Task:</strong> {protocol.instruction}</p>
      <p><strong>Goal:</strong> {protocol.goal}</p>
      <div><strong>Supplied constraints</strong><ul>{protocol.constraints.map((constraint) => <li key={constraint}>{constraint}</li>)}</ul></div>
      <p className="local-marker"><strong>Feedback boundary:</strong> {protocol.feedbackBoundary.replaceAll("_", " ")}</p>
      <FeedbackUnavailable original={attempt?.draft} />
      <label className="writing-draft-field"><span>Your revision</span><textarea rows={7} maxLength={12_000} value={attempt?.draft ?? ""} onChange={(event) => onDraftChange(protocol, event.target.value, attempt?.id)} /></label>
      <div className="writing-task-actions"><button className="secondary-button" type="button" disabled={!attempt} onClick={() => attempt && onTryAgain(attempt.id)}>Try again with a linked revision</button><Link href={lessonPacketHref("en", protocol.band, protocol.unitId, protocol.lessonId)}>Open supplied lesson</Link></div>
    </li>
  );
}

function FeedbackUnavailable({ original }: { readonly original?: string }) {
  const unavailable = "No evaluator is connected, so no feedback exists.";
  return (
    <section className="writing-feedback-unavailable" aria-label="Writing feedback unavailable">
      <h4>Correction workspace</h4>
      <dl>
        <div><dt>Original</dt><dd>{original || "No local draft yet."}</dd></div>
        <div><dt>Corrections</dt><dd>{unavailable}</dd></div>
        <div><dt>Grammar mistakes</dt><dd>{unavailable}</dd></div>
        <div><dt>Vocabulary issues</dt><dd>{unavailable}</dd></div>
        <div><dt>Naturalness</dt><dd>{unavailable}</dd></div>
        <div><dt>Coherence</dt><dd>{unavailable}</dd></div>
        <div><dt>Better alternatives</dt><dd>{unavailable}</dd></div>
        <div><dt>Explanation</dt><dd>{unavailable}</dd></div>
      </dl>
    </section>
  );
}
