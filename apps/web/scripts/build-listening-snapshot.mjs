import { createHash } from "node:crypto";
import { mkdir, readFile, writeFile } from "node:fs/promises";
import path from "node:path";
import process from "node:process";
import { fileURLToPath } from "node:url";
import { repositoryRoot } from "./lib/sources.mjs";

const scriptDirectory = path.dirname(fileURLToPath(import.meta.url));
const sourcePath = path.resolve(repositoryRoot, "curriculum/web-listening/v1/inventory.json");
const outputPath = path.resolve(scriptDirectory, "../src/content/generated/listening-snapshot.json");
const fail = (message) => { throw new Error(`Listening snapshot build failed: ${message}`); };
const sha256 = (value) => createHash("sha256").update(value).digest("hex");

function isRecord(value) {
  return Boolean(value) && typeof value === "object" && !Array.isArray(value);
}

function requireString(value, label) {
  if (typeof value !== "string" || !value.trim()) fail(`${label} must be a non-empty string`);
  return value;
}

function hasOnlyFields(value, fields, label) {
  if (Object.keys(value).some((field) => !fields.includes(field))) fail(`${label} has unsupported fields`);
}

function buildNoMediaSnapshot(raw) {
  if (!isRecord(raw)) fail("source inventory must be an object");
  hasOnlyFields(raw, ["schema_version", "inventory_version", "availability", "content_status", "sessions"], "source inventory");
  if (raw.schema_version !== "1.0" || raw.availability !== "NO_AUTHORIZED_MEDIA" || raw.content_status !== "UNREVIEWED" || !Array.isArray(raw.sessions) || raw.sessions.length !== 0) {
    fail("only an empty UNREVIEWED NO_AUTHORIZED_MEDIA inventory may be built until explicit browser-media authorization is added");
  }
  const inventoryVersion = requireString(raw.inventory_version, "source inventory.inventory_version");
  return {
    schemaVersion: "1.0",
    inventoryVersion: `listening-${sha256(inventoryVersion).slice(0, 16)}`,
    availability: "NO_AUTHORIZED_MEDIA",
    sessions: [],
  };
}

export async function buildListeningSnapshot() {
  const raw = JSON.parse(await readFile(sourcePath, "utf8"));
  return buildNoMediaSnapshot(raw);
}

async function main() {
  const snapshot = await buildListeningSnapshot();
  const serialized = `${JSON.stringify(snapshot, null, 2)}\n`;
  if (process.argv.includes("--check")) {
    let current;
    try { current = await readFile(outputPath, "utf8"); } catch { fail("generated listening snapshot is missing; run npm run build:listening-snapshot"); }
    if (current !== serialized) fail("generated listening snapshot is stale; run npm run build:listening-snapshot");
    console.log("Verified deterministic no-authorized-media Listening Lab snapshot.");
  } else {
    await mkdir(path.dirname(outputPath), { recursive: true });
    await writeFile(outputPath, serialized, "utf8");
    console.log("Built deterministic no-authorized-media Listening Lab snapshot.");
  }
}

if (process.argv[1] && path.resolve(process.argv[1]) === fileURLToPath(import.meta.url)) await main();
