"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import {
  getDictionaryEntry,
  getDictionaryRelations,
  getDictionaryEntries,
  dictionarySnapshot,
  searchDictionaryEntries,
} from "@/content/dictionary-catalog";
import type { DictionaryEntry } from "@/content/dictionary-types";
import {
  dictionaryStatus,
  emptyDictionaryProgress,
  loadDictionaryProgress,
  recordDictionaryOutcome,
  saveDictionaryProgress,
  startDictionaryEntry,
  type DictionaryProgress,
  type DictionaryStatus,
} from "@/lib/dictionary-progress";
import { loadLearner, setActiveLanguage } from "@/lib/progress";

const STATUS_LABEL: Readonly<Record<DictionaryStatus, string>> = {
  learned: "✓ learned",
  learning: "◉ learning",
  weak: "! weak",
  not_learned: "○ not learned",
};
const FILTERS = ["all", "learned", "learning", "weak", "not_learned"] as const;
type DictionaryFilter = (typeof FILTERS)[number];

function Status({ status }: { readonly status: DictionaryStatus }) {
  return <span className={`dictionary-status dictionary-status-${status}`} aria-label={`Local status: ${STATUS_LABEL[status]}`}>{STATUS_LABEL[status]}</span>;
}

export function DictionaryWorkspace() {
  const entries = useMemo(() => getDictionaryEntries("en"), []);
  const knownIds = useMemo(() => entries.map((entry) => entry.id), [entries]);
  const [progress, setProgress] = useState<DictionaryProgress>(() =>
    emptyDictionaryProgress({ learnerId: "local-unavailable", language: "en" }, dictionarySnapshot.inventoryVersion));
  const [ready, setReady] = useState(false);
  const [query, setQuery] = useState("");
  const [filter, setFilter] = useState<DictionaryFilter>("all");
  const [selectedId, setSelectedId] = useState<string>();

  const refresh = useCallback(() => {
    const learner = setActiveLanguage(loadLearner(), "en");
    setProgress(loadDictionaryProgress({ learnerId: learner.learnerId, language: "en" }, dictionarySnapshot.inventoryVersion, knownIds));
    setReady(true);
  }, [knownIds]);

  useEffect(() => {
    setReady(false);
    refresh();
    const onStorage = (event: StorageEvent) => {
      if (!event.key || event.storageArea !== window.localStorage) return;
      refresh();
    };
    window.addEventListener("focus", refresh);
    window.addEventListener("storage", onStorage);
    return () => {
      window.removeEventListener("focus", refresh);
      window.removeEventListener("storage", onStorage);
    };
  }, [refresh]);

  const displayed = useMemo(() => searchDictionaryEntries("en", query).filter((entry) =>
    filter === "all" || dictionaryStatus(progress.entries[entry.id]) === filter), [filter, progress.entries, query]);
  const selected = selectedId ? getDictionaryEntry(selectedId) : undefined;

  function commit(next: DictionaryProgress) {
    setProgress(next);
    saveDictionaryProgress(next);
  }

  function start(entry: DictionaryEntry) {
    if (!ready) return;
    commit(startDictionaryEntry(progress, entry.id, new Date().toISOString()));
  }

  function result(entry: DictionaryEntry, correct: boolean) {
    if (!ready) return;
    commit(recordDictionaryOutcome(progress, entry.id, correct, new Date().toISOString()));
  }

  return <div className="content-stack dictionary-workspace" lang="en">
    <section className="catalog-hero dictionary-hero">
      <div>
        <p className="eyebrow">Original-authored local library</p>
        <h1>Dictionary / Language Library</h1>
        <p className="lede">Search the supplied lexical records, keep local study signals, and inspect explicitly linked senses and word forms.</p>
      </div>
    </section>
    <section className="dictionary-boundary" aria-labelledby="dictionary-boundary-heading">
      <h2 id="dictionary-boundary-heading">Local-status boundary</h2>
      <p>Status markers use browser-local supplied recall outcomes only. They do not establish proficiency, CEFR attainment, retention, diagnosis, or language mastery. Displayed bands are `UNREVIEWED` authored labels, not independently validated CEFR decisions.</p>
    </section>
    <section className="page-section" aria-labelledby="dictionary-search-heading">
      <div className="section-heading"><div><p className="eyebrow">Supplied records only</p><h2 id="dictionary-search-heading">Search the library</h2></div><p>The current library is a bounded `take` family, not a complete dictionary.</p></div>
      <label className="dictionary-search">Search a supplied word, meaning, phrase, band, or tier
        <input value={query} onChange={(event) => setQuery(event.target.value)} placeholder="Search take" type="search" />
      </label>
      <div className="library-filters" aria-label="Dictionary status filter">
        {FILTERS.map((candidate) => <button key={candidate} type="button" className="text-button" aria-pressed={filter === candidate} onClick={() => setFilter(candidate)}>
          {candidate === "all" ? "All records" : STATUS_LABEL[candidate]}
        </button>)}
      </div>
      {displayed.length ? <ul className="dictionary-results">
        {displayed.map((entry) => <li key={entry.id}><button type="button" onClick={() => setSelectedId(entry.id)}>
          <Status status={dictionaryStatus(progress.entries[entry.id])} />
          <strong>{entry.headword}</strong>
          <span>{entry.kind === "word_sense" ? `Sense ${entry.senseNumber}` : entry.kind.replaceAll("_", " ")} · {entry.band} · {entry.tier}</span>
          <span>{entry.vietnameseMeaning ?? entry.definition}</span>
        </button></li>)}
      </ul> : <p className="empty-state">No supplied dictionary record matches this local view.</p>}
    </section>
    {selected ? <DictionaryDetail entry={selected} status={dictionaryStatus(progress.entries[selected.id])} ready={ready} onClose={() => setSelectedId(undefined)} onStart={() => start(selected)} onResult={(correct) => result(selected, correct)} /> : null}
  </div>;
}

function DictionaryDetail({ entry, status, ready, onClose, onStart, onResult }: {
  readonly entry: DictionaryEntry;
  readonly status: DictionaryStatus;
  readonly ready: boolean;
  readonly onClose: () => void;
  readonly onStart: () => void;
  readonly onResult: (correct: boolean) => void;
}) {
  const senses = getDictionaryRelations(entry, "senseIds");
  const phrasalVerbs = getDictionaryRelations(entry, "phrasalVerbIds");
  const wordFamily = getDictionaryRelations(entry, "wordFamilyIds");
  const familyCollocations = [...new Set(senses.flatMap((sense) => sense.collocations))];
  return <section className="page-section dictionary-detail" aria-labelledby="dictionary-entry-heading">
    <div className="section-heading"><div><p className="eyebrow"><Status status={status} /></p><h2 id="dictionary-entry-heading">{entry.headword}</h2></div><button type="button" className="text-button" onClick={onClose}>Close entry</button></div>
    <p><strong>{entry.kind === "word_sense" ? `Sense ${entry.senseNumber}` : entry.kind.replaceAll("_", " ")}</strong> · {entry.partOfSpeech} · {entry.band} · {entry.tier}</p>
    {entry.ipa ? <p className="dictionary-ipa">{entry.ipa}</p> : null}
    <p>{entry.vietnameseMeaning ? <><strong>{entry.vietnameseMeaning}</strong> — </> : null}{entry.definition}</p>
    <h3>Examples</h3><ul>{entry.examples.map((example) => <li key={example}>{example}</li>)}</ul>
    <h3>Collocations</h3><ul>{entry.collocations.map((collocation) => <li key={collocation}>{collocation}</li>)}</ul>
    {familyCollocations.length > entry.collocations.length ? <><h3>Supplied family collocations</h3><ul>{familyCollocations.map((collocation) => <li key={collocation}>{collocation}</li>)}</ul></> : null}
    <DictionaryLinks title="Senses" entries={senses} />
    <DictionaryLinks title="Phrasal verbs" entries={phrasalVerbs} />
    <DictionaryLinks title="Word family" entries={wordFamily} />
    {status === "not_learned" ? <button type="button" className="secondary-button" disabled={!ready} onClick={onStart}>Start local study</button> : <div className="dictionary-recall"><h3>Supplied recall check</h3><p>{entry.recall.prompt}</p><div className="button-row"><button type="button" disabled={!ready} className="primary-button" onClick={() => onResult(true)}>I recalled it</button><button type="button" disabled={!ready} className="secondary-button" onClick={() => onResult(false)}>I need to review it</button></div></div>}
  </section>;
}

function DictionaryLinks({ title, entries }: { readonly title: string; readonly entries: readonly DictionaryEntry[] }) {
  return <section className="dictionary-links"><h3>{title}</h3>{entries.length ? <ul>{entries.map((entry) => <li key={entry.id}>{entry.headword}{entry.senseNumber ? ` — Sense ${entry.senseNumber}` : ""} ({entry.band})</li>)}</ul> : <p>No explicitly supplied {title.toLowerCase()} are available for this entry.</p>}</section>;
}
