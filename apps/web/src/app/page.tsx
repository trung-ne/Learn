import Link from "next/link";
import { HomeLearning, type HomeCourse } from "@/components/home-learning";
import { getAvailableCourses, getLanguages, getLessonsForLanguageLevel, snapshot } from "@/content/catalog";
import { getLanguageConfiguration } from "@/content/languages";
import { languageHref, learnHref, lessonHref } from "@/lib/routes";

function homeCourses(): readonly HomeCourse[] {
  return getAvailableCourses().map((course) => {
    const lessons = getLessonsForLanguageLevel(course.language, course.level);
    return {
      language: course.language,
      level: course.level,
      lessonCount: course.lessonCount,
      availability: course.availability,
      firstLessonHref: lessonHref(course.firstLesson),
      lessons: lessons.map((lesson) => ({ lessonId: lesson.lessonId, unitId: lesson.unitId })),
      lessonHrefs: Object.fromEntries(lessons.map((lesson) => [lesson.lessonId, lessonHref(lesson)])),
    };
  });
}

export default function HomePage() {
  return (
    <div className="page-shell home-page">
      <section className="hero">
        <p className="eyebrow">English Master</p>
        <h1>Learn carefully, at your own pace.</h1>
        <p className="lede">
          A local-first learner view of {snapshot.lessons.length} static English and German lesson packets. Exercise checks and progress remain in this browser.
        </p>
        <Link className="primary-link" href={learnHref()}>Browse all languages</Link>
      </section>

      <section className="language-grid" aria-label="Available target languages">
        {getLanguages().map((language) => {
          const configuration = getLanguageConfiguration(language.code);
          if (!configuration) return null;
          return (
            <Link className="language-card" href={languageHref(language.code)} key={language.code}>
              <span className="language-code" aria-hidden="true">{language.code.toUpperCase()}</span>
              <div><h2>{configuration.name}</h2><p>{configuration.nativeName} · {language.bands.join("–")}</p></div>
              <span aria-hidden="true">→</span>
            </Link>
          );
        })}
      </section>

      <HomeLearning courses={homeCourses()} />
    </div>
  );
}
