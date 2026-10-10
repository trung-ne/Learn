export const metadata = {
  title: "Offline",
  description: "English Master offline availability notice.",
};

export default function OfflinePage() {
  return <main className="page-shell empty-page"><p className="eyebrow">Offline</p><h1>This page has not been saved for offline use.</h1><p className="lede">Reconnect once to open it, or save an available review page from its offline controls. Browser-local learning data is never uploaded by this feature.</p><a className="primary-link" href="/learn/">Open the learning catalog</a></main>;
}
