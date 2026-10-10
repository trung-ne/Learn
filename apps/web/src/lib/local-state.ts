export const LOCAL_STATE_EVENT = "english-master:local-state";

export type LocalStateIssue = "read" | "write" | "remove" | "import" | "quota";

export interface LocalStateStatus {
  readonly available: boolean;
  readonly issue?: LocalStateIssue;
  readonly occurredAt?: string;
}

const LEARNER_ID = "[a-z0-9-]{8,128}";
const LANGUAGE = "(?:en|de)";
const BAND = "(?:A1|A2|B1|B2|C1|C2)";
const APP_STORAGE_KEY = new RegExp(
  `^english-master\\.(?:learner\\.v2\\.profile|diagnostics\\.v1|` +
  `(?:progress\\.v2|review\\.v1|listening-lab\\.v1)\\.${LEARNER_ID}\\.${LANGUAGE}\\.${BAND}|` +
  `(?:vocabulary\\.v1|grammar\\.v1|dictionary\\.v1|writing\\.v1|reading\\.v1|tutor-preferences\\.v1)\\.${LEARNER_ID}\\.${LANGUAGE}|` +
  `assessment\\.v1\\.${LEARNER_ID}\\.en\\.[a-z0-9_-]+)$`,
  "u",
);

let currentStatus: LocalStateStatus = { available: true };

function isBrowser(): boolean {
  return typeof window !== "undefined" && typeof window.localStorage !== "undefined";
}

function issueFor(error: unknown, fallback: LocalStateIssue): LocalStateIssue {
  return error instanceof DOMException && error.name === "QuotaExceededError" ? "quota" : fallback;
}

function publish(status: LocalStateStatus): void {
  currentStatus = status;
  if (isBrowser()) window.dispatchEvent(new CustomEvent<LocalStateStatus>(LOCAL_STATE_EVENT, { detail: status }));
}

export function localStateStatus(): LocalStateStatus {
  return currentStatus;
}

export function reportLocalStateIssue(issue: LocalStateIssue, error?: unknown): void {
  publish({ available: false, issue: issueFor(error, issue), occurredAt: new Date().toISOString() });
}

export function reportLocalStateAvailable(): void {
  if (!currentStatus.available) publish({ available: true });
}

export function isEnglishMasterStorageKey(key: string): boolean {
  return APP_STORAGE_KEY.test(key);
}

export function browserLocalStorage(): Storage | undefined {
  if (!isBrowser()) return undefined;
  try {
    const storage = window.localStorage;
    const probe = "english-master.storage-probe";
    storage.setItem(probe, "1");
    storage.removeItem(probe);
    reportLocalStateAvailable();
    return storage;
  } catch (error) {
    reportLocalStateIssue("write", error);
    return undefined;
  }
}

export function localStorageEntries(storage: Storage): Readonly<Record<string, string>> {
  const entries: Record<string, string> = {};
  try {
    for (let index = 0; index < storage.length; index += 1) {
      const key = storage.key(index);
      if (key && isEnglishMasterStorageKey(key)) {
        const value = storage.getItem(key);
        if (value !== null) entries[key] = value;
      }
    }
  } catch (error) {
    reportLocalStateIssue("read", error);
  }
  return entries;
}
