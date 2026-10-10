"use client";

import { useEffect } from "react";
import { recordLocalDiagnostic } from "@/lib/local-diagnostics";

export default function GlobalError({ reset }: Readonly<{ reset: () => void }>) {
  useEffect(() => {
    recordLocalDiagnostic({ category: "render", occurredAt: new Date().toISOString(), buildId: "static", pathname: window.location.pathname });
  }, []);

  return <html lang="en"><body><main className="page-shell empty-page"><p className="eyebrow">Local recovery</p><h1>English Master needs to restart this page.</h1><p>No diagnostic details or local learning data were sent anywhere.</p><button type="button" onClick={reset}>Try again</button></main></body></html>;
}
