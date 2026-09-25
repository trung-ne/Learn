"use client";

import { useState } from "react";
import type { PracticeProtocol } from "@/content/types";

export type Modality = "listening" | "speaking" | "pronunciation" | "writing";

interface PracticePanelsProps {
  readonly practice: Readonly<Record<Modality, PracticeProtocol>>;
  readonly completed: Readonly<Partial<Record<Modality, boolean>>>;
  readonly writingDraft: string;
  readonly onProtocolComplete: (modality: Modality, completed: boolean) => void;
  readonly onDraftChange: (draft: string) => void;
}

const labels: Record<Modality, string> = {
  listening: "Listening without audio",
  speaking: "Speaking self-practice",
  pronunciation: "Pronunciation self-practice",
  writing: "Writing draft",
};

export function PracticePanels({ practice, completed, writingDraft, onProtocolComplete, onDraftChange }: PracticePanelsProps) {
  return (
    <div className="practice-grid">
      <ListeningPanel protocol={practice.listening} completed={Boolean(completed.listening)} onComplete={(value) => onProtocolComplete("listening", value)} />
      <StaticPanel modality="speaking" protocol={practice.speaking} completed={Boolean(completed.speaking)} onComplete={(value) => onProtocolComplete("speaking", value)} />
      <StaticPanel modality="pronunciation" protocol={practice.pronunciation} completed={Boolean(completed.pronunciation)} onComplete={(value) => onProtocolComplete("pronunciation", value)} />
      <WritingPanel protocol={practice.writing} completed={Boolean(completed.writing)} draft={writingDraft} onDraftChange={onDraftChange} onComplete={(value) => onProtocolComplete("writing", value)} />
    </div>
  );
}

function ProtocolDetails({ protocol }: { readonly protocol: PracticeProtocol }) {
  const checks = protocol.constraints ?? protocol.checklist ?? [];
  return (
    <>
      {protocol.goal && <p><strong>Goal:</strong> {protocol.goal}</p>}
      <p>{protocol.instruction}</p>
      {checks.length > 0 && <ul>{checks.map((item) => <li key={item}>{item}</li>)}</ul>}
    </>
  );
}

function CompletionToggle({ checked, onChange }: { readonly checked: boolean; readonly onChange: (value: boolean) => void }) {
  return (
    <label className="completion-toggle">
      <input type="checkbox" checked={checked} onChange={(event) => onChange(event.target.checked)} />
      <span>Mark this self-practice protocol complete locally</span>
    </label>
  );
}

function ListeningPanel({ protocol, completed, onComplete }: { readonly protocol: PracticeProtocol; readonly completed: boolean; readonly onComplete: (value: boolean) => void }) {
  const [attempt, setAttempt] = useState("");
  const [revealed, setRevealed] = useState(false);
  return (
    <section className="practice-card" aria-labelledby="practice-listening">
      <h3 id="practice-listening">{labels.listening}</h3>
      <p className="boundary-note">Transcript-only practice. No audio is supplied or simulated.</p>
      <ProtocolDetails protocol={protocol} />
      {protocol.question && (
        <label><span>{protocol.question}</span><input value={attempt} onChange={(event) => setAttempt(event.target.value)} /></label>
      )}
      {protocol.transcript && (
        <>
          <button type="button" disabled={!attempt.trim()} onClick={() => setRevealed(true)}>Reveal transcript after attempting</button>
          {revealed && <div className="transcript"><strong>Transcript</strong><p>{protocol.transcript}</p>{protocol.answer && <p><strong>Supplied answer:</strong> {protocol.answer}</p>}</div>}
        </>
      )}
      <CompletionToggle checked={completed} onChange={onComplete} />
    </section>
  );
}

function StaticPanel({ modality, protocol, completed, onComplete }: { readonly modality: "speaking" | "pronunciation"; readonly protocol: PracticeProtocol; readonly completed: boolean; readonly onComplete: (value: boolean) => void }) {
  const isPronunciation = modality === "pronunciation";
  return (
    <section className="practice-card" aria-labelledby={`practice-${modality}`}>
      <h3 id={`practice-${modality}`}>{labels[modality]}</h3>
      <p className="boundary-note">
        {isPronunciation
          ? "No audio is collected or scored. Assessment remains NOT_ASSESSED."
          : "No chat simulation or generated feedback is provided."}
      </p>
      <ProtocolDetails protocol={protocol} />
      {protocol.target && <p><strong>Target:</strong> {protocol.target}</p>}
      {isPronunciation && <p className="status-pill">{protocol.without_audio ?? protocol.assessment ?? "NOT_ASSESSED"}</p>}
      <CompletionToggle checked={completed} onChange={onComplete} />
    </section>
  );
}

function WritingPanel({ protocol, completed, draft, onDraftChange, onComplete }: { readonly protocol: PracticeProtocol; readonly completed: boolean; readonly draft: string; readonly onDraftChange: (value: string) => void; readonly onComplete: (value: boolean) => void }) {
  return (
    <section className="practice-card" aria-labelledby="practice-writing">
      <h3 id="practice-writing">{labels.writing}</h3>
      <p className="boundary-note">Drafts stay in this browser. No feedback or replacement text is generated.</p>
      <ProtocolDetails protocol={protocol} />
      <label><span>Your local draft</span><textarea rows={7} value={draft} onChange={(event) => onDraftChange(event.target.value)} /></label>
      <CompletionToggle checked={completed} onChange={onComplete} />
    </section>
  );
}
