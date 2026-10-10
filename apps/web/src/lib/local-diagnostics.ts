export const DIAGNOSTICS_VERSION = 1 as const;
const DIAGNOSTICS_KEY = "english-master.diagnostics.v1";
const MAX_DIAGNOSTICS = 20;

export interface LocalDiagnostic {
  readonly category: "render" | "storage" | "service_worker" | "offline";
  readonly occurredAt: string;
  readonly buildId: string;
  readonly pathname: string;
}

export interface LocalDiagnosticLog {
  readonly version: typeof DIAGNOSTICS_VERSION;
  readonly records: readonly LocalDiagnostic[];
}

function emptyLog(): LocalDiagnosticLog {
  return { version: DIAGNOSTICS_VERSION, records: [] };
}

function validRecord(value: unknown): value is LocalDiagnostic {
  if (!value || typeof value !== "object") return false;
  const record = value as Partial<LocalDiagnostic>;
  return (
    (record.category === "render" || record.category === "storage" || record.category === "service_worker" || record.category === "offline") &&
    typeof record.occurredAt === "string" && !Number.isNaN(Date.parse(record.occurredAt)) &&
    typeof record.buildId === "string" && record.buildId.length <= 128 &&
    typeof record.pathname === "string" && record.pathname.startsWith("/") && record.pathname.length <= 512 && !record.pathname.includes("?") && !record.pathname.includes("#")
  );
}

export function parseLocalDiagnostics(serialized: string | null): LocalDiagnosticLog {
  if (!serialized) return emptyLog();
  try {
    const candidate: unknown = JSON.parse(serialized);
    if (!candidate || typeof candidate !== "object") return emptyLog();
    const log = candidate as Partial<LocalDiagnosticLog>;
    if (log.version !== DIAGNOSTICS_VERSION || !Array.isArray(log.records) || !log.records.every(validRecord)) return emptyLog();
    return { version: DIAGNOSTICS_VERSION, records: log.records.slice(-MAX_DIAGNOSTICS) };
  } catch {
    return emptyLog();
  }
}

export function recordLocalDiagnostic(
  diagnostic: LocalDiagnostic,
  storage: Pick<Storage, "getItem" | "setItem"> = window.localStorage,
): boolean {
  if (!validRecord(diagnostic)) return false;
  try {
    const current = parseLocalDiagnostics(storage.getItem(DIAGNOSTICS_KEY));
    storage.setItem(DIAGNOSTICS_KEY, JSON.stringify({
      version: DIAGNOSTICS_VERSION,
      records: [...current.records, diagnostic].slice(-MAX_DIAGNOSTICS),
    }));
    return true;
  } catch {
    return false;
  }
}

export function localDiagnosticExport(
  storage: Pick<Storage, "getItem"> = window.localStorage,
): LocalDiagnosticLog {
  try {
    return parseLocalDiagnostics(storage.getItem(DIAGNOSTICS_KEY));
  } catch {
    return emptyLog();
  }
}
