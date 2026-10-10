"use client";

import { useEffect, useState } from "react";
import { LOCAL_STATE_EVENT, localStateStatus, type LocalStateStatus } from "@/lib/local-state";

function messageFor(status: LocalStateStatus): string | undefined {
  if (status.available) return undefined;
  if (status.issue === "quota") return "This browser has no room to save more local learning data. Export a backup or clear data before continuing.";
  if (status.issue === "import") return "Your local backup was not restored. Existing learning data was kept where possible.";
  return "This browser could not save local learning data. Changes may disappear after a reload.";
}

export function LocalStateNotice() {
  const [status, setStatus] = useState<LocalStateStatus>(localStateStatus);

  useEffect(() => {
    const onStatus = (event: Event) => setStatus((event as CustomEvent<LocalStateStatus>).detail);
    window.addEventListener(LOCAL_STATE_EVENT, onStatus);
    return () => window.removeEventListener(LOCAL_STATE_EVENT, onStatus);
  }, []);

  const message = messageFor(status);
  if (!message) return null;
  return (
    <aside className="local-state-notice" role="status" aria-live="polite">
      <strong>Local storage needs attention.</strong>
      <span>{message}</span>
      <a href="/data/">Open local data and backup tools</a>
    </aside>
  );
}
