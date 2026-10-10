"use client";

import Link from "next/link";
import { useEffect, useMemo, useState } from "react";
import { getPronunciationProtocols } from "@/content/pronunciation-catalog";
import type { PronunciationProtocol } from "@/content/pronunciation-types";
import type { Band, LanguageCode } from "@/content/types";
import { loadLearner, loadProgress, setActiveLanguage, type CourseProgress } from "@/lib/progress";
import { lessonPacketHref } from "@/lib/routes";

const allFilter = "all";

export function PronunciationWorkspace({ language }: { readonly language: LanguageCode }) {
  const protocols = useMemo(() => getPronunciationProtocols(language), [language]);
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
    progressByBand[protocol.band]?.lessons[protocol.lessonId]?.protocols.pronunciation === true
  )).map((protocol) => protocol.id)), [progressByBand, protocols]);
  const displayed = protocols.filter((protocol) => (
    (bandFilter === allFilter || protocol.band === bandFilter) &&
    (tierFilter === allFilter || protocol.tier === tierFilter)
  ));
  const targetCount = protocols.filter((protocol) => Boolean(protocol.target)).length;

  return (
    <div className="content-stack pronunciation-workspace" lang={language}>
      <section className="catalog-hero pronunciation-hero">
        <div>
          <p className="eyebrow">{language === "en" ? "English" : "German"} supplied lesson protocols</p>
          <h1>Pronunciation self-practice</h1>
          <p className="lede">Find stored lesson guidance and mark only your own self-practice in this browser.</p>
        </div>
        <dl className="vocabulary-summary" aria-label="Pronunciation self-practice summary">
          <div><dt>Supplied protocols</dt><dd>{protocols.length}</dd></div>
          <div><dt>Target-labelled</dt><dd>{targetCount}</dd></div>
          <div><dt>Locally marked</dt><dd>{ready ? locallyMarkedIds.size : "—"}</dd></div>
          <div><dt>Not assessed</dt><dd>{protocols.length}</dd></div>
        </dl>
      </section>

      <section className="page-section pronunciation-boundary" aria-labelledby="pronunciation-boundary-heading">
        <h2 id="pronunciation-boundary-heading">Audio-free boundary</h2>
        <p>No model audio, recording, upload, speech recognition, acoustic scoring, or pronunciation, word-stress, fluency, or intonation result is available here.</p>
        <p>Every supplied protocol is <strong>NOT_ASSESSED</strong>. A locally marked protocol records self-practice only; it does not update Review, grammar or vocabulary progress, Mistake/Weakness, or a Weakness Engine.</p>
      </section>

      <section className="page-section pronunciation-protocol-list" aria-labelledby="pronunciation-protocols-heading">
        <div className="section-heading">
          <div><p className="eyebrow">Lesson-bound guidance</p><h2 id="pronunciation-protocols-heading">Pronunciation protocols</h2></div>
          <div className="filter-row" aria-label="Filter pronunciation protocols">
            <label>Band<select value={bandFilter} onChange={(event) => setBandFilter(event.target.value)}><option value={allFilter}>All bands</option>{bands.map((band) => <option key={band} value={band}>{band}</option>)}</select></label>
            <label>Tier<select value={tierFilter} onChange={(event) => setTierFilter(event.target.value)}><option value={allFilter}>All tiers</option>{tiers.map((tier) => <option key={tier} value={tier}>{tier}</option>)}</select></label>
          </div>
        </div>
        {!ready ? <p className="empty-state">Loading local self-practice markers…</p> : displayed.length ? (
          <ol>{displayed.map((protocol) => <PronunciationProtocolCard key={protocol.id} protocol={protocol} locallyMarked={locallyMarkedIds.has(protocol.id)} />)}</ol>
        ) : <p className="empty-state">No supplied pronunciation protocols match this filter.</p>}
      </section>
    </div>
  );
}

function PronunciationProtocolCard({ protocol, locallyMarked }: { readonly protocol: PronunciationProtocol; readonly locallyMarked: boolean }) {
  return (
    <li className="pronunciation-protocol-card">
      <div className="section-heading">
        <div><p className="eyebrow">{protocol.tier} · {protocol.topic}</p><h3>{protocol.title}</h3></div>
        <span className="status-pill">{protocol.assessmentAvailability.replaceAll("_", " ")}</span>
      </div>
      <p><strong>Stored instruction:</strong> {protocol.instruction}</p>
      {protocol.target && <p><strong>Supplied target:</strong> {protocol.target}</p>}
      {protocol.goal && <p><strong>Goal:</strong> {protocol.goal}</p>}
      <ProtocolTextList label="Supplied guidance" values={protocol.constraints ?? protocol.checklist} />
      <ProtocolTextList label="Supplied examples" values={protocol.examples} />
      {protocol.explanation && <p><strong>Supplied explanation:</strong> {protocol.explanation}</p>}
      <p className="local-marker"><strong>Local self-practice:</strong> {locallyMarked ? "marked in this browser" : "not marked"}</p>
      <Link href={lessonPacketHref(protocol.language, protocol.band, protocol.unitId, protocol.lessonId)}>Open supplied lesson</Link>
    </li>
  );
}

function ProtocolTextList({ label, values }: { readonly label: string; readonly values?: readonly string[] }) {
  if (!values?.length) return null;
  return <div><strong>{label}</strong><ul>{values.map((value) => <li key={value}>{value}</li>)}</ul></div>;
}
