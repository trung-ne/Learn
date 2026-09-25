import Link from "next/link";
import { snapshot } from "@/content/catalog";
import { learnHref } from "@/lib/routes";

export default function HomePage() {
  return (
    <div className="page-shell home-page">
      <section className="hero">
        <p className="eyebrow">Self-study, locally</p>
        <h1>Learn carefully, at your own pace.</h1>
        <p className="lede">
          Browse {snapshot.lessons.length} static lesson packets in English and German. Exercise checks and progress stay in your browser.
        </p>
        <Link className="primary-link" href={learnHref()}>Choose a language</Link>
      </section>

      <section className="expectations" aria-labelledby="expectations-heading">
        <h2 id="expectations-heading">What to expect</h2>
        <div className="expectation-grid">
          <article><h3>Local by design</h3><p>Optional progress and writing drafts use browser storage separated by target language.</p></article>
          <article><h3>Bounded practice</h3><p>Objective items can be checked locally. Speaking and writing remain learner-led and are not AI-scored.</p></article>
          <article><h3>Accurate status</h3><p>All displayed content remains UNREVIEWED development material derived from immutable repository manifests.</p></article>
        </div>
      </section>
    </div>
  );
}
