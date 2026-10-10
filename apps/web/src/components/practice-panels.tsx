"use client";

import Link from "next/link";
import { useState } from "react";
import type { LessonPractice, PracticeProtocol, LanguageCode } from "@/content/types";
import { pronunciationHref, speakingHref, writingHref } from "@/lib/routes";

export type Modality = "listening" | "speaking" | "pronunciation" | "writing";

interface PracticePanelsProps {
  readonly practice: LessonPractice;
  readonly language?: LanguageCode;
  readonly targetLevel?: string;
  readonly completed: Readonly<Partial<Record<Modality, boolean>>>;
  /** Retained for callers with an unimported legacy local draft; the dedicated Writing workspace owns editing. */
  readonly writingDraft?: string;
  /** Retained for compatibility; dedicated Writing workspace owns editing. */
  readonly onDraftChange?: (draft: string) => void;
  readonly onProtocolComplete: (modality: Modality, completed: boolean) => void;
}

const labels: Record<Modality, string> = {
  listening: "Listening",
  speaking: "Speaking",
  pronunciation: "Pronunciation",
  writing: "Writing",
};

export function PracticePanels({
  practice,
  language = "en",
  targetLevel,
  completed,
  onProtocolComplete,
}: PracticePanelsProps) {
  return (
    <div className="practice-grid">
      {practice.listening && (
        <ListeningPanel
          protocol={practice.listening}
          completed={Boolean(completed.listening)}
          onComplete={(value) => onProtocolComplete("listening", value)}
        />
      )}
      {practice.speaking && (
        <SpeakingPanel
          protocol={practice.speaking}
          language={language}
          completed={Boolean(completed.speaking)}
          onComplete={(value) => onProtocolComplete("speaking", value)}
        />
      )}
      {practice.pronunciation && (
        <PronunciationPanel
          protocol={practice.pronunciation}
          language={language}
          completed={Boolean(completed.pronunciation)}
          onComplete={(value) => onProtocolComplete("pronunciation", value)}
        />
      )}
      {practice.writing && (
        <WritingPanel
          protocol={practice.writing}
          language={language}
          targetLevel={targetLevel}
          completed={Boolean(completed.writing)}
          onComplete={(value) => onProtocolComplete("writing", value)}
        />
      )}
    </div>
  );
}

function PromptTools({
  protocol,
  label = "Lesson-specific prompt",
}: {
  readonly protocol: PracticeProtocol;
  readonly label?: string;
}) {
  return (
    <>
      <div className="stored-prompt">
        <strong>{label}</strong>
        <p>{protocol.instruction}</p>
      </div>
      <CopyPrompt prompt={protocol.instruction} />
      <p className="boundary-note">Use this stored prompt in your preferred AI or voice-AI tool.</p>
    </>
  );
}

function ProtocolGuidance({ protocol }: { readonly protocol: PracticeProtocol }) {
  const checks = protocol.constraints ?? protocol.checklist ?? [];
  return (
    <>
      {protocol.goal && (
        <p>
          <strong>Goal:</strong> {protocol.goal}
        </p>
      )}
      {checks.length > 0 && <ul>{checks.map((item) => <li key={item}>{item}</li>)}</ul>}
    </>
  );
}

function CopyPrompt({ prompt }: { readonly prompt: string }) {
  const [status, setStatus] = useState<"idle" | "copied" | "failed">("idle");

  async function copyPrompt() {
    try {
      if (!navigator.clipboard) throw new Error("Clipboard access is unavailable");
      await navigator.clipboard.writeText(prompt);
      setStatus("copied");
    } catch {
      setStatus("failed");
    }
  }

  return (
    <div className="copy-prompt-control">
      <button className="secondary-button" type="button" onClick={copyPrompt}>
        Copy prompt
      </button>
      <span aria-live="polite">
        {status === "copied" && "Copied."}
        {status === "failed" && "Copying is unavailable in this browser."}
      </span>
    </div>
  );
}

function CompletionToggle({
  checked,
  onChange,
}: {
  readonly checked: boolean;
  readonly onChange: (value: boolean) => void;
}) {
  return (
    <label className="completion-toggle">
      <input type="checkbox" checked={checked} onChange={(event) => onChange(event.target.checked)} />
      <span>Mark this self-practice protocol complete locally</span>
    </label>
  );
}

function ListeningPanel({
  protocol,
  completed,
  onComplete,
}: {
  readonly protocol: PracticeProtocol;
  readonly completed: boolean;
  readonly onComplete: (value: boolean) => void;
}) {
  const [attempt, setAttempt] = useState("");
  const [revealed, setRevealed] = useState(false);
  return (
    <section className="practice-card" aria-labelledby="practice-listening">
      <h3 id="practice-listening">{labels.listening}</h3>
      <p className="boundary-note">Transcript-only practice. No permitted audio asset is available in this lesson.</p>
      <PromptTools protocol={protocol} />
      <ProtocolGuidance protocol={protocol} />
      {protocol.question && (
        <label>
          <span>{protocol.question}</span>
          <input value={attempt} onChange={(event) => setAttempt(event.target.value)} />
        </label>
      )}
      {protocol.transcript && (
        <>
          <button
            type="button"
            disabled={!attempt.trim()}
            aria-expanded={revealed}
            aria-controls="listening-transcript"
            onClick={() => setRevealed(true)}
          >
            Reveal transcript after attempting
          </button>
          {revealed && (
            <div className="transcript" id="listening-transcript" role="status">
              <strong>Transcript</strong>
              <p>{protocol.transcript}</p>
              {protocol.answer && (
                <p>
                  <strong>Supplied answer:</strong> {protocol.answer}
                </p>
              )}
            </div>
          )}
        </>
      )}
      <CompletionToggle checked={completed} onChange={onComplete} />
    </section>
  );
}

function SpeakingPanel({
  protocol,
  language,
  completed,
  onComplete,
}: {
  readonly protocol: PracticeProtocol;
  readonly language: LanguageCode;
  readonly completed: boolean;
  readonly onComplete: (value: boolean) => void;
}) {
  return (
    <section className="practice-card" aria-labelledby="practice-speaking">
      <h3 id="practice-speaking">{labels.speaking}</h3>
      <p className="boundary-note">Prompt-first self-practice. No recording, chat simulation, or generated feedback is provided.</p>
      <PromptTools protocol={protocol} />
      <SourceText label="Situation" value={protocol.situation} />
      <SourceText label="Your role" value={protocol.learner_role} />
      <SourceText label="AI role" value={protocol.ai_role} />
      <ProtocolGuidance protocol={protocol} />
      <SourceList label="Useful language" values={protocol.useful_language} />
      <Link href={speakingHref(language)}>Browse supplied speaking protocols</Link>
      <CompletionToggle checked={completed} onChange={onComplete} />
    </section>
  );
}

function PronunciationPanel({
  protocol,
  language,
  completed,
  onComplete,
}: {
  readonly protocol: PracticeProtocol;
  readonly language: LanguageCode;
  readonly completed: boolean;
  readonly onComplete: (value: boolean) => void;
}) {
  const assessment = protocol.without_audio ?? protocol.assessment;
  return (
    <section className="practice-card" aria-labelledby="practice-pronunciation">
      <h3 id="practice-pronunciation">{labels.pronunciation}</h3>
      <p className="boundary-note">No audio is collected or scored in this app.</p>
      <PromptTools protocol={protocol} />
      <SourceText label="Target sound or feature" value={protocol.target} />
      <ProtocolGuidance protocol={protocol} />
      <SourceList label="Examples" values={protocol.examples} />
      <SourceText label="Pronunciation explanation" value={protocol.explanation} />
      {assessment && <p className="status-pill">{assessment}</p>}
      <Link href={pronunciationHref(language)}>Browse supplied pronunciation protocols</Link>
      <CompletionToggle checked={completed} onChange={onComplete} />
    </section>
  );
}

function SourceText({ label, value }: { readonly label: string; readonly value?: string }) {
  if (!value) return null;
  return (
    <p>
      <strong>{label}:</strong> {value}
    </p>
  );
}

function SourceList({
  label,
  values,
}: {
  readonly label: string;
  readonly values?: readonly string[];
}) {
  if (!values?.length) return null;
  return (
    <div>
      <strong>{label}</strong>
      <ul>{values.map((value) => <li key={value}>{value}</li>)}</ul>
    </div>
  );
}

function WritingPanel({
  protocol,
  language,
  targetLevel,
  completed,
  onComplete,
}: {
  readonly protocol: PracticeProtocol;
  readonly language: LanguageCode;
  readonly targetLevel?: string;
  readonly completed: boolean;
  readonly onComplete: (value: boolean) => void;
}) {
  return (
    <section className="practice-card" aria-labelledby="practice-writing">
      <h3 id="practice-writing">{labels.writing}</h3>
      <p className="boundary-note">Drafts stay in this browser. No feedback or replacement text is generated.</p>
      <SourceText label="Target level" value={targetLevel} />
      <SourceText label="Task" value={protocol.instruction} />
      <PromptTools protocol={protocol} label="AI writing tutor prompt" />
      <ProtocolGuidance protocol={protocol} />
      <SourceList label="Useful language" values={protocol.useful_language} />
      {language === "en" ? (
        <Link href={writingHref("en")}>Open this task in the dedicated Writing workspace</Link>
      ) : (
        <p className="local-marker">A dedicated writing workspace is not available for this target language.</p>
      )
      <CompletionToggle checked={completed} onChange={onComplete} />
    </section>
  );
}
