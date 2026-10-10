"use client";

import { useEffect } from "react";
import { recordLocalDiagnostic } from "@/lib/local-diagnostics";

export default function ErrorPage({ reset }: Readonly<{ reset: () => void }>) {
  useEffect(() => {
    recordLocalDiagnostic({ category: "render", occurredAt: new Date().toISOString(), buildId: "static", pathname: window.location.pathname });
  }, []);

  return <main className="page-shell empty-page"><p className="eyebrow">Local recovery</p><h1>This page needs to be reloaded.</h1><p className="lede">English Master did not display this page as expected. No error details or learning data were sent anywhere.</p><button className="primary-button" type="button" onClick={reset}>Try this page again</button></main>;
}
