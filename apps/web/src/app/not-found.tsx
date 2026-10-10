import Link from "next/link";

export default function NotFound() {
  return <main className="page-shell empty-page"><p className="eyebrow">Not available</p><h1>This learning page is not in the current static collection.</h1><p className="lede">The app does not invent missing lessons, records, or routes. Return to the available learning catalog.</p><Link className="primary-link" href="/learn/">Open learning catalog</Link></main>;
}
