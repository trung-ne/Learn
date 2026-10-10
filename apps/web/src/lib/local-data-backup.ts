import { isEnglishMasterStorageKey, localStorageEntries, reportLocalStateIssue } from "./local-state";

export const LOCAL_BACKUP_VERSION = 1 as const;
export const MAX_BACKUP_BYTES = 2_000_000;
export const MAX_BACKUP_RECORDS = 200;
export const MAX_BACKUP_RECORD_BYTES = 500_000;

export interface LocalDataBackup {
  readonly version: typeof LOCAL_BACKUP_VERSION;
  readonly createdAt: string;
  readonly records: Readonly<Record<string, string>>;
}

export interface BackupInspection {
  readonly valid: boolean;
  readonly backup?: LocalDataBackup;
  readonly recordCount: number;
  readonly error?: string;
}

function isIsoTimestamp(value: unknown): value is string {
  return typeof value === "string" && !Number.isNaN(Date.parse(value));
}

function validRecord(key: string, value: unknown): value is string {
  if (!isEnglishMasterStorageKey(key) || typeof value !== "string" || value.length > MAX_BACKUP_RECORD_BYTES) return false;
  try {
    const parsed: unknown = JSON.parse(value);
    return parsed !== null && typeof parsed === "object";
  } catch {
    return false;
  }
}

export function createLocalDataBackup(storage: Storage): LocalDataBackup {
  return {
    version: LOCAL_BACKUP_VERSION,
    createdAt: new Date().toISOString(),
    records: localStorageEntries(storage),
  };
}

export function inspectLocalDataBackup(serialized: string): BackupInspection {
  if (serialized.length > MAX_BACKUP_BYTES) {
    return { valid: false, recordCount: 0, error: "The backup file exceeds the local safety limit." };
  }
  try {
    const candidate: unknown = JSON.parse(serialized);
    if (!candidate || typeof candidate !== "object" || Array.isArray(candidate)) {
      return { valid: false, recordCount: 0, error: "The backup file is not an English Master backup object." };
    }
    const backup = candidate as Partial<LocalDataBackup>;
    if (backup.version !== LOCAL_BACKUP_VERSION || !isIsoTimestamp(backup.createdAt) || !backup.records || typeof backup.records !== "object" || Array.isArray(backup.records)) {
      return { valid: false, recordCount: 0, error: "The backup version or envelope is not supported." };
    }
    const records = Object.entries(backup.records);
    if (records.length > MAX_BACKUP_RECORDS || !records.every(([key, value]) => validRecord(key, value))) {
      return { valid: false, recordCount: records.length, error: "The backup contains an unsupported, malformed, or oversized local record." };
    }
    return {
      valid: true,
      recordCount: records.length,
      backup: { version: LOCAL_BACKUP_VERSION, createdAt: backup.createdAt, records: Object.fromEntries(records) },
    };
  } catch {
    return { valid: false, recordCount: 0, error: "The backup file is not valid JSON." };
  }
}

export function applyLocalDataBackup(backup: LocalDataBackup, storage: Storage): boolean {
  const inspection = inspectLocalDataBackup(JSON.stringify(backup));
  if (!inspection.valid || !inspection.backup) return false;
  const previous = localStorageEntries(storage);
  try {
    for (const key of Object.keys(previous)) storage.removeItem(key);
    for (const [key, value] of Object.entries(inspection.backup.records)) storage.setItem(key, value);
    return true;
  } catch (error) {
    try {
      for (const key of Object.keys(localStorageEntries(storage))) storage.removeItem(key);
      for (const [key, value] of Object.entries(previous)) storage.setItem(key, value);
    } catch {
      // Preserve the original write failure as the actionable condition.
    }
    reportLocalStateIssue("import", error);
    return false;
  }
}

export function clearEnglishMasterLocalData(storage: Storage): boolean {
  const keys = Object.keys(localStorageEntries(storage));
  try {
    for (const key of keys) storage.removeItem(key);
    return true;
  } catch (error) {
    reportLocalStateIssue("remove", error);
    return false;
  }
}
