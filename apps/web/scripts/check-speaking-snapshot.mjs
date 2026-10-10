import { readFile } from "node:fs/promises";
import path from "node:path";
import { fileURLToPath } from "node:url";
import { buildSpeakingSnapshot } from "./build-speaking-snapshot.mjs";

const scriptDirectory = path.dirname(fileURLToPath(import.meta.url));
const snapshotPath = path.resolve(scriptDirectory, "../src/content/generated/speaking-snapshot.json");

const expected = `${JSON.stringify(await buildSpeakingSnapshot(), null, 2)}\n`;
const actual = await readFile(snapshotPath, "utf8");
if (actual !== expected) throw new Error("Speaking snapshot is stale; run npm run build:speaking-snapshot");
console.log("Speaking snapshot is current.");
