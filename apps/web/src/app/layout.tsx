import type { Metadata } from "next";
import Link from "next/link";
import { LanguageSwitcher } from "@/components/language-switcher";
import { getAvailableCourses } from "@/content/catalog";
import "./globals.css";

export const metadata: Metadata = {
  title: { default: "English Master", template: "%s · English Master" },
  description: "A local-first learner view of immutable English and German lesson packets.",
};

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="en">
      <body>
        <a className="skip-link" href="#main-content">Skip to content</a>
        <header className="site-header">
          <Link className="brand" href="/">English Master</Link>
          <nav className="header-nav" aria-label="Primary navigation"><Link href="/learn">Learn</Link></nav>
          <LanguageSwitcher courses={getAvailableCourses().map(({ language, level }) => ({ language, level }))} />
          <span className="header-note">Static · local progress · no account</span>
        </header>
        <main id="main-content">{children}</main>
        <footer>
          <p>These local learning materials are presented for self-study. Internal curriculum tiers are not official CEFR levels.</p>
          <p>This interface conveys no review, publication, provider-behavior, or learner-outcome authority.</p>
        </footer>
      </body>
    </html>
  );
}
