import { buildReadingSnapshot } from "./build-reading-snapshot.mjs";
import { readFile } from "node:fs/promises";
import path from "node:path";
import { fileURLToPath } from "node:url";

const scriptDirectory = path.dirname(fileURLToPath(import.meta.url));
const snapshotPath = path.resolve(scriptDirectory, "../src/content/generated/reading-snapshot.json");
const expected = `${JSON.stringify(await buildReadingSnapshot(), null, 2)}\n`;
const actual = await readFile(snapshotPath, "utf8");

if (actual !== expected) {
  throw new Error("Reading snapshot is stale; run npm run build:reading-snapshot after an explicit source update.");
}

console.log(`Verified deterministic ${JSON.parse(expected).readers.length}-reader reading snapshot.`);
