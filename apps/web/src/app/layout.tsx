import type { Metadata, Viewport } from "next";
import Link from "next/link";
import { LanguageSwitcher } from "@/components/language-switcher";
import { LocalStateNotice } from "@/components/local-state-notice";
import { PwaManager } from "@/components/pwa-manager";
import { getAvailableCourses } from "@/content/catalog";
import "./globals.css";
import "./production-hardening.css";

export const metadata: Metadata = {
  title: { default: "English Master", template: "%s · English Master" },
  description: "A local-first learner view of immutable English and German lesson packets.",
  manifest: "/manifest.webmanifest",
  icons: { icon: "/icons/english-master.svg" },
};

export const viewport: Viewport = {
  themeColor: "#0f6b61",
  colorScheme: "light",
};

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="en">
      <body>
        <PwaManager />
        <a className="skip-link" href="#main-content">Skip to content</a>
        <LocalStateNotice />
        <header className="site-header">
          <Link className="brand" href="/">English Master</Link>
          <nav className="header-nav" aria-label="Primary navigation">
            <Link href="/learn">Learn</Link>
            <Link href="/learn/en/vocabulary">Vocabulary</Link>
            <Link href="/learn/en/dictionary">Dictionary</Link>
            <Link href="/learn/en/grammar">Grammar</Link>
            <Link href="/learn/en/listening">Listening</Link>
            <Link href="/learn/en/reading">Reading</Link>
            <Link href="/learn/en/writing">Writing</Link>
            <Link href="/learn/en/speaking">Speaking</Link>
            <Link href="/learn/en/pronunciation">Pronunciation</Link>
          </nav>
          <LanguageSwitcher courses={getAvailableCourses().map(({ language, level }) => ({ language, level }))} />
          <span className="header-note">Static · local progress · no account</span>
        </header>
        <main id="main-content">{children}</main>
        <footer>
          <p>These local learning materials are presented for self-study. Internal curriculum tiers are not official CEFR levels.</p>
          <p>This interface conveys no review, publication, provider-behavior, or learner-outcome authority.</p>
          <p><Link href="/data/">Data and offline tools</Link> stay in this browser unless the learner explicitly exports a backup.</p>
        </footer>
      </body>
    </html>
  );
}
