export const ASSESSMENT_RUN_ID = "assessment_38118701d2db5edb1013b6584591b78bd3d697cd3d47367af8c05eebc261c1d3" as const;

export type AssessmentType = "LESSON_QUIZ" | "UNIT_TEST" | "LEVEL_TEST" | "PLACEMENT";
export type AssessmentItemType = "multiple_choice" | "fill_blank" | "matching" | "ordering" | "reading" | "listening";

export interface AssessmentSource {
  readonly level: string;
  readonly tier: string;
  readonly unitId: string;
  readonly lessonId: string;
  readonly packetId: string;
  readonly packetSha256: string;
  readonly exerciseId: string;
  readonly questionIndex?: number;
}

export type AssessmentAnswerContract =
  | Readonly<{ correctAnswer: string }>
  | Readonly<{ acceptableAnswers: readonly string[] }>
  | Readonly<{ pairs: readonly Readonly<{ left: string; right: string }>[] }>
  | Readonly<{ correctOrder: readonly string[] }>;

export interface AssessmentItem {
  readonly id: string;
  readonly type: AssessmentItemType;
  readonly prompt: string;
  readonly stimulus?: string;
  readonly question?: string;
  readonly options?: readonly string[];
  readonly items?: readonly string[];
  readonly source: AssessmentSource;
  readonly targetIds: readonly string[];
  readonly targetDimensions: readonly string[];
  readonly conceptIds: readonly string[];
  readonly answerContract: AssessmentAnswerContract;
}

export interface AssessmentScope {
  readonly levels: readonly string[];
  readonly tiers: readonly string[];
  readonly unitIds: readonly string[];
  readonly lessonIds: readonly string[];
  readonly targetDimensions?: readonly string[];
  readonly outlineAssessmentId?: string;
  readonly itemsPerTier?: number;
  readonly passingCorrectPerTier?: number;
  readonly outputField?: string;
}

export interface AssessmentPackage {
  readonly id: string;
  readonly type: AssessmentType;
  readonly packageSha256: string;
  readonly scope: AssessmentScope;
  readonly items: readonly AssessmentItem[];
  readonly contentStatus: "UNREVIEWED";
}

export interface AssessmentSnapshot {
  readonly schemaVersion: "1.0";
  readonly runId: typeof ASSESSMENT_RUN_ID;
  readonly manifestSha256: string;
  readonly contentStatus: "UNREVIEWED";
  readonly packages: readonly AssessmentPackage[];
}
