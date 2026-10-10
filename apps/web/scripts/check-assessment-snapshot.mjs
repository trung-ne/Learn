import { readFile } from "node:fs/promises";
import path from "node:path";
import { fileURLToPath } from "node:url";
import { buildAssessmentSnapshot } from "./build-assessment-snapshot.mjs";

const scriptDirectory = path.dirname(fileURLToPath(import.meta.url));
const snapshotPath = path.resolve(scriptDirectory, "../src/content/generated/assessment-snapshot.json");
const expected = `${JSON.stringify(await buildAssessmentSnapshot(), null, 2)}\n`;
const actual = await readFile(snapshotPath, "utf8");
if (actual !== expected) {
  throw new Error("Assessment snapshot is stale; run npm run build:assessment-snapshot after an explicit upstream update.");
}
console.log("Verified deterministic 367-package English assessment snapshot.");
