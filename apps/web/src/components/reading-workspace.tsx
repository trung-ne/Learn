"use client";

import { useEffect, useMemo, useRef, useState, type ReactNode } from "react";
import { matchesAnyAnswer } from "@/lib/answers";
import { getReadingBands, getReadingReaders, getReadingTiers, readingSnapshot } from "@/content/reading-catalog";
import type { ReadingReader } from "@/content/reading-types";
import { getVocabularySense, vocabularySnapshot } from "@/content/vocabulary-catalog";
import { loadLearner, setActiveLanguage } from "@/lib/progress";
import { emptyReadingProgress, loadReadingProgress, saveReadingProgress, toggleReadingBookmark, type ReadingProgress } from "@/lib/reading-progress";
import { loadVocabularyProgress, saveVocabularyProgress, startWordSense, type VocabularyProgress } from "@/lib/vocabulary-progress";
import { ReadingWordSenseDetail } from "./reading-word-sense-detail";

const allFilter = "all";

export function ReadingWorkspace() {
  const [bandFilter, setBandFilter] = useState<string>(allFilter);
  const [tierFilter, setTierFilter] = useState<string>(allFilter);
  const [progress, setProgress] = useState<ReadingProgress>(() => emptyReadingProgress({ learnerId: "local-unavailable", language: "en" }, readingSnapshot.inventoryVersion));
  const [vocabularyProgress, setVocabularyProgress] = useState<VocabularyProgress | undefined>();
  const [ready, setReady] = useState(false);

  useEffect(() => {
    const learner = setActiveLanguage(loadLearner(), "en");
    setProgress(loadReadingProgress({ learnerId: learner.learnerId, language: "en" }, readingSnapshot.inventoryVersion));
    setVocabularyProgress(loadVocabularyProgress({ learnerId: learner.learnerId, language: "en" }, vocabularySnapshot.inventoryVersion));
    setReady(true);
  }, []);

  const bands = getReadingBands();
  const tiers = useMemo(() => getReadingTiers(bandFilter === allFilter ? undefined : bandFilter as ReadingReader["band"]), [bandFilter]);
  const objectiveReaders = useMemo(() => getReadingReaders({
    mode: "GRADED_OBJECTIVE",
    ...(bandFilter === allFilter ? {} : { band: bandFilter as ReadingReader["band"] }),
    ...(tierFilter === allFilter ? {} : { tier: tierFilter }),
  }), [bandFilter, tierFilter]);
  const suppliedTextReaders = useMemo(() => getReadingReaders({
    mode: "SUPPLIED_TEXT",
    ...(bandFilter === allFilter ? {} : { band: bandFilter as ReadingReader["band"] }),
    ...(tierFilter === allFilter ? {} : { tier: tierFilter }),
  }), [bandFilter, tierFilter]);

  function toggleBookmark(readerId: string) {
    if (!ready) return;
    const next = toggleReadingBookmark(progress, readerId, new Date().toISOString());
    setProgress(next);
    saveReadingProgress(next);
  }

  function addSense(senseId: string) {
    if (!vocabularyProgress) return;
    const next = startWordSense(vocabularyProgress, senseId, new Date().toISOString());
    setVocabularyProgress(next);
    saveVocabularyProgress(next);
  }

  const bookmarkCount = Object.keys(progress.bookmarks).length;
  return (
    <div className="content-stack reading-workspace" lang="en">
      <section className="catalog-hero reading-hero">
        <div>
          <p className="eyebrow">English supplied reading inventory</p>
          <h1>Reading</h1>
          <p className="lede">Read current lesson passages, answer only supplied objective questions, and add only explicitly mapped WordSenses to local vocabulary.</p>
        </div>
        <dl className="vocabulary-summary" aria-label="Reading availability summary">
          <div><dt>Objective passages</dt><dd>112</dd></div>
          <div><dt>Supplied texts</dt><dd>100</dd></div>
          <div><dt>Bookmarks</dt><dd>{ready ? bookmarkCount : "—"}</dd></div>
          <div><dt>Content state</dt><dd>Unreviewed</dd></div>
        </dl>
      </section>

      <section className="page-section reading-boundary" aria-labelledby="reading-boundary-heading">
        <h2 id="reading-boundary-heading">Current availability</h2>
        <p>Graded reading contains short supplied A1–B1 passages with their supplied answer data. C1–C2 texts have no supplied question. B2, source-authored intensive-reading activities, and an extensive-reading collection are not available. No source-authored main-idea, detail, or inference labels are supplied; vocabulary-in-context is available only for the explicitly mapped WordSenses.</p>
        <p>Answers and bookmarks stay local. They do not update lesson completion, Review, grammar, Mistake/Weakness, or a reading/proficiency score.</p>
      </section>

      <section className="page-section reading-filter-section" aria-label="Filter supplied reading">
        <div className="filter-row">
          <label>Band<select value={bandFilter} onChange={(event) => { setBandFilter(event.target.value); setTierFilter(allFilter); }}><option value={allFilter}>Available bands</option>{bands.map((band) => <option key={band} value={band}>{band}</option>)}</select></label>
          <label>Tier<select value={tierFilter} onChange={(event) => setTierFilter(event.target.value)}><option value={allFilter}>Available tiers</option>{tiers.map((tier) => <option key={tier} value={tier}>{tier}</option>)}</select></label>
        </div>
      </section>

      <ReadingGroup
        title="Graded reading"
        description="Supplied objective practice. A correct result only means the response matches supplied answer data."
        readers={objectiveReaders}
        progress={progress}
        vocabularyProgress={vocabularyProgress}
        onToggleBookmark={toggleBookmark}
        onAddSense={addSense}
      />
      <ReadingGroup
        title="Close reading texts"
        description="Supplied C1–C2 text only. No comprehension question, summary, or task has been added."
        readers={suppliedTextReaders}
        progress={progress}
        vocabularyProgress={vocabularyProgress}
        onToggleBookmark={toggleBookmark}
        onAddSense={addSense}
      />
      <section className="page-section reading-unavailable" aria-labelledby="extensive-reading-heading">
        <h2 id="extensive-reading-heading">Extensive reading unavailable</h2>
        <p>No supplied sustained reader collection, reader-choice library, or volume-tracking content is available in this inventory.</p>
      </section>
    </div>
  );
}

function ReadingGroup({
  title,
  description,
  readers,
  progress,
  vocabularyProgress,
  onToggleBookmark,
  onAddSense,
}: {
  readonly title: string;
  readonly description: string;
  readonly readers: readonly ReadingReader[];
  readonly progress: ReadingProgress;
  readonly vocabularyProgress?: VocabularyProgress;
  readonly onToggleBookmark: (readerId: string) => void;
  readonly onAddSense: (senseId: string) => void;
}) {
  return (
    <section className="page-section reading-reader-list" aria-labelledby={`${title.toLowerCase().replaceAll(" ", "-")}-heading`}>
      <div className="section-heading"><div><p className="eyebrow">{readers.length} supplied records</p><h2 id={`${title.toLowerCase().replaceAll(" ", "-")}-heading`}>{title}</h2></div><p>{description}</p></div>
      {readers.length ? <ol>{readers.map((reader) => <ReadingCard key={reader.id} reader={reader} bookmarked={Boolean(progress.bookmarks[reader.id])} vocabularyProgress={vocabularyProgress} onToggleBookmark={onToggleBookmark} onAddSense={onAddSense} />)}</ol> : <p className="empty-state">No supplied reading records match this filter.</p>}
    </section>
  );
}

function ReadingCard({
  reader,
  bookmarked,
  vocabularyProgress,
  onToggleBookmark,
  onAddSense,
}: {
  readonly reader: ReadingReader;
  readonly bookmarked: boolean;
  readonly vocabularyProgress?: VocabularyProgress;
  readonly onToggleBookmark: (readerId: string) => void;
  readonly onAddSense: (senseId: string) => void;
}) {
  const [answer, setAnswer] = useState("");
  const [checked, setChecked] = useState<boolean | undefined>();
  const activeTrigger = useRef<HTMLButtonElement>(null);
  const [selectedSenseId, setSelectedSenseId] = useState<string>();
  const question = reader.questions?.[0];
  const selectedSense = selectedSenseId ? getVocabularySense(selectedSenseId) : undefined;

  return (
    <li className="reading-reader-card">
      <div className="section-heading">
        <div><p className="eyebrow">{reader.band} · {reader.tier} · {reader.topic}</p><h3>{reader.title}</h3></div>
        <button className="secondary-button" type="button" aria-pressed={bookmarked} onClick={() => onToggleBookmark(reader.id)}>{bookmarked ? "Remove bookmark" : "Bookmark locally"}</button>
      </div>
      <ReadingText reader={reader} onSelectSense={(senseId, trigger) => { activeTrigger.current = trigger; setSelectedSenseId(senseId); }} />
      {question ? <div className="reading-question">
        <label>{question.prompt}<input value={answer} onChange={(event) => { setAnswer(event.target.value); setChecked(undefined); }} /></label>
        <button className="secondary-button" type="button" disabled={!answer.trim()} onClick={() => setChecked(matchesAnyAnswer(answer, question.acceptedAnswers))}>Check supplied answer</button>
        {checked !== undefined && <p className={checked ? "feedback-correct" : "feedback-incorrect"} role="status">{checked ? "Correct — your response matches the supplied answer data." : "Not yet — review the supplied passage and try again."}</p>}
      </div> : <p className="local-marker">Supplied text; no question supplied.</p>}
      {selectedSense && <ReadingWordSenseDetail
        sense={selectedSense}
        added={Boolean(vocabularyProgress?.senses[selectedSense.id])}
        onAdd={() => onAddSense(selectedSense.id)}
        onClose={() => { setSelectedSenseId(undefined); activeTrigger.current?.focus(); }}
      />}
    </li>
  );
}

function ReadingText({ reader, onSelectSense }: { readonly reader: ReadingReader; readonly onSelectSense: (senseId: string, trigger: HTMLButtonElement) => void }) {
  const ranges = reader.wordSenseRanges ?? [];
  const pieces: ReactNode[] = [];
  let cursor = 0;
  for (const range of ranges) {
    if (cursor < range.start) pieces.push(reader.sourceText.slice(cursor, range.start));
    pieces.push(<button className="reading-word" type="button" key={`${range.start}-${range.end}`} onClick={(event) => onSelectSense(range.senseId, event.currentTarget)}>{reader.sourceText.slice(range.start, range.end)}</button>);
    cursor = range.end;
  }
  if (cursor < reader.sourceText.length) pieces.push(reader.sourceText.slice(cursor));
  return <p className="reading-passage">{pieces}</p>;
}
