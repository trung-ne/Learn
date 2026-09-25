"use client";

import { useEffect, useState } from "react";
import type { LanguageCode } from "@/content/types";
import { emptyProgress, loadProgress, resetProgress, type LanguageProgress } from "@/lib/progress";

export function CatalogProgress({ language, languageName }: { readonly language: LanguageCode; readonly languageName: string }) {
  const [progress, setProgress] = useState<LanguageProgress>(() => emptyProgress(language));
  const [ready, setReady] = useState(false);

  useEffect(() => {
    setProgress(loadProgress(language));
    setReady(true);
  }, [language]);

  const completed = Object.values(progress.lessons).filter((lesson) => lesson.completed).length;

  function reset() {
    if (!window.confirm(`Reset only ${languageName} local progress?`)) return;
    resetProgress(language);
    setProgress(emptyProgress(language));
  }

  return (
    <aside className="progress-summary" aria-live="polite">
      <div><strong>{ready ? completed : "–"}</strong><span> lessons locally complete</span></div>
      <button type="button" className="text-button" disabled={!ready || Object.keys(progress.lessons).length === 0} onClick={reset}>Reset this language</button>
    </aside>
  );
}
