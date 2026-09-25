import { buildSnapshot } from "./build-content-snapshot.mjs";
import { readFile } from "node:fs/promises";
import path from "node:path";
import { fileURLToPath } from "node:url";

const scriptDirectory = path.dirname(fileURLToPath(import.meta.url));
const snapshotPath = path.resolve(scriptDirectory, "../src/content/generated/curriculum-snapshot.json");
const expected = `${JSON.stringify(await buildSnapshot(), null, 2)}\n`;
const actual = await readFile(snapshotPath, "utf8");

if (actual !== expected) {
  throw new Error("Curriculum snapshot is stale; run npm run build:snapshot after an explicit upstream update.");
}

console.log("Verified deterministic 310-packet curriculum snapshot.");
