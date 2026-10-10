"use client";

import Link from "next/link";
import { useEffect, useMemo, useState } from "react";
import { getSpeakingProtocols } from "@/content/speaking-catalog";
import type { SpeakingAssessment, SpeakingProtocol } from "@/content/speaking-types";
import type { Band, LanguageCode } from "@/content/types";
import { loadLearner, loadProgress, setActiveLanguage, type CourseProgress } from "@/lib/progress";
import { lessonPacketHref } from "@/lib/routes";

const allFilter = "all";
const practiceModes = ["Repeat", "Read aloud", "Controlled response", "Guided response", "Roleplay", "Free speaking"] as const;

const englishProgression = [
  ["A1", "Introduce yourself and exchange simple personal information."],
  ["A2", "Describe familiar routines, experiences, and plans."],
  ["B1", "Explain a problem and discuss practical options."],
  ["B2", "Defend an opinion while responding to a counterpoint."],
  ["C1", "Negotiate a position and adapt to another viewpoint."],
  ["C2", "Discuss nuanced abstract topics with precision."],
] as const;

export function SpeakingWorkspace({ language }: { readonly language: LanguageCode }) {
  const protocols = useMemo(() => getSpeakingProtocols(language), [language]);
  const [progressByBand, setProgressByBand] = useState<Readonly<Partial<Record<Band, CourseProgress>>>>({});
  const [ready, setReady] = useState(false);
  const [bandFilter, setBandFilter] = useState<string>(allFilter);
  const [tierFilter, setTierFilter] = useState<string>(allFilter);

  useEffect(() => {
    setReady(false);
    const learner = setActiveLanguage(loadLearner(), language);
    const nextProgress: Partial<Record<Band, CourseProgress>> = {};
    for (const band of new Set(protocols.map((protocol) => protocol.band))) {
      nextProgress[band] = loadProgress({ learnerId: learner.learnerId, language, course: band });
    }
    setProgressByBand(nextProgress);
    setReady(true);
  }, [language, protocols]);

  const bands = useMemo(() => [...new Set(protocols.map((protocol) => protocol.band))], [protocols]);
  const tiers = useMemo(() => [...new Set(protocols.map((protocol) => protocol.tier))], [protocols]);
  const locallyMarkedIds = useMemo(() => new Set(protocols.filter((protocol) => (
    progressByBand[protocol.band]?.lessons[protocol.lessonId]?.protocols.speaking === true
  )).map((protocol) => protocol.id)), [progressByBand, protocols]);
  const displayed = protocols.filter((protocol) => (
    (bandFilter === allFilter || protocol.band === bandFilter) &&
    (tierFilter === allFilter || protocol.tier === tierFilter)
  ));

  return (
    <div className="content-stack speaking-workspace" lang={language}>
      <section className="catalog-hero speaking-hero">
        <div>
          <p className="eyebrow">{language === "en" ? "English" : "German"} supplied lesson protocols</p>
          <h1>Speaking self-practice</h1>
          <p className="lede">Use stored lesson prompts as a structured local speaking course; mark only your own self-practice in this browser.</p>
        </div>
        <dl className="vocabulary-summary" aria-label="Speaking self-practice summary">
          <div><dt>Supplied protocols</dt><dd>{protocols.length}</dd></div>
          <div><dt>Locally marked</dt><dd>{ready ? locallyMarkedIds.size : "—"}</dd></div>
          <div><dt>Assessment</dt><dd>Not assessed</dd></div>
          <div><dt>Content state</dt><dd>Unreviewed</dd></div>
        </dl>
      </section>

      <section className="page-section speaking-boundary" aria-labelledby="speaking-boundary-heading">
        <h2 id="speaking-boundary-heading">Local-only assessment boundary</h2>
        <p>No recording, chat simulation, provider, generated feedback, score, correction, or spoken/text evaluation is available here.</p>
        <p>All assessment dimensions are <strong>NOT_ASSESSED</strong>. A locally marked protocol records self-practice only; it does not update Review, grammar, vocabulary, Mistake/Weakness, assessment/mastery, or a Weakness Engine.</p>
        <AssessmentAvailability assessment={protocols[0]?.assessment} />
      </section>

      <section className="page-section speaking-course-map" aria-labelledby="speaking-course-map-heading">
        <p className="eyebrow">App-authored self-practice navigation</p>
        <h2 id="speaking-course-map-heading">Speaking practice sequence</h2>
        <p>This navigation does not classify individual supplied protocols, evaluate performance, or establish learner or CEFR progression.</p>
        <ol>{practiceModes.map((mode) => <li key={mode}>{mode}</li>)}</ol>
        {language === "en" ? (
          <>
            <h3>English communicative orientation</h3>
            <dl className="speaking-progression-list">
              {englishProgression.map(([band, focus]) => <div key={band}><dt>{band}</dt><dd>{focus}</dd></div>)}
            </dl>
          </>
        ) : <p className="local-marker">Only the currently available German A1 pilot protocols are shown; no other levels are implied.</p>}
      </section>

      <section className="page-section speaking-protocol-list" aria-labelledby="speaking-protocols-heading">
        <div className="section-heading">
          <div><p className="eyebrow">Lesson-bound guidance</p><h2 id="speaking-protocols-heading">Speaking protocols</h2></div>
          <div className="filter-row" aria-label="Filter speaking protocols">
            <label>Band<select value={bandFilter} onChange={(event) => setBandFilter(event.target.value)}><option value={allFilter}>All bands</option>{bands.map((band) => <option key={band} value={band}>{band}</option>)}</select></label>
            <label>Tier<select value={tierFilter} onChange={(event) => setTierFilter(event.target.value)}><option value={allFilter}>All tiers</option>{tiers.map((tier) => <option key={tier} value={tier}>{tier}</option>)}</select></label>
          </div>
        </div>
        {!ready ? <p className="empty-state">Loading local self-practice markers…</p> : displayed.length ? (
          <ol>{displayed.map((protocol) => <SpeakingProtocolCard key={protocol.id} protocol={protocol} locallyMarked={locallyMarkedIds.has(protocol.id)} />)}</ol>
        ) : <p className="empty-state">No supplied speaking protocols match this filter.</p>}
      </section>
    </div>
  );
}

function AssessmentAvailability({ assessment }: { readonly assessment?: SpeakingAssessment }) {
  if (!assessment) return null;
  return (
    <dl className="speaking-assessment-list" aria-label="Unavailable speaking assessment dimensions">
      {Object.entries(assessment).map(([dimension, value]) => <div key={dimension}><dt>{dimension}</dt><dd>{value.replaceAll("_", " ")}</dd></div>)}
    </dl>
  );
}

function SpeakingProtocolCard({ protocol, locallyMarked }: { readonly protocol: SpeakingProtocol; readonly locallyMarked: boolean }) {
  return (
    <li className="speaking-protocol-card">
      <div className="section-heading">
        <div><p className="eyebrow">{protocol.tier} · {protocol.topic}</p><h3>{protocol.title}</h3></div>
        <span className="status-pill">{protocol.assessment.overall.replaceAll("_", " ")}</span>
      </div>
      <p><strong>Stored instruction:</strong> {protocol.instruction}</p>
      {protocol.goal && <p><strong>Goal:</strong> {protocol.goal}</p>}
      <ProtocolTextList label="Supplied guidance" values={protocol.constraints ?? protocol.checklist} />
      <p className="local-marker"><strong>Local self-practice:</strong> {locallyMarked ? "marked in this browser" : "not marked"}</p>
      <Link href={lessonPacketHref(protocol.language, protocol.band, protocol.unitId, protocol.lessonId)}>Open supplied lesson</Link>
    </li>
  );
}

function ProtocolTextList({ label, values }: { readonly label: string; readonly values?: readonly string[] }) {
  if (!values?.length) return null;
  return <div><strong>{label}</strong><ul>{values.map((value) => <li key={value}>{value}</li>)}</ul></div>;
}
