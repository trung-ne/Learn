import Link from "next/link";
import { getLanguages } from "@/content/catalog";
import { getLanguageConfiguration } from "@/content/languages";
import { languageHref } from "@/lib/routes";

export default function LearnPage() {
  return (
    <div className="page-shell home-page">
      <section className="hero">
        <p className="eyebrow">Choose a target language</p>
        <h1>What would you like to learn?</h1>
        <p className="lede">Available lessons are local static material. Choose a language to see its current course levels.</p>
      </section>

      <section className="language-grid" aria-label="Available target languages">
        {getLanguages().map((language) => {
          const configuration = getLanguageConfiguration(language.code);
          if (!configuration) return null;
          return (
            <Link className="language-card" href={languageHref(language.code)} key={language.code}>
              <span className="language-code" aria-hidden="true">{language.code.toUpperCase()}</span>
              <div>
                <h2>{configuration.name}</h2>
                <p>{configuration.nativeName} · {language.lessonCount} lessons · {configuration.availableLevels.join("–")}</p>
              </div>
              <span aria-hidden="true">→</span>
            </Link>
          );
        })}
      </section>
    </div>
  );
}
