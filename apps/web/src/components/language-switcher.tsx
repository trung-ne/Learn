"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useEffect, useState } from "react";
import { languages, type LanguageCode } from "@/content/languages";
import type { CourseSummary } from "@/content/catalog";
import { loadLearner, setActiveLanguage } from "@/lib/progress";
import { switchDestination } from "@/lib/language-switching";

interface LanguageSwitcherProps {
  readonly courses: readonly Pick<CourseSummary, "language" | "level">[];
}

function languageInPath(pathname: string): LanguageCode | undefined {
  const match = pathname.match(/^\/learn\/(en|de)(?:\/|$)/u);
  return match?.[1] as LanguageCode | undefined;
}

export function LanguageSwitcher({ courses }: LanguageSwitcherProps) {
  const pathname = usePathname() ?? "/";
  const routedLanguage = languageInPath(pathname);
  const [preferredLanguage, setPreferredLanguage] = useState<LanguageCode>();
  const activeLanguage = routedLanguage ?? preferredLanguage;

  useEffect(() => {
    setPreferredLanguage(loadLearner().activeLanguage);
  }, []);

  function selectLanguage(language: LanguageCode) {
    const learner = loadLearner();
    setActiveLanguage(learner, language);
    setPreferredLanguage(language);
  }

  return (
    <nav className="language-switcher" aria-label="Learning language">
      {Object.values(languages).map((language) => {
        const active = activeLanguage === language.code;
        return (
          <Link
            aria-current={active ? "page" : undefined}
            href={switchDestination(pathname, language.code, courses)}
            key={language.code}
            onClick={() => selectLanguage(language.code)}
          >
            <span>{language.name}</span><span className="switcher-native">{language.nativeName}</span>
          </Link>
        );
      })}
    </nav>
  );
}
