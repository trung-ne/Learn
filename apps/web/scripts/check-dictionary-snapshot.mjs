import { buildDictionarySnapshot } from "./build-dictionary-snapshot.mjs";
import { readFile } from "node:fs/promises";
import path from "node:path";
import { fileURLToPath } from "node:url";

const scriptDirectory = path.dirname(fileURLToPath(import.meta.url));
const snapshotPath = path.resolve(scriptDirectory, "../src/content/generated/dictionary-snapshot.json");
const expected = `${JSON.stringify(await buildDictionarySnapshot(), null, 2)}\n`;
const actual = await readFile(snapshotPath, "utf8");
if (actual !== expected) throw new Error("Dictionary snapshot is stale; run npm run build:dictionary-snapshot after an explicit inventory update.");
console.log(`Verified deterministic ${JSON.parse(expected).entries.length}-entry dictionary snapshot.`);
