import { readFile } from "node:fs/promises";
import path from "node:path";
import { fileURLToPath } from "node:url";
import { buildPronunciationSnapshot } from "./build-pronunciation-snapshot.mjs";

const scriptDirectory = path.dirname(fileURLToPath(import.meta.url));
const snapshotPath = path.resolve(scriptDirectory, "../src/content/generated/pronunciation-snapshot.json");

const expected = `${JSON.stringify(await buildPronunciationSnapshot(), null, 2)}\n`;
const actual = await readFile(snapshotPath, "utf8");
if (actual !== expected) throw new Error("Pronunciation snapshot is stale; run npm run build:pronunciation-snapshot");
console.log("Pronunciation snapshot is current.");
