import rawSnapshot from "./generated/curriculum-snapshot.json";
import { getLanguageConfiguration, isAvailableLevel, isLanguageCode, languages } from "./languages";
import type {
  Band,
  CourseAvailability,
  CurriculumSnapshot,
  DisplayLesson,
  LanguageCode,
  LanguageSummary,
} from "./types";

export interface CourseSummary {
  readonly language: LanguageCode;
  readonly level: Band;
  readonly lessonCount: number;
  readonly availability: CourseAvailability;
  readonly firstLesson: DisplayLesson;
}

const practiceModalities = new Set(["listening", "speaking", "pronunciation", "writing"]);
const practiceStringFields = new Set([
  "instruction",
  "goal",
  "question",
  "answer",
  "transcript",
  "target",
  "without_audio",
  "assessment",
  "feedback_boundary",
  "mode",
  "situation",
  "learner_role",
  "ai_role",
  "explanation",
]);
const practiceArrayFields = new Set(["constraints", "checklist", "useful_language", "examples"]);
const exerciseStringFields = new Set([
  "id",
  "type",
  "prompt",
  "correct_answer",
  "answer",
  "stimulus",
  "explanation",
]);
const exerciseStringArrayFields = new Set(["options", "acceptable_answers", "items", "correct_order"]);
const simpleObjectiveTypes = new Set(["multiple_choice", "fill_blank", "selection", "completion"]);
const questionObjectiveTypes = new Set(["reading", "listening"]);

function hasUniqueStrings(values: readonly string[]): boolean {
  return new Set(values).size === values.length;
}

function lessonsFor(value: CurriculumSnapshot, language: LanguageCode): readonly DisplayLesson[] {
  return value.lessons.filter((lesson) => lesson.language === language);
}

function expectedBands(lessons: readonly DisplayLesson[]): readonly Band[] {
  return [...new Set(lessons.map((lesson) => lesson.band))];
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return Boolean(value) && typeof value === "object" && !Array.isArray(value);
}

function hasOnlyFields(value: Record<string, unknown>, allowed: ReadonlySet<string>, label: string): void {
  if (Object.keys(value).some((field) => !allowed.has(field))) {
    throw new Error(`${label} contains unsupported learner-facing fields.`);
  }
}

function isSafeSegment(value: unknown): value is string {
  return typeof value === "string" && /^[A-Za-z0-9][A-Za-z0-9._-]*$/u.test(value);
}

function isNonEmptyString(value: unknown): value is string {
  return typeof value === "string" && value.trim().length > 0;
}

function isStringArray(value: unknown): value is readonly string[] {
  return Array.isArray(value) && value.every(isNonEmptyString);
}

function isCourseAvailability(value: unknown): value is CourseAvailability {
  return value === "AVAILABLE" || value === "PILOT";
}

function isPositiveInteger(value: unknown): value is number {
  return typeof value === "number" && Number.isInteger(value) && value > 0;
}

function validateOptionalString(value: unknown, label: string): void {
  if (value !== undefined && !isNonEmptyString(value)) throw new Error(`${label} must be a non-empty string.`);
}

function validateOptionalStringArray(value: unknown, label: string): void {
  if (value !== undefined && !isStringArray(value)) throw new Error(`${label} must be an array of non-empty strings.`);
}

function validateSection(value: unknown): void {
  if (!isRecord(value)) throw new Error("Curriculum snapshot contains an invalid section.");
  hasOnlyFields(value, new Set(["id", "title", "type", "body", "vietnameseTip"]), "Section");
  if (!isSafeSegment(value.id) || !isNonEmptyString(value.title) || !isNonEmptyString(value.type) || !isNonEmptyString(value.body)) {
    throw new Error("Curriculum snapshot contains an invalid section.");
  }
  validateOptionalString(value.vietnameseTip, "Section Vietnamese tip");
}

function validateExercise(value: unknown): void {
  if (!isRecord(value)) throw new Error("Curriculum snapshot contains an invalid exercise.");
  hasOnlyFields(
    value,
    new Set([...exerciseStringFields, ...exerciseStringArrayFields, "pairs", "questions", "rubric"]),
    "Exercise",
  );
  for (const field of exerciseStringFields) validateOptionalString(value[field], `Exercise ${field}`);
  if (!isSafeSegment(value.id) || !isNonEmptyString(value.type) || !isNonEmptyString(value.prompt)) {
    throw new Error("Curriculum snapshot contains an invalid exercise.");
  }
  for (const field of exerciseStringArrayFields) validateOptionalStringArray(value[field], `Exercise ${field}`);
  if (value.pairs !== undefined) {
    if (!Array.isArray(value.pairs) || !value.pairs.every((pair) =>
      isRecord(pair) && Object.keys(pair).every((field) => field === "left" || field === "right") &&
      isNonEmptyString(pair.left) && isNonEmptyString(pair.right)
    ) || !hasUniqueStrings(value.pairs.map((pair) => (pair as Record<string, string>).left)) ||
      !hasUniqueStrings(value.pairs.map((pair) => (pair as Record<string, string>).right))) {
      throw new Error("Curriculum snapshot contains invalid exercise pairs.");
    }
  }
  if (value.questions !== undefined) {
    if (!Array.isArray(value.questions) || !value.questions.every((question) =>
      isRecord(question) && Object.keys(question).every((field) => field === "question" || field === "acceptable_answers") &&
      isNonEmptyString(question.question) && isStringArray(question.acceptable_answers) && question.acceptable_answers.length > 0
    ) || !hasUniqueStrings(value.questions.map((question) => (question as Record<string, string>).question))) {
      throw new Error("Curriculum snapshot contains invalid exercise questions.");
    }
  }
  if (value.rubric !== undefined && !isNonEmptyString(value.rubric)) {
    if (!isRecord(value.rubric) || Object.keys(value.rubric).some((field) => field !== "criteria") ||
      (value.rubric.criteria !== undefined && !isStringArray(value.rubric.criteria))) {
      throw new Error("Curriculum snapshot contains an invalid exercise rubric.");
    }
  }

  if (simpleObjectiveTypes.has(value.type)) {
    const answers = value.correct_answer
      ? [value.correct_answer]
      : Array.isArray(value.acceptable_answers) ? value.acceptable_answers : value.answer ? [value.answer] : [];
    if (!answers.length) throw new Error("Curriculum snapshot objective exercise requires answer data.");
    if (value.type === "multiple_choice") {
      if (!Array.isArray(value.options) || !value.options.length || !hasUniqueStrings(value.options) ||
        !answers.every((answer) => value.options!.includes(answer))) {
        throw new Error("Curriculum snapshot multiple-choice exercise requires unique options containing its answer data.");
      }
    }
  } else if (value.type === "matching") {
    if (!Array.isArray(value.pairs) || !value.pairs.length) {
      throw new Error("Curriculum snapshot matching exercise requires pairs.");
    }
  } else if (value.type === "ordering") {
    if (!Array.isArray(value.items) || !Array.isArray(value.correct_order) || !value.items.length ||
      value.items.length !== value.correct_order.length || !hasUniqueStrings(value.items) ||
      !hasUniqueStrings(value.correct_order) ||
      JSON.stringify([...value.items].sort()) !== JSON.stringify([...value.correct_order].sort())) {
      throw new Error("Curriculum snapshot ordering exercise requires compatible unique items and answer data.");
    }
  } else if (questionObjectiveTypes.has(value.type) && (!Array.isArray(value.questions) || !value.questions.length)) {
    throw new Error("Curriculum snapshot reading or listening exercise requires answerable questions.");
  }
}

function validateUniqueRecordIds(values: readonly unknown[], label: string): void {
  const ids = values.map((value) => isRecord(value) ? value.id : undefined);
  if (!ids.every(isSafeSegment) || new Set(ids).size !== ids.length) {
    throw new Error(`Curriculum snapshot contains duplicate or invalid ${label} IDs.`);
  }
}

function validatePractice(value: unknown): void {
  if (!isRecord(value)) throw new Error("Curriculum snapshot contains invalid practice protocols.");
  for (const [modality, protocol] of Object.entries(value)) {
    if (!practiceModalities.has(modality) || !isRecord(protocol)) {
      throw new Error("Curriculum snapshot contains an unsupported practice modality.");
    }
    hasOnlyFields(protocol, new Set([...practiceStringFields, ...practiceArrayFields]), "Practice protocol");
    if (!isNonEmptyString(protocol.instruction)) throw new Error("Practice protocol requires an instruction.");
    for (const field of practiceStringFields) validateOptionalString(protocol[field], `Practice ${field}`);
    for (const field of practiceArrayFields) validateOptionalStringArray(protocol[field], `Practice ${field}`);
  }
}

export function validateSnapshot(value: unknown): asserts value is CurriculumSnapshot {
  if (!isRecord(value) || value.schemaVersion !== "1.1" || !Array.isArray(value.lessons) || !Array.isArray(value.languages)) {
    throw new Error("Unsupported curriculum snapshot metadata.");
  }
  hasOnlyFields(value, new Set(["schemaVersion", "languages", "lessons"]), "Curriculum snapshot");
  if (value.languages.length !== Object.keys(languages).length) {
    throw new Error("Curriculum snapshot language inventory is unsupported.");
  }

  const identities = new Set<string>();
  const summaryCodes = new Set<string>();
  for (const summary of value.languages) {
    if (!isRecord(summary)) throw new Error("Curriculum snapshot has an unsupported language.");
    const code = summary.code;
    if (typeof code !== "string" || !isLanguageCode(code) || summaryCodes.has(code)) {
      throw new Error("Curriculum snapshot has an unsupported language.");
    }
    hasOnlyFields(summary, new Set(["code", "name", "lessonCount", "bands"]), "Language summary");
    summaryCodes.add(code);
    const configuration = getLanguageConfiguration(code);
    if (!configuration || summary.name !== configuration.name || !isPositiveInteger(summary.lessonCount) || !Array.isArray(summary.bands) ||
      !summary.bands.every((band) => typeof band === "string" && isAvailableLevel(code, band))) {
      throw new Error("Curriculum snapshot language metadata drifted.");
    }
  }

  for (const lesson of value.lessons) {
    if (!isRecord(lesson)) throw new Error("Curriculum snapshot contains an invalid lesson.");
    hasOnlyFields(lesson, new Set([
      "language", "band", "courseAvailability", "tier", "unitId", "lessonId", "sequence", "title", "topic",
      "durationMinutes", "objectives", "languageFocus", "prerequisites", "sections", "exercises", "practice",
    ]), "Lesson");
    if (
      typeof lesson.language !== "string" ||
      !isLanguageCode(lesson.language) ||
      typeof lesson.band !== "string" ||
      !isAvailableLevel(lesson.language, lesson.band) ||
      !isCourseAvailability(lesson.courseAvailability) ||
      !isNonEmptyString(lesson.tier) ||
      !isSafeSegment(lesson.unitId) ||
      !isSafeSegment(lesson.lessonId) ||
      !isNonEmptyString(lesson.title) ||
      !isNonEmptyString(lesson.topic) ||
      !isPositiveInteger(lesson.sequence) ||
      !isPositiveInteger(lesson.durationMinutes)
    ) {
      throw new Error("Curriculum snapshot contains an unsupported lesson.");
    }
    validateOptionalStringArray(lesson.objectives, "Lesson objectives");
    validateOptionalString(lesson.languageFocus, "Lesson language focus");
    validateOptionalStringArray(lesson.prerequisites, "Lesson prerequisites");
    if (lesson.sections !== undefined) {
      if (!Array.isArray(lesson.sections)) throw new Error("Lesson sections must be an array.");
      lesson.sections.forEach(validateSection);
      validateUniqueRecordIds(lesson.sections, "section");
    }
    if (lesson.exercises !== undefined) {
      if (!Array.isArray(lesson.exercises)) throw new Error("Lesson exercises must be an array.");
      lesson.exercises.forEach(validateExercise);
      validateUniqueRecordIds(lesson.exercises, "exercise");
    }
    if (lesson.practice !== undefined) validatePractice(lesson.practice);
    const identity = `${lesson.language}:${lesson.lessonId}`;
    if (identities.has(identity)) throw new Error(`Duplicate lesson identity: ${identity}`);
    identities.add(identity);
  }

  const snapshot = value as CurriculumSnapshot;
  for (const code of Object.keys(languages) as LanguageCode[]) {
    const summary = snapshot.languages.find((item) => item.code === code);
    const languageLessons = lessonsFor(snapshot, code);
    const bands = expectedBands(languageLessons);
    if (!summary || summary.lessonCount !== languageLessons.length || JSON.stringify(summary.bands) !== JSON.stringify(bands)) {
      throw new Error(`Curriculum snapshot availability drifted for ${code}.`);
    }
  }
}

const candidateSnapshot: unknown = rawSnapshot;
validateSnapshot(candidateSnapshot);
export const snapshot = candidateSnapshot;

export function getLanguages(): readonly LanguageSummary[] {
  return snapshot.languages;
}

export function getLanguage(code: string): LanguageSummary | undefined {
  if (!isLanguageCode(code)) return undefined;
  return snapshot.languages.find((language) => language.code === code);
}

export function getLessonsForLanguage(code: LanguageCode): readonly DisplayLesson[] {
  return lessonsFor(snapshot, code);
}

export function getLessonsForLanguageLevel(
  language: LanguageCode,
  level: Band,
): readonly DisplayLesson[] {
  return snapshot.lessons.filter((lesson) => lesson.language === language && lesson.band === level);
}

export function getAvailableCourses(language?: LanguageCode): readonly CourseSummary[] {
  const codes: readonly LanguageCode[] = language ? [language] : (Object.keys(languages) as LanguageCode[]);
  return codes.flatMap((code) => {
    const configuration = getLanguageConfiguration(code);
    if (!configuration) return [];
    return configuration.availableLevels.flatMap((level) => {
      const lessons = getLessonsForLanguageLevel(code, level);
      if (lessons.length === 0) return [];
      return [{
        language: code,
        level,
        lessonCount: lessons.length,
        availability: lessons[0]!.courseAvailability,
        firstLesson: lessons[0]!,
      }];
    });
  });
}

export function isAvailableCourse(language: LanguageCode, level: string): level is Band {
  return getAvailableCourses(language).some((course) => course.level === level);
}

export function getLessonById(language: LanguageCode, level: Band, lessonId: string): DisplayLesson | undefined {
  return getLessonsForLanguageLevel(language, level).find((lesson) => lesson.lessonId === lessonId);
}

export function getLesson(
  language: string,
  level: string,
  unitId: string,
  lessonId: string,
): DisplayLesson | undefined {
  if (!isLanguageCode(language) || !isAvailableCourse(language, level)) return undefined;
  return getLessonsForLanguageLevel(language, level).find(
    (lesson) => lesson.unitId === unitId && lesson.lessonId === lessonId,
  );
}

export function groupLessonsByTierAndUnit(
  lessons: readonly DisplayLesson[],
): ReadonlyMap<string, ReadonlyMap<string, readonly DisplayLesson[]>> {
  const tiers = new Map<string, Map<string, DisplayLesson[]>>();
  for (const lesson of lessons) {
    const units = tiers.get(lesson.tier) ?? new Map<string, DisplayLesson[]>();
    const unitLessons = units.get(lesson.unitId) ?? [];
    unitLessons.push(lesson);
    units.set(lesson.unitId, unitLessons);
    tiers.set(lesson.tier, units);
  }
  return tiers;
}

export { isAvailableLevel, isLanguageCode };
