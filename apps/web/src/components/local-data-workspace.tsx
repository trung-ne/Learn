"use client";

import { ChangeEvent, useState } from "react";
import {
  applyLocalDataBackup,
  clearEnglishMasterLocalData,
  createLocalDataBackup,
  inspectLocalDataBackup,
  type BackupInspection,
} from "@/lib/local-data-backup";
import { browserLocalStorage } from "@/lib/local-state";

function downloadBackup(): boolean {
  const storage = browserLocalStorage();
  if (!storage) return false;
  const backup = createLocalDataBackup(storage);
  const blob = new Blob([`${JSON.stringify(backup, null, 2)}\n`], { type: "application/json" });
  const url = URL.createObjectURL(blob);
  const anchor = document.createElement("a");
  anchor.href = url;
  anchor.download = `english-master-local-backup-${backup.createdAt.slice(0, 10)}.json`;
  anchor.click();
  URL.revokeObjectURL(url);
  return true;
}

export function LocalDataWorkspace() {
  const [inspection, setInspection] = useState<BackupInspection>();
  const [status, setStatus] = useState<string>();
  const [resetConfirmed, setResetConfirmed] = useState(false);

  function exportData() {
    setStatus(downloadBackup()
      ? "A local backup download has started. Store it safely: it can contain writing drafts and a browser-local learner identifier."
      : "This browser cannot read local learning data for backup.");
  }

  function inspectFile(event: ChangeEvent<HTMLInputElement>) {
    const file = event.currentTarget.files?.[0];
    setInspection(undefined);
    setStatus(undefined);
    if (!file) return;
    if (file.size > 2_000_000) {
      setInspection({ valid: false, recordCount: 0, error: "The selected file exceeds the local safety limit." });
      return;
    }
    const reader = new FileReader();
    reader.onload = () => setInspection(inspectLocalDataBackup(String(reader.result ?? "")));
    reader.onerror = () => setInspection({ valid: false, recordCount: 0, error: "The selected backup could not be read." });
    reader.readAsText(file);
  }

  function restoreData() {
    const storage = browserLocalStorage();
    if (!storage || !inspection?.valid || !inspection.backup) {
      setStatus("The checked backup could not be restored.");
      return;
    }
    setStatus(applyLocalDataBackup(inspection.backup, storage)
      ? `Restored ${inspection.recordCount} local learning record${inspection.recordCount === 1 ? "" : "s"}. Reload a workspace to see its restored state.`
      : "The backup was not restored. Check browser storage availability and try again.");
  }

  function resetData() {
    const storage = browserLocalStorage();
    if (!storage || !resetConfirmed) return;
    setStatus(clearEnglishMasterLocalData(storage)
      ? "This browser’s English Master local learning data was cleared."
      : "This browser could not clear all English Master local learning data.");
    setResetConfirmed(false);
  }

  return (
    <section className="local-data-workspace" aria-labelledby="local-data-heading">
      <p className="eyebrow">Browser-local data</p>
      <h1 id="local-data-heading">Data and offline tools</h1>
      <p className="lede">Progress, review state, assessment drafts, and writing drafts stay in this browser. They are not synchronized to an account or sent to English Master.</p>
      <div className="local-data-boundary">
        <h2>Before you change browsers or clear site data</h2>
        <p>Export a backup. Backup files can contain learner-authored writing drafts and a browser-local learner identifier, so store them safely.</p>
      </div>
      <section className="local-data-card" aria-labelledby="export-heading">
        <h2 id="export-heading">Export local data</h2>
        <p>Creates a JSON file in your browser. Nothing is uploaded or synchronized.</p>
        <button className="primary-button" type="button" onClick={exportData}>Download local backup</button>
      </section>
      <section className="local-data-card" aria-labelledby="restore-heading">
        <h2 id="restore-heading">Check and restore a backup</h2>
        <p>The app checks the file before writing any records. Unknown, malformed, unsupported, and oversized records are rejected.</p>
        <label className="local-file-input">
          Select a local backup file
          <input type="file" accept="application/json,.json" onChange={inspectFile} />
        </label>
        {inspection && (
          <div className={inspection.valid ? "local-data-result valid" : "local-data-result invalid"} role="status">
            {inspection.valid
              ? <p>Backup checked: {inspection.recordCount} allowed local record{inspection.recordCount === 1 ? "" : "s"}, created {inspection.backup?.createdAt}.</p>
              : <p>Backup not accepted: {inspection.error}</p>}
          </div>
        )}
        <button className="secondary-button" type="button" onClick={restoreData} disabled={!inspection?.valid}>Restore checked backup</button>
      </section>
      <section className="local-data-card local-data-danger" aria-labelledby="reset-heading">
        <h2 id="reset-heading">Clear this browser’s learning data</h2>
        <p>This affects only English Master keys in this browser. It cannot be undone unless you exported a backup first.</p>
        <label className="completion-toggle"><input type="checkbox" checked={resetConfirmed} onChange={(event) => setResetConfirmed(event.target.checked)} /> I understand that this clears browser-local learning data.</label>
        <button className="secondary-button" type="button" onClick={resetData} disabled={!resetConfirmed}>Clear local learning data</button>
      </section>
      {status && <p className="local-data-status" role="status">{status}</p>}
    </section>
  );
}
