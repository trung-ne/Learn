import Link from "next/link";
import { getAssessmentPackages, getLevelTest, getPlacementPackage } from "@/content/assessment-catalog";
import { assessmentPackageHref } from "@/lib/routes";
import { AssessmentDashboard } from "./assessment-dashboard";

const levels = ["A1", "A2", "B1", "B2", "C1", "C2"] as const;

export function AssessmentHub() {
  const packages = getAssessmentPackages();
  const placement = getPlacementPackage();
  const lessonQuizzes = packages.filter((item) => item.type === "LESSON_QUIZ");
  const unitTests = packages.filter((item) => item.type === "UNIT_TEST");

  return (
    <div className="content-stack assessment-hub">
      <section className="catalog-hero">
        <div>
          <p className="eyebrow">English-only local assessment</p>
          <h1>Assessment</h1>
          <p className="lede">Use the existing supplied objective packages for local practice evidence. These results are not certification, a proficiency decision, or course unlocks.</p>
        </div>
      </section>
      <section className="assessment-boundary" aria-label="Assessment availability">
        <p>All displayed assessment content is UNREVIEWED. The browser scores only supplied no-media objective answers and saves results in this browser.</p>
        <p>German has no language-scoped assessment package yet, so no German score or placement result is shown.</p>
      </section>
      <section className="assessment-hierarchy" aria-labelledby="assessment-hierarchy-heading">
        <p className="eyebrow">Assessment hierarchy</p>
        <h2 id="assessment-hierarchy-heading">Available evidence stages</h2>
        <ol>
          <li><Link href={assessmentPackageHref(placement.id)}>Placement</Link><span>Available: 24 supplied objective items; yields a fixed local starting-point suggestion only.</span></li>
          <li><strong>Lesson quiz</strong><span>Available: {lessonQuizzes.length} lesson-bound objective packages, linked from each English lesson.</span></li>
          <li><strong>Unit checkpoint</strong><span>Available: {unitTests.length} supplied ten-item unit tests, linked from English level catalogs.</span></li>
          <li><strong>Skill checkpoint</strong><span>Unavailable: no immutable package can validly assess all requested skills.</span></li>
          <li><strong>CEFR level test</strong><span>Available: supplied band-level tests; they do not certify CEFR attainment.</span></li>
          <li><strong>Comprehensive assessment</strong><span>Unavailable: current data cannot assess speaking, writing, pronunciation, and audio listening.</span></li>
        </ol>
      </section>
      <section className="assessment-level-tests" aria-labelledby="assessment-level-tests-heading">
        <p className="eyebrow">Level tests</p>
        <h2 id="assessment-level-tests-heading">Supplied English band tests</h2>
        <ul className="assessment-link-list">
          {levels.map((level) => {
            const test = getLevelTest(level);
            return test ? <li key={level}><Link href={assessmentPackageHref(test.id)}>{level} level test</Link><span>{test.items.length} objective items · not CEFR certification</span></li> : null;
          })}
        </ul>
      </section>
      <AssessmentDashboard />
    </div>
  );
}
