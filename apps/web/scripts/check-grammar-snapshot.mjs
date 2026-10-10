import { buildGrammarSnapshot } from "./build-grammar-snapshot.mjs";
import { readFile } from "node:fs/promises";
import path from "node:path";
import { fileURLToPath } from "node:url";

const scriptDirectory = path.dirname(fileURLToPath(import.meta.url));
const snapshotPath = path.resolve(scriptDirectory, "../src/content/generated/grammar-snapshot.json");
const expected = `${JSON.stringify(await buildGrammarSnapshot(), null, 2)}\n`;
const actual = await readFile(snapshotPath, "utf8");

if (actual !== expected) {
  throw new Error("Grammar snapshot is stale; run npm run build:grammar-snapshot after an explicit source update.");
}

console.log(`Verified deterministic ${JSON.parse(expected).targets.length}-target grammar snapshot.`);
