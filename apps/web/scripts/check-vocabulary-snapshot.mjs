import { buildVocabularySnapshot } from "./build-vocabulary-snapshot.mjs";
import { readFile } from "node:fs/promises";
import path from "node:path";
import { fileURLToPath } from "node:url";

const scriptDirectory = path.dirname(fileURLToPath(import.meta.url));
const snapshotPath = path.resolve(scriptDirectory, "../src/content/generated/vocabulary-snapshot.json");
const expected = `${JSON.stringify(await buildVocabularySnapshot(), null, 2)}\n`;
const actual = await readFile(snapshotPath, "utf8");

if (actual !== expected) {
  throw new Error("Vocabulary snapshot is stale; run npm run build:vocabulary-snapshot after an explicit inventory update.");
}

console.log(`Verified deterministic ${JSON.parse(expected).senses.length}-sense vocabulary snapshot.`);
