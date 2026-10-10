import { createHash } from "node:crypto";
import { mkdir, readFile, writeFile } from "node:fs/promises";
import path from "node:path";
import process from "node:process";
import { fileURLToPath } from "node:url";
import { repositoryRoot, sources } from "./lib/sources.mjs";

const scriptDirectory = path.dirname(fileURLToPath(import.meta.url));
const outputPath = path.resolve(scriptDirectory, "../src/content/generated/speaking-snapshot.json");
const bands = new Set(["A1", "A2", "B1", "B2", "C1", "C2"]);
const allowedLanguages = new Set(["en", "de"]);
const assessmentDimensions = ["overall", "grammar", "vocabulary", "fluency", "pronunciation", "coherence", "appropriacy"];

const fail = (message) => { throw new Error(`Speaking snapshot build failed: ${message}`); };
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
const requireTier = (value, source, label) => {
  const tier = requireString(value, label);
  if (!new RegExp(`^${source.band}\\.[12]$`, "u").test(tier)) fail(`${label} does not belong to ${source.band}`);
  return tier;
};

function protocolId(language, lessonId) {
  return `speaking-${language}-${sha256(`${language}:${lessonId}`).slice(0, 20)}`;
}

function notAssessed() {
  return Object.fromEntries(assessmentDimensions.map((dimension) => [dimension, "NOT_ASSESSED"]));
}

function projectProtocol(packet, source, label) {
  const lessonId = requireSafeId(packet.lesson_id, `${label}.lesson_id`);
  const isGerman = source.language === "de";
  const protocol = isGerman
    ? (() => {
      if (packet.language_code !== "de") fail(`${label}.language_code must be de`);
      const matches = requireArray(packet.prompts, `${label}.prompts`).filter((prompt) => {
        requireRecord(prompt, `${label}.prompt`);
        return prompt.modality === "speaking";
      });
      if (matches.length !== 1) fail(`${label}.prompts must contain exactly one speaking protocol`);
      return requireRecord(matches[0], `${label}.prompts.speaking`);
    })()
    : (() => {
      requireRecord(packet.practice, `${label}.practice`);
      return requireRecord(packet.practice.speaking, `${label}.practice.speaking`);
    })();
  const protocolLabel = `${label}.${isGerman ? "prompts.speaking" : "practice.speaking"}`;
  const unitId = isGerman
    ? (() => {
      const unitMatch = lessonId.match(/^(.*)-l\d+$/u);
      if (!unitMatch) fail(`${label}.lesson_id does not identify a unit`);
      return requireSafeId(unitMatch[1], `${label}.unit_id`);
    })()
    : requireSafeId(packet.unit_id, `${label}.unit_id`);
  const projected = {
    id: protocolId(source.language, lessonId),
    language: source.language,
    band: source.band,
    tier: requireTier(packet.tier, source, `${label}.tier`),
    unitId,
    lessonId,
    title: requireString(packet.title, `${label}.title`),
    topic: isGerman ? requireString(packet.title, `${label}.title`) : requireString(packet.topic, `${label}.topic`),
    instruction: requireString(protocol.instruction, `${protocolLabel}.instruction`),
    assessment: notAssessed(),
    contentStatus: "UNREVIEWED",
  };
  if (isGerman) {
    projected.checklist = requireStringArray(protocol.checklist, `${protocolLabel}.checklist`);
  } else {
    projected.goal = requireString(protocol.goal, `${protocolLabel}.goal`);
    projected.constraints = requireStringArray(protocol.constraints, `${protocolLabel}.constraints`);
  }
  return projected;
}

async function loadSourceProtocols(source) {
  if (!allowedLanguages.has(source.language) || !bands.has(source.band) || !Number.isInteger(source.expectedCount) || source.expectedCount < 1) {
    fail("source inventory contains an unsupported language, band, or count");
  }
  const manifestPath = path.resolve(repositoryRoot, source.manifest);
  const manifest = requireRecord(JSON.parse(await readFile(manifestPath, "utf8")), `${source.band} manifest`);
  if (manifest.content_status !== "UNREVIEWED") fail(`${source.manifest} is not UNREVIEWED`);
  const inventory = requireArray(manifest.inventory, `${source.band} manifest inventory`);
  if (inventory.length !== source.expectedCount) fail(`${source.band} manifest count drifted`);
  const protocols = [];
  const lessonIds = new Set();
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

export async function buildSpeakingSnapshot() {
  const expectedEnglishBands = sources.filter((source) => source.language === "en").map((source) => source.band);
  if (expectedEnglishBands.length !== bands.size || new Set(expectedEnglishBands).size !== bands.size) {
    fail("English speaking source inventory is incomplete");
  }
  const protocols = (await Promise.all(sources.map(loadSourceProtocols))).flat();
  const ids = new Set();
  for (const protocol of protocols) {
    if (ids.has(protocol.id)) fail(`duplicate speaking protocol identity ${protocol.id}`);
    ids.add(protocol.id);
  }
  protocols.sort((left, right) => left.language.localeCompare(right.language) || left.band.localeCompare(right.band) || left.lessonId.localeCompare(right.lessonId));
  return {
    schemaVersion: "1.0",
    inventoryVersion: `speaking-${sha256(JSON.stringify(protocols)).slice(0, 16)}`,
    protocols,
  };
}

async function main() {
  const snapshot = await buildSpeakingSnapshot();
  const serialized = `${JSON.stringify(snapshot, null, 2)}\n`;
  if (process.argv.includes("--check")) {
    let current;
    try { current = await readFile(outputPath, "utf8"); } catch { fail("generated speaking snapshot is missing; run npm run build:speaking-snapshot"); }
    if (current !== serialized) fail("generated speaking snapshot is stale; run npm run build:speaking-snapshot");
    console.log(`Verified deterministic ${snapshot.protocols.length}-protocol speaking snapshot.`);
  } else {
    await mkdir(path.dirname(outputPath), { recursive: true });
    await writeFile(outputPath, serialized, "utf8");
    console.log(`Built deterministic ${snapshot.protocols.length}-protocol speaking snapshot.`);
  }
}

if (process.argv[1] && path.resolve(process.argv[1]) === fileURLToPath(import.meta.url)) await main();
