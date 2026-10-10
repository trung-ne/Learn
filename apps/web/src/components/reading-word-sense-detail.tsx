import { useEffect, useRef } from "react";
import type { VocabularySense } from "@/content/vocabulary-types";

export function ReadingWordSenseDetail({
  sense,
  added,
  onAdd,
  onClose,
}: {
  readonly sense: VocabularySense;
  readonly added: boolean;
  readonly onAdd: () => void;
  readonly onClose: () => void;
}) {
  const headingRef = useRef<HTMLHeadingElement>(null);

  useEffect(() => { headingRef.current?.focus(); }, [sense.id]);

  return (
    <aside className="reading-word-sense-detail" aria-labelledby={`reading-sense-${sense.id}`} onKeyDown={(event) => { if (event.key === "Escape") onClose(); }}>
      <div className="section-heading">
        <div><p className="eyebrow">Exact supplied WordSense</p><h4 id={`reading-sense-${sense.id}`} ref={headingRef} tabIndex={-1}>{sense.lemma} <span className="ipa">{sense.ipa}</span></h4></div>
        <button className="text-button" type="button" onClick={onClose}>Close</button>
      </div>
      <p><strong>Part of speech:</strong> {sense.partOfSpeech}</p>
      {sense.vietnameseMeaning && <p><strong>Vietnamese meaning:</strong> {sense.vietnameseMeaning}</p>}
      <p><strong>Definition:</strong> {sense.definition}</p>
      <p><strong>Example:</strong> {sense.examples[0]}</p>
      <button className="secondary-button" type="button" disabled={added} onClick={onAdd}>{added ? "Added to vocabulary locally" : "Add to vocabulary"}</button>
    </aside>
  );
}
