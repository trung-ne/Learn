import { mkdir, readFile, readdir, writeFile } from "node:fs/promises";
import path from "node:path";
import process from "node:process";
import { fileURLToPath } from "node:url";
import { repositoryRoot } from "./lib/sources.mjs";

const scriptDirectory = path.dirname(fileURLToPath(import.meta.url));
const inventoryDirectory = path.resolve(repositoryRoot, "curriculum/web-dictionary/v1");
const outputPath = path.resolve(scriptDirectory, "../src/content/generated/dictionary-snapshot.json");
const bands = new Set(["A1", "A2", "B1", "B2", "C1", "C2"]);
const kinds = new Set(["word_sense", "phrasal_verb", "word_form"]);
const relationKeys = ["sense_ids", "phrasal_verb_ids", "word_family_ids"];

const fail = (message) => { throw new Error(`Dictionary snapshot build failed: ${message}`); };
const isRecord = (value) => Boolean(value) && typeof value === "object" && !Array.isArray(value);
const requireRecord = (value, label) => { if (!isRecord(value)) fail(`${label} must be an object`); return value; };
const requireString = (value, label) => { if (typeof value !== "string" || value.trim() !== value || !value || value.length > 400) fail(`${label} must be a bounded non-empty string`); return value; };
const requireArray = (value, label) => { if (!Array.isArray(value)) fail(`${label} must be an array`); return value; };
const requireStringArray = (value, label) => {
  const values = requireArray(value, label).map((item, index) => requireString(item, `${label}[${index}]`));
  if (!values.length || new Set(values).size !== values.length) fail(`${label} must be a non-empty unique string array`);
  return values;
};
const requireSafeId = (value, label) => { if (typeof value !== "string" || !/^[a-z][a-z0-9-]*$/u.test(value)) fail(`${label} must be a safe identifier`); return value; };
const requireRelationArray = (value, label) => {
  const values = requireArray(value, label).map((item, index) => requireSafeId(item, `${label}[${index}]`));
  if (new Set(values).size !== values.length) fail(`${label} must contain unique identifiers`);
  return values;
};
const optionalString = (value, label) => value === undefined ? undefined : requireString(value, label);

function projectRecord(record, label) {
  requireRecord(record, label);
  const allowed = new Set(["id", "language", "kind", "headword", "sense_number", "band", "tier", "part_of_speech", "definition", "vietnamese_meaning", "ipa", "examples", "collocations", "relations", "recall", "authorship", "content_status"]);
  if (Object.keys(record).some((key) => !allowed.has(key))) fail(`${label} contains unsupported fields`);
  const id = requireSafeId(record.id, `${label}.id`);
  if (record.language !== "en") fail(`${label}.language must be en`);
  if (!kinds.has(record.kind)) fail(`${label}.kind is unsupported`);
  const band = requireString(record.band, `${label}.band`);
  if (!bands.has(band)) fail(`${label}.band is unsupported`);
  const tier = requireString(record.tier, `${label}.tier`);
  if (!new RegExp(`^${band}\\.[12]$`, "u").test(tier)) fail(`${label}.tier must belong to its band`);
  const kind = record.kind;
  const senseNumber = record.sense_number;
  if (kind === "word_sense" && (!Number.isInteger(senseNumber) || senseNumber < 1)) fail(`${label}.sense_number must be positive for a word sense`);
  if (kind !== "word_sense" && senseNumber !== undefined) fail(`${label}.sense_number is only allowed for a word sense`);
  const relations = requireRecord(record.relations, `${label}.relations`);
  if (Object.keys(relations).length !== relationKeys.length || relationKeys.some((key) => !(key in relations))) fail(`${label}.relations has unsupported or missing fields`);
  const projectedRelations = Object.fromEntries(relationKeys.map((key) => [key, requireRelationArray(relations[key], `${label}.relations.${key}`)]));
  const recall = requireRecord(record.recall, `${label}.recall`);
  if (Object.keys(recall).some((key) => !["prompt", "accepted_answers", "distractors"].includes(key))) fail(`${label}.recall contains unsupported fields`);
  const acceptedAnswers = requireStringArray(recall.accepted_answers, `${label}.recall.accepted_answers`);
  const distractors = requireStringArray(recall.distractors, `${label}.recall.distractors`);
  if (distractors.length < 2 || distractors.some((item) => acceptedAnswers.includes(item))) fail(`${label}.recall has invalid distractors`);
  if (record.authorship !== "PROJECT_AUTHORED" || record.content_status !== "UNREVIEWED") fail(`${label} must be original authored and unreviewed`);
  return {
    id,
    language: "en",
    kind,
    headword: requireString(record.headword, `${label}.headword`),
    ...(kind === "word_sense" ? { senseNumber } : {}),
    band,
    tier,
    partOfSpeech: requireString(record.part_of_speech, `${label}.part_of_speech`),
    definition: requireString(record.definition, `${label}.definition`),
    ...(optionalString(record.vietnamese_meaning, `${label}.vietnamese_meaning`) ? { vietnameseMeaning: record.vietnamese_meaning } : {}),
    ...(optionalString(record.ipa, `${label}.ipa`) ? { ipa: record.ipa } : {}),
    examples: requireStringArray(record.examples, `${label}.examples`),
    collocations: requireStringArray(record.collocations, `${label}.collocations`),
    relations: { senseIds: projectedRelations.sense_ids, phrasalVerbIds: projectedRelations.phrasal_verb_ids, wordFamilyIds: projectedRelations.word_family_ids },
    recall: { prompt: requireString(recall.prompt, `${label}.recall.prompt`), acceptedAnswers, distractors },
    contentStatus: "UNREVIEWED",
  };
}

export async function buildDictionarySnapshot() {
  const files = (await readdir(inventoryDirectory)).filter((name) => name.endsWith(".json")).sort();
  if (!files.length) fail("no dictionary inventory batches were found");
  const entries = [];
  const versions = [];
  const ids = new Set();
  const identities = new Set();
  for (const file of files) {
    const source = requireRecord(JSON.parse(await readFile(path.join(inventoryDirectory, file), "utf8")), file);
    if (source.schema_version !== "1.0" || source.content_status !== "UNREVIEWED") fail(`${file} has unsupported metadata`);
    versions.push(requireString(source.inventory_version, `${file}.inventory_version`));
    for (const [index, record] of requireArray(source.records, `${file}.records`).entries()) {
      const entry = projectRecord(record, `${file}.records[${index}]`);
      const identity = `${entry.kind}\u0000${entry.headword}\u0000${entry.senseNumber ?? ""}`;
      if (ids.has(entry.id) || identities.has(identity)) fail(`${file} has a duplicate entry identity`);
      ids.add(entry.id); identities.add(identity); entries.push(entry);
    }
  }
  for (const entry of entries) {
    for (const [relation, linkedIds] of Object.entries(entry.relations)) {
      for (const linkedId of linkedIds) {
        if (!ids.has(linkedId)) fail(`${entry.id}.${relation} has an unresolved reference`);
      }
    }
  }
  entries.sort((left, right) => left.headword.localeCompare(right.headword) || (left.senseNumber ?? 0) - (right.senseNumber ?? 0) || left.id.localeCompare(right.id));
  return { schemaVersion: "1.0", inventoryVersion: versions.join("+"), entries };
}

async function main() {
  const snapshot = await buildDictionarySnapshot();
  const serialized = `${JSON.stringify(snapshot, null, 2)}\n`;
  if (process.argv.includes("--check")) {
    let current;
    try { current = await readFile(outputPath, "utf8"); } catch { fail("generated dictionary snapshot is missing; run npm run build:dictionary-snapshot"); }
    if (current !== serialized) fail("generated dictionary snapshot is stale; run npm run build:dictionary-snapshot");
    console.log(`Verified deterministic ${snapshot.entries.length}-entry dictionary snapshot.`);
  } else {
    await mkdir(path.dirname(outputPath), { recursive: true });
    await writeFile(outputPath, serialized, "utf8");
    console.log(`Built deterministic ${snapshot.entries.length}-entry dictionary snapshot.`);
  }
}

if (process.argv[1] && path.resolve(process.argv[1]) === fileURLToPath(import.meta.url)) await main();
