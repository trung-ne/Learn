declare module "*.mjs" {
  export const addUniqueIdentity: (identities: Set<string>, language: string, lessonId: string) => void;
  export const assertBytesHash: (bytes: Buffer, expected: string, label: string) => void;
  export const assertSafeInventoryPaths: (inventory: readonly { path: string }[], label: string) => readonly string[];
  export const assertUnreviewed: (status: string, label: string) => void;
  export const buildSnapshot: () => Promise<{ lessons: readonly Record<string, unknown>[]; languages: readonly unknown[] }>;
  export const projectExercise: (exercise: Record<string, unknown>, label: string) => Record<string, unknown>;
  export const projectPracticeProtocol: (protocol: Record<string, unknown>, label: string) => Record<string, unknown>;
  export const adaptGermanPacket: (packet: Record<string, unknown>, source: Record<string, unknown>) => Record<string, unknown>;}
