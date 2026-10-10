"use client";

import Link from "next/link";
import { useEffect, useRef, useState, type RefObject } from "react";
import type { ListeningSession } from "@/content/listening-types";
import { listeningSnapshot, getListeningSessions } from "@/content/listening-catalog";
import { lessonPacketHref } from "@/lib/routes";
import { matchesAnyAnswer } from "@/lib/answers";
import {
  emptyListeningLabProgress,
  loadListeningLabProgress,
  recordListeningLabStage,
  saveListeningLabProgress,
  type ListeningLabProgress,
} from "@/lib/listening-lab-progress";
import { loadLearner } from "@/lib/progress";

function normalizeWords(value: string): readonly string[] {
  return value.toLocaleLowerCase().match(/[\p{L}\p{N}]+/gu) ?? [];
}

function MissedWords({ dictation, transcript }: { readonly dictation: string; readonly transcript: string }) {
  const attempted = new Set(normalizeWords(dictation));
  const words = normalizeWords(transcript);
  return (
    <p className="listening-word-comparison" aria-label="Words from the supplied transcript that were not in your local dictation">
      {words.map((word, index) => <span className={attempted.has(word) ? "matched-word" : "missed-word"} key={`${word}-${index}`}>{word} </span>)}
    </p>
  );
}

function ListeningSessionCard({ session }: { readonly session: ListeningSession }) {
  const audioRef = useRef<HTMLAudioElement | HTMLVideoElement>(null);
  const [meaning, setMeaning] = useState("");
  const [dictation, setDictation] = useState("");
  const [progress, setProgress] = useState<ListeningLabProgress | undefined>();
  const [mediaError, setMediaError] = useState(false);

  useEffect(() => {
    const learner = loadLearner();
    setProgress(loadListeningLabProgress(
      { learnerId: learner.learnerId, language: "en", course: session.band },
      listeningSnapshot.inventoryVersion,
    ));
  }, [session.band]);

  const sessionProgress = progress?.sessions[session.id];
  const completed = sessionProgress?.completedStages ?? [];
  const hasMeaning = completed.includes("meaning_attempted");
  const hasDictation = completed.includes("dictation_attempted");
  const revealed = completed.includes("transcript_revealed");
  const hasShadowed = completed.includes("shadow_marked");
  const finalMarked = completed.includes("final_listen_marked");

  function record(stage: "meaning_attempted" | "dictation_attempted" | "transcript_revealed" | "shadow_marked" | "final_listen_marked") {
    if (!progress) return;
    const next = recordListeningLabStage(progress, session.id, stage, new Date().toISOString());
    setProgress(next);
    saveListeningLabProgress(next);
  }

  function seekSentence(startSeconds: number, endSeconds: number) {
    const media = audioRef.current;
    if (!media) return;
    media.currentTime = startSeconds;
    void media.play().catch(() => {});
    window.setTimeout(() => { if (media.currentTime >= startSeconds) media.pause(); }, Math.ceil((endSeconds - startSeconds) * 1000));
  }

  const media = session.mediaKind === "video" ? (
    <video ref={audioRef as RefObject<HTMLVideoElement>} controls preload="metadata" onError={() => setMediaError(true)}>
      <source src={session.assetPath} type={session.mimeType} />
      Your browser cannot play this supplied media.
    </video>
  ) : (
    <audio ref={audioRef as RefObject<HTMLAudioElement>} controls preload="metadata" onError={() => setMediaError(true)}>
      <source src={session.assetPath} type={session.mimeType} />
      Your browser cannot play this supplied media.
    </audio>
  );

  return (
    <article className="listening-session-card" aria-labelledby={`${session.id}-title`}>
      <div className="section-heading">
        <div><p className="eyebrow">Supplied session · lesson target {session.band}</p><h2 id={`${session.id}-title`}>{session.title}</h2></div>
        <Link href={lessonPacketHref("en", session.band, session.unitId, session.lessonId)}>Open supplied lesson</Link>
      </div>
      <dl className="listening-metadata">
        <div><dt>Topic</dt><dd>{session.topic}</dd></div><div><dt>Accent label</dt><dd>{session.accent}</dd></div>
        <div><dt>Speakers</dt><dd>{session.speakerLabels.join(", ")}</dd></div><div><dt>Supplied pace</dt><dd>{session.speed}</dd></div>
        <div><dt>Grammar labels</dt><dd>{session.grammar.join(", ")}</dd></div><div><dt>Vocabulary labels</dt><dd>{session.vocabulary.join(", ")}</dd></div>
        <div><dt>Phonetic features</dt><dd>{session.phoneticFeatures.join(", ")}</dd></div>
      </dl>
      <ol className="listening-steps">
        <li><strong>Listen without transcript.</strong>{media}{mediaError && <p role="status">The supplied local media could not be played in this browser.</p>}</li>
        <li><label><strong>Answer the supplied meaning question.</strong><span>{session.meaningPrompt}</span><input value={meaning} onChange={(event) => setMeaning(event.target.value)} /></label><button type="button" disabled={!meaning.trim() || hasMeaning} onClick={() => record("meaning_attempted")}>Check meaning attempt</button>{hasMeaning && <p role="status">{matchesAnyAnswer(meaning, session.acceptedMeaningAnswers) ? "Your response matches supplied answer data." : "Your response does not match supplied answer data."}</p>}</li>
        <li><strong>Listen again.</strong><span> Use the supplied local player above.</span></li>
        <li><label><strong>Dictation.</strong><span>{session.dictationPrompt}</span><textarea value={dictation} onChange={(event) => setDictation(event.target.value)} /></label><button type="button" disabled={!hasMeaning || !dictation.trim() || hasDictation} onClick={() => record("dictation_attempted")}>Save local dictation attempt</button></li>
        <li><strong>Reveal transcript.</strong><button type="button" disabled={!hasDictation || revealed} aria-expanded={revealed} onClick={() => record("transcript_revealed")}>Reveal supplied transcript</button>{revealed && <div className="transcript" role="status"><p>{session.transcript}</p><MissedWords dictation={dictation} transcript={session.transcript} /></div>}</li>
        <li><strong>Listen by sentence.</strong>{revealed && <div className="sentence-controls">{session.sentences.map((sentence) => <button type="button" key={sentence.id} onClick={() => seekSentence(sentence.startSeconds, sentence.endSeconds)}>{sentence.speaker}: {sentence.text}</button>)}</div>}</li>
        <li><strong>Shadow.</strong><button type="button" disabled={!revealed || hasShadowed} onClick={() => record("shadow_marked")}>Mark self-practice locally</button></li>
        <li><strong>Final listen.</strong><button type="button" disabled={!hasShadowed || finalMarked} onClick={() => record("final_listen_marked")}>Mark final listen locally</button>{finalMarked && <p role="status">Marked locally. This is not a listening assessment, proficiency result, or completion claim.</p>}</li>
      </ol>
    </article>
  );
}

export function ListeningLabWorkspace() {
  const sessions = getListeningSessions("en");
  if (!sessions.length) {
    return <section className="listening-lab-empty" aria-labelledby="listening-lab-heading"><p className="eyebrow">Authorized-media boundary</p><h1 id="listening-lab-heading">Listening Lab</h1><p>No authorized browser-playable listening session is currently supplied.</p><p>The lesson pages retain separate transcript-only practice. Transcript-only practice cannot complete the audio-first Listening Lab sequence.</p></section>;
  }
  return <section className="listening-lab-workspace" aria-label="Listening Lab sessions">{sessions.map((session) => <ListeningSessionCard key={session.id} session={session} />)}</section>;
}
