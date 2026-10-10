declare module "*.mjs" {
  export const addUniqueIdentity: (identities: Set<string>, language: string, lessonId: string) => void;
  export const assertBytesHash: (bytes: Buffer, expected: string, label: string) => void;
  export const assertSafeInventoryPaths: (inventory: readonly { path: string }[], label: string) => readonly string[];
  export const assertUnreviewed: (status: string, label: string) => void;
  export const buildSnapshot: () => Promise<{ lessons: readonly Record<string, unknown>[]; languages: readonly unknown[] }>;
  export const buildVocabularySnapshot: () => Promise<{ schemaVersion: string; inventoryVersion: string; senses: readonly Record<string, unknown>[] }>;
  export const buildDictionarySnapshot: () => Promise<{ schemaVersion: string; inventoryVersion: string; entries: readonly { id: string; headword: string; senseNumber?: number; contentStatus: string }[] }>;  export const buildGrammarSnapshot: () => Promise<{ schemaVersion: string; inventoryVersion: string; targets: readonly Record<string, unknown>[] }>;
  export const buildListeningSnapshot: () => Promise<{ schemaVersion: string; inventoryVersion: string; availability: string; sessions: readonly Record<string, unknown>[] }>;
  export const buildPronunciationSnapshot: () => Promise<{ schemaVersion: string; inventoryVersion: string; protocols: readonly Record<string, unknown>[] }>;
  export const buildReadingSnapshot: () => Promise<{ schemaVersion: string; inventoryVersion: string; readers: readonly Record<string, unknown>[] }>;
  export const buildSpeakingSnapshot: () => Promise<{ schemaVersion: string; inventoryVersion: string; protocols: readonly Record<string, unknown>[] }>;
  export const buildWritingSnapshot: () => Promise<{ schemaVersion: string; inventoryVersion: string; protocols: readonly Record<string, unknown>[] }>;
  export const projectExercise: (exercise: Record<string, unknown>, label: string) => Record<string, unknown>;
  export const projectPracticeProtocol: (protocol: Record<string, unknown>, label: string) => Record<string, unknown>;
  export const adaptGermanPacket: (packet: Record<string, unknown>, source: Record<string, unknown>) => Record<string, unknown>;
  export const routeUrl: (file: string) => string;
  export const serviceWorkerSource: (manifest: { version: string; shell: readonly string[]; routes: readonly string[] }) => string;
  export const cacheControlFor: (relativePath: string) => string;
  export const safePath: (root: string, urlPath: string) => string | null;
  export const responseHeaders: (root: string, target: string) => Record<string, string>;
}
