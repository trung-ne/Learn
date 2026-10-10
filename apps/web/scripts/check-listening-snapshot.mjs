import { readFile } from "node:fs/promises";
import path from "node:path";
import { fileURLToPath } from "node:url";
import { buildListeningSnapshot } from "./build-listening-snapshot.mjs";

const outputPath = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "../src/content/generated/listening-snapshot.json");
const expected = `${JSON.stringify(await buildListeningSnapshot(), null, 2)}\n`;
const actual = await readFile(outputPath, "utf8");

if (actual !== expected) {
  throw new Error("Listening snapshot is stale; run npm run build:listening-snapshot after an intentional source-inventory change.");
}

console.log("Listening Lab snapshot is current.");
