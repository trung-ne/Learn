import { readFile } from "node:fs/promises";
import path from "node:path";
import { fileURLToPath } from "node:url";
import { buildWritingSnapshot } from "./build-writing-snapshot.mjs";

const scriptDirectory = path.dirname(fileURLToPath(import.meta.url));
const snapshotPath = path.resolve(scriptDirectory, "../src/content/generated/writing-snapshot.json");
const expected = `${JSON.stringify(await buildWritingSnapshot(), null, 2)}\n`;
const actual = await readFile(snapshotPath, "utf8");
if (actual !== expected) throw new Error("Writing snapshot is stale; run npm run build:writing-snapshot");
console.log("Writing snapshot is current.");
