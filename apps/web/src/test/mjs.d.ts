declare module "*.mjs" {
  export const addUniqueIdentity: (identities: Set<string>, language: string, lessonId: string) => void;
  export const assertBytesHash: (bytes: Buffer, expected: string, label: string) => void;
  export const assertSafeInventoryPaths: (inventory: readonly { path: string }[], label: string) => readonly string[];
  export const assertUnreviewed: (status: string, label: string) => void;
  export const buildSnapshot: () => Promise<{ lessons: readonly unknown[]; sourceManifests: readonly { packetCount: number }[] }>;
}
