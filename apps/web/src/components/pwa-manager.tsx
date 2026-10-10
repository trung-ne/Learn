"use client";

import { useEffect, useState } from "react";
import { recordLocalDiagnostic } from "@/lib/local-diagnostics";

type PwaState = "unsupported" | "registering" | "ready" | "update" | "failed";

function secureContextForWorker(): boolean {
  return window.isSecureContext || window.location.hostname === "localhost" || window.location.hostname === "127.0.0.1";
}

export function PwaManager() {
  const [state, setState] = useState<PwaState>("registering");

  useEffect(() => {
    if (!("serviceWorker" in navigator) || !secureContextForWorker()) {
      setState("unsupported");
      return;
    }
    let registration: ServiceWorkerRegistration | undefined;
    const checkUpdate = () => {
      if (registration?.waiting) setState("update");
    };
    navigator.serviceWorker.register("/sw.js", { scope: "/" }).then((value) => {
      registration = value;
      setState("ready");
      value.addEventListener("updatefound", () => value.installing?.addEventListener("statechange", checkUpdate));
      checkUpdate();
    }).catch(() => {
      recordLocalDiagnostic({ category: "service_worker", occurredAt: new Date().toISOString(), buildId: "static", pathname: window.location.pathname });
      setState("failed");
    });
    return () => undefined;
  }, []);

  function activateUpdate() {
    navigator.serviceWorker.getRegistration().then((registration) => registration?.waiting?.postMessage({ type: "skip-waiting" }));
    navigator.serviceWorker.addEventListener("controllerchange", () => window.location.reload(), { once: true });
  }

  if (state === "update") {
    return <aside className="pwa-update" role="status" aria-live="polite"><span>An offline update is ready.</span><button className="secondary-button" type="button" onClick={activateUpdate}>Update and reload</button></aside>;
  }
  if (state === "failed") {
    return <aside className="pwa-update" role="status">Offline support could not start in this browser. Local learning data remains in this browser only.</aside>;
  }
  return null;
}

export function OfflineReviewControl() {
  const [available, setAvailable] = useState(false);
  const [status, setStatus] = useState<string>();

  useEffect(() => {
    if (!("serviceWorker" in navigator)) return;
    navigator.serviceWorker.ready.then(async () => {
      const cacheNames = await caches.keys();
      const current = cacheNames.find((name) => name.startsWith("english-master-static-"));
      if (current) setAvailable(await (await caches.open(current)).match(window.location.pathname.endsWith("/") ? window.location.pathname : `${window.location.pathname}/`) !== undefined);
    }).catch(() => undefined);
  }, []);

  async function changeCache(action: "cache-route" | "remove-route") {
    const controller = navigator.serviceWorker.controller;
    if (!controller) {
      setStatus("Offline review support is not ready yet. Reload on a secure connection and try again.");
      return;
    }
    const path = window.location.pathname.endsWith("/") ? window.location.pathname : `${window.location.pathname}/`;
    const channel = new MessageChannel();
    const result = new Promise<boolean>((resolve) => {
      const timeout = window.setTimeout(() => resolve(false), 5_000);
      channel.port1.onmessage = (event: MessageEvent<{ ok?: boolean; cached?: boolean }>) => {
        window.clearTimeout(timeout);
        resolve(event.data?.ok === true && event.data.cached === (action === "cache-route"));
      };
    });
    controller.postMessage({ type: action, path }, [channel.port2]);
    if (await result) {
      setAvailable(action === "cache-route");
      setStatus(action === "cache-route" ? "This review page is available for offline use on this browser." : "The offline copy of this review page was removed.");
      return;
    }
    recordLocalDiagnostic({ category: "offline", occurredAt: new Date().toISOString(), buildId: "static", pathname: window.location.pathname });
    setStatus("The offline review change could not be completed. Try again while connected.");
  }

  return <section className="offline-review-control" aria-labelledby="offline-review-heading">
    <h2 id="offline-review-heading">Offline review</h2>
    <p>{available ? "This review page is available from the current offline cache." : "Save this current review page for offline use on this browser."}</p>
    <button className="secondary-button" type="button" onClick={() => changeCache(available ? "remove-route" : "cache-route")}>{available ? "Remove offline copy" : "Make this review available offline"}</button>
    {status && <p role="status">{status}</p>}
  </section>;
}
