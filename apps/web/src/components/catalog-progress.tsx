"use client";

import { useEffect, useState } from "react";
import type { CourseLevel, LanguageCode } from "@/content/types";
import {
  emptyProgress,
  loadLearner,
  loadProgress,
  resetProgress,
  summarizeCourseProgress,
  type CourseLessonInventory,
  type CourseProgress,
} from "@/lib/progress";

interface CatalogProgressProps {
  readonly language: LanguageCode;
  readonly course: CourseLevel;
  readonly languageName: string;
  readonly lessons: readonly CourseLessonInventory[];
}

function unitLabel(unitId: string): string {
  const match = unitId.match(/-u(\d+)$/iu);
  return match ? `Unit ${Number(match[1])}` : unitId;
}

export function CatalogProgress({ language, course, languageName, lessons }: CatalogProgressProps) {
  const [progress, setProgress] = useState<CourseProgress>(() =>
    emptyProgress({ learnerId: "local-unavailable", language, course }),
  );
  const [ready, setReady] = useState(false);

  useEffect(() => {
    setReady(false);
    const learner = loadLearner();
    setProgress(loadProgress({ learnerId: learner.learnerId, language, course }));
    setReady(true);
  }, [course, language]);

  const summary = summarizeCourseProgress(progress, lessons);

  function reset() {
    if (!window.confirm(`Reset only ${languageName} ${course} local progress?`)) return;
    resetProgress(progress);
    setProgress(emptyProgress(progress));
  }

  return (
    <aside className="progress-summary" aria-live="polite">
      <div><strong>{ready ? summary.completedLessons : "–"} / {summary.totalLessons}</strong><span> lessons locally complete</span></div>
      {ready && summary.units.length > 0 && (
        <ul className="unit-progress-list" aria-label="Unit progress">
          {summary.units.map((unit) => (
            <li key={unit.unitId}>{unitLabel(unit.unitId)}: {unit.completedLessons} / {unit.totalLessons}</li>
          ))}
        </ul>
      )}
      <button type="button" className="text-button" disabled={!ready || Object.keys(progress.lessons).length === 0} onClick={reset}>Reset this course</button>
    </aside>
  );
}
