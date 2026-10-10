import { createHash } from "node:crypto";
import { mkdir, readFile, writeFile } from "node:fs/promises";
import path from "node:path";
import process from "node:process";
import { fileURLToPath } from "node:url";
import { repositoryRoot, sources } from "./lib/sources.mjs";

const scriptDirectory = path.dirname(fileURLToPath(import.meta.url));
const outputPath = path.resolve(scriptDirectory, "../src/content/generated/writing-snapshot.json");
const bands = ["A1", "A2", "B1", "B2", "C1", "C2"];
const fail = (message) => { throw new Error(`Writing snapshot build failed: ${message}`); };
const sha256 = (value) => createHash("sha256").update(value).digest("hex");
const requireRecord = (value, label) => {
  if (!value || typeof value !== "object" || Array.isArray(value)) fail(`${label} must be an object`);
  return value;
};
const requireArray = (value, label) => {
  if (!Array.isArray(value)) fail(`${label} must be an array`);
  return value;
};
const requireString = (value, label) => {
  if (typeof value !== "string" || !value.trim()) fail(`${label} must be a non-empty string`);
  return value;
};
const requireStringArray = (value, label) => {
  const items = requireArray(value, label).map((item, index) => requireString(item, `${label}[${index}]`));
  if (!items.length || new Set(items).size !== items.length) fail(`${label} must be a non-empty unique string array`);
  return items;
};
const requireSafeId = (value, label) => {
  if (typeof value !== "string" || !/^[a-z][a-z0-9-]*$/u.test(value)) fail(`${label} must be a safe identifier`);
  return value;
};

function protocolId(lessonId) {
  return `writing-en-${sha256(`en:${lessonId}`).slice(0, 20)}`;
}

function projectProtocol(packet, source, label) {
  const lessonId = requireSafeId(packet.lesson_id, `${label}.lesson_id`);
  const unitId = requireSafeId(packet.unit_id, `${label}.unit_id`);
  const tier = requireString(packet.tier, `${label}.tier`);
  if (!new RegExp(`^${source.band}\\.[12]$`, "u").test(tier)) fail(`${label}.tier does not belong to ${source.band}`);
  const practice = requireRecord(packet.practice, `${label}.practice`);
  const protocol = requireRecord(practice.writing, `${label}.practice.writing`);
  if (protocol.feedback_boundary !== "FEEDBACK_ONLY_NO_REPLACEMENT") {
    fail(`${label}.practice.writing.feedback_boundary must be FEEDBACK_ONLY_NO_REPLACEMENT`);
  }
  return {
    id: protocolId(lessonId),
    language: "en",
    band: source.band,
    tier,
    unitId,
    lessonId,
    title: requireString(packet.title, `${label}.title`),
    topic: requireString(packet.topic, `${label}.topic`),
    goal: requireString(protocol.goal, `${label}.practice.writing.goal`),
    instruction: requireString(protocol.instruction, `${label}.practice.writing.instruction`),
    constraints: requireStringArray(protocol.constraints, `${label}.practice.writing.constraints`),
    feedbackBoundary: "FEEDBACK_ONLY_NO_REPLACEMENT",
    contentStatus: "UNREVIEWED",
  };
}

async function loadSourceProtocols(source) {
  if (source.language !== "en" || !bands.includes(source.band) || source.expectedCount !== 50) {
    fail("source inventory contains an unsupported writing source");
  }
  const manifestPath = path.resolve(repositoryRoot, source.manifest);
  const manifest = requireRecord(JSON.parse(await readFile(manifestPath, "utf8")), `${source.band} manifest`);
  if (manifest.content_status !== "UNREVIEWED") fail(`${source.manifest} is not UNREVIEWED`);
  const inventory = requireArray(manifest.inventory, `${source.band} manifest inventory`);
  if (inventory.length !== source.expectedCount) fail(`${source.band} manifest count drifted`);
  const lessonIds = new Set();
  const protocols = [];
  for (const [index, record] of inventory.entries()) {
    requireRecord(record, `${source.band} manifest inventory ${index}`);
    const relativePath = requireString(record.path, `${source.band} manifest inventory ${index}.path`).replaceAll("\\", "/");
    if (!/^packets\/[A-Za-z0-9._-]+\.json$/u.test(relativePath)) fail(`${source.band} manifest contains an unsafe packet path`);
    const expectedHash = requireString(record.sha256, `${source.band} manifest inventory ${index}.sha256`);
    if (!/^[a-f0-9]{64}$/u.test(expectedHash)) fail(`${source.band} manifest contains an invalid packet hash`);
    const packetPath = path.resolve(path.dirname(manifestPath), relativePath);
    const packetBytes = await readFile(packetPath);
    if (sha256(packetBytes) !== expectedHash) fail(`${source.band} packet hash mismatch for ${relativePath}`);
    const packet = requireRecord(JSON.parse(packetBytes.toString("utf8")), `${source.band} packet ${relativePath}`);
    if (packet.content_status !== "UNREVIEWED") fail(`${source.band} packet ${relativePath} is not UNREVIEWED`);
    const lessonId = requireSafeId(packet.lesson_id, `${source.band} packet ${relativePath}.lesson_id`);
    if (lessonIds.has(lessonId)) fail(`${source.band} manifest repeats lesson ${lessonId}`);
    lessonIds.add(lessonId);
    protocols.push(projectProtocol(packet, source, `${source.band} packet ${relativePath}`));
  }
  return protocols;
}

export async function buildWritingSnapshot() {
  const englishSources = sources.filter((source) => source.language === "en");
  if (englishSources.length !== bands.length || new Set(englishSources.map((source) => source.band)).size !== bands.length) {
    fail("English writing source inventory is incomplete");
  }
  const protocols = (await Promise.all(englishSources.map(loadSourceProtocols))).flat();
  if (protocols.length !== 300) fail("writing inventory must contain exactly 300 protocols");
  const ids = new Set();
  const lessonIds = new Set();
  for (const protocol of protocols) {
    if (ids.has(protocol.id) || lessonIds.has(protocol.lessonId)) fail(`duplicate writing protocol identity ${protocol.id}`);
    ids.add(protocol.id);
    lessonIds.add(protocol.lessonId);
  }
  for (const band of bands) {
    if (protocols.filter((protocol) => protocol.band === band).length !== 50) fail(`${band} writing inventory must contain exactly 50 protocols`);
  }
  protocols.sort((left, right) => left.band.localeCompare(right.band) || left.lessonId.localeCompare(right.lessonId));
  return {
    schemaVersion: "1.0",
    inventoryVersion: `writing-${sha256(JSON.stringify(protocols)).slice(0, 16)}`,
    protocols,
  };
}

async function main() {
  const snapshot = await buildWritingSnapshot();
  const serialized = `${JSON.stringify(snapshot, null, 2)}\n`;
  if (process.argv.includes("--check")) {
    let current;
    try { current = await readFile(outputPath, "utf8"); } catch { fail("generated writing snapshot is missing; run npm run build:writing-snapshot"); }
    if (current !== serialized) fail("generated writing snapshot is stale; run npm run build:writing-snapshot");
    console.log(`Verified deterministic ${snapshot.protocols.length}-protocol writing snapshot.`);
  } else {
    await mkdir(path.dirname(outputPath), { recursive: true });
    await writeFile(outputPath, serialized, "utf8");
    console.log(`Built deterministic ${snapshot.protocols.length}-protocol writing snapshot.`);
  }
}

if (process.argv[1] && path.resolve(process.argv[1]) === fileURLToPath(import.meta.url)) await main();
