import { createHash } from "node:crypto";
import { mkdir, readFile, readdir, writeFile } from "node:fs/promises";
import path from "node:path";
import process from "node:process";
import { fileURLToPath } from "node:url";
import { repositoryRoot, sources } from "./lib/sources.mjs";

const scriptDirectory = path.dirname(fileURLToPath(import.meta.url));
const inventoryDirectory = path.resolve(repositoryRoot, "curriculum/web-reading/v1");
const vocabularyDirectory = path.resolve(repositoryRoot, "curriculum/web-vocabulary/v1");
const outputPath = path.resolve(scriptDirectory, "../src/content/generated/reading-snapshot.json");
const allowedBands = new Set(["A1", "A2", "B1", "C1", "C2"]);
const expectedByMode = new Map([
  ["GRADED_OBJECTIVE", 112],
  ["SUPPLIED_TEXT", 100],
]);

const fail = (message) => { throw new Error(`Reading snapshot build failed: ${message}`); };
const sha256 = (value) => createHash("sha256").update(value).digest("hex");
const canonicalize = (value) => {
  if (Array.isArray(value)) return `[${value.map(canonicalize).join(",")}]`;
  if (value !== null && typeof value === "object") {
    return `{${Object.keys(value).sort().map((key) => `${JSON.stringify(key)}:${canonicalize(value[key])}`).join(",")}}`;
  }
  return JSON.stringify(value);
};
const canonicalHashWithout = (record, identityField) => {
  const projected = { ...record };
  delete projected[identityField];
  return sha256(canonicalize(projected));
};
const requireRecord = (value, label) => {
  if (!value || typeof value !== "object" || Array.isArray(value)) fail(`${label} must be an object`);
  return value;
};
const requireArray = (value, label) => {
  if (!Array.isArray(value)) fail(`${label} must be an array`);
  return value;
};
const requireString = (value, label) => {
  if (typeof value !== "string" || value.trim().length === 0) fail(`${label} must be a non-empty string`);
  return value;
};
const requireStringArray = (value, label) => requireArray(value, label).map((item, index) => requireString(item, `${label}[${index}]`));
const requireSafeId = (value, label) => {
  if (typeof value !== "string" || !/^[a-z][a-z0-9-]*$/u.test(value)) fail(`${label} must be a safe identifier`);
  return value;
};
const requireSha256 = (value, label) => {
  if (typeof value !== "string" || !/^[a-f0-9]{64}$/u.test(value)) fail(`${label} must be a SHA-256 digest`);
  return value;
};
const requireInteger = (value, label) => {
  if (!Number.isInteger(value) || value < 0) fail(`${label} must be a non-negative integer`);
  return value;
};
const hasOnlyFields = (record, allowed, label) => {
  if (Object.keys(record).some((field) => !allowed.has(field))) fail(`${label} contains unsupported fields`);
};
const unique = (values) => new Set(values).size === values.length;

async function loadVocabularySenses() {
  const entries = (await readdir(vocabularyDirectory)).filter((entry) => entry.endsWith(".json")).sort();
  const senses = new Map();
  for (const entry of entries) {
    const batch = requireRecord(JSON.parse(await readFile(path.join(vocabularyDirectory, entry), "utf8")), entry);
    if (batch.schema_version !== "1.0" || batch.content_status !== "UNREVIEWED") fail(`${entry} has unsupported vocabulary metadata`);
    for (const [index, rawSense] of requireArray(batch.records, `${entry}.records`).entries()) {
      const sense = requireRecord(rawSense, `${entry}.records[${index}]`);
      const id = requireSafeId(sense.id, `${entry}.records[${index}].id`);
      if (sense.language !== "en") fail(`${entry}.records[${index}] is not English`);
      if (senses.has(id)) fail(`duplicate vocabulary sense ${id}`);
      senses.set(id, { lemma: requireString(sense.lemma, `${entry}.records[${index}].lemma`) });
    }
  }
  if (senses.size !== 20) fail(`expected the current 20 WordSense records, found ${senses.size}`);
  return senses;
}

async function loadPacketIndex() {
  const selectedSources = sources.filter((source) => source.language === "en" && allowedBands.has(source.band));
  if (selectedSources.length !== allowedBands.size || new Set(selectedSources.map((source) => source.band)).size !== allowedBands.size) {
    fail("English reading source declarations are incomplete or duplicated");
  }

  const packets = new Map();
  for (const source of selectedSources) {
    const manifestPath = path.resolve(repositoryRoot, source.manifest);
    const manifestBytes = await readFile(manifestPath);
    const manifest = requireRecord(JSON.parse(manifestBytes.toString("utf8")), `${source.band} manifest`);
    const expectedSchema = source.band === "A1" ? "2.0" : "1.0";
    if (manifest.record_type !== `${source.band.toLowerCase()}_full_run_manifest` || manifest.schema_version !== expectedSchema ||
      manifest.content_status !== "UNREVIEWED") {
      fail(`${source.manifest} has unsupported manifest metadata`);
    }
    if (canonicalHashWithout(manifest, "manifest_sha256") !== manifest.manifest_sha256) {
      fail(`${source.manifest} canonical manifest hash mismatch`);
    }
    const inventory = requireArray(manifest.inventory, `${source.band} manifest.inventory`);
    const lessonIds = requireArray(manifest.lesson_ids, `${source.band} manifest.lesson_ids`);
    if (inventory.length !== source.expectedCount || lessonIds.length !== source.expectedCount) fail(`${source.band} manifest packet count drifted`);
    const manifestDirectory = path.dirname(manifestPath);
    const inventoryPaths = inventory.map((entry, index) => {
      const item = requireRecord(entry, `${source.band} manifest.inventory[${index}]`);
      const relativePath = requireString(item.path, `${source.band} manifest.inventory[${index}].path`).replaceAll("\\", "/");
      if (!/^packets\/[A-Za-z0-9._-]+\.json$/u.test(relativePath)) fail(`${source.band} manifest contains an unsafe packet path`);
      return relativePath;
    }).sort();
    const packetFiles = (await readdir(path.join(manifestDirectory, "packets")))
      .filter((entry) => entry.endsWith(".json"))
      .map((entry) => `packets/${entry}`)
      .sort();
    if (JSON.stringify(packetFiles) !== JSON.stringify(inventoryPaths)) fail(`${source.band} packet directory is not a closed manifest inventory`);
    for (const [index, rawEntry] of inventory.entries()) {
      const entry = requireRecord(rawEntry, `${source.band} manifest.inventory[${index}]`);
      const relativePath = requireString(entry.path, `${source.band} manifest.inventory[${index}].path`);
      const expectedHash = requireSha256(entry.sha256, `${source.band} manifest.inventory[${index}].sha256`);
      const packetPath = path.resolve(path.dirname(manifestPath), relativePath);
      if (!packetPath.startsWith(`${path.dirname(manifestPath)}${path.sep}`)) fail(`${source.band} manifest contains an unsafe packet path`);
      const bytes = await readFile(packetPath);
      if (sha256(bytes) !== expectedHash) fail(`${source.band} packet hash mismatch for ${relativePath}`);
      const packet = requireRecord(JSON.parse(bytes.toString("utf8")), relativePath);
      if (packet.content_status !== "UNREVIEWED" || canonicalHashWithout(packet, "packet_sha256") !== packet.packet_sha256) {
        fail(`${relativePath} has unsupported metadata or a canonical packet hash mismatch`);
      }
      const lessonId = requireSafeId(packet.lesson_id, `${relativePath}.lesson_id`);
      if (!lessonIds.includes(lessonId)) fail(`${relativePath} lesson identity is absent from its manifest`);
      const key = `${source.band}:${lessonId}:${expectedHash}`;
      if (packets.has(key)) fail(`duplicate current packet binding ${key}`);
      packets.set(key, { source, packet, relativePath });
    }
  }
  return packets;
}

function projectQuestions(exercise, label) {
  const questions = requireArray(exercise.questions, `${label}.questions`).map((rawQuestion, index) => {
    const question = requireRecord(rawQuestion, `${label}.questions[${index}]`);
    const prompt = requireString(question.question, `${label}.questions[${index}].question`);
    const acceptedAnswers = requireStringArray(question.acceptable_answers, `${label}.questions[${index}].acceptable_answers`);
    if (!acceptedAnswers.length || !unique(acceptedAnswers)) fail(`${label}.questions[${index}] has invalid answer data`);
    return { prompt, acceptedAnswers };
  });
  if (!questions.length) fail(`${label} has no supplied objective questions`);
  return questions;
}

function projectOccurrences(rawOccurrences, text, senses, label) {
  if (rawOccurrences === undefined) return undefined;
  const ranges = requireArray(rawOccurrences, `${label}.word_sense_occurrences`).map((rawOccurrence, index) => {
    const occurrenceLabel = `${label}.word_sense_occurrences[${index}]`;
    const occurrence = requireRecord(rawOccurrence, occurrenceLabel);
    hasOnlyFields(occurrence, new Set(["sense_id", "surface", "start", "end"]), occurrenceLabel);
    const senseId = requireSafeId(occurrence.sense_id, `${occurrenceLabel}.sense_id`);
    const sense = senses.get(senseId);
    if (!sense) fail(`${occurrenceLabel} references an unknown WordSense`);
    const surface = requireString(occurrence.surface, `${occurrenceLabel}.surface`);
    const start = requireInteger(occurrence.start, `${occurrenceLabel}.start`);
    const end = requireInteger(occurrence.end, `${occurrenceLabel}.end`);
    if (end <= start || end > text.length || text.slice(start, end) !== surface) fail(`${occurrenceLabel} does not identify an exact source range`);
    if (surface !== sense.lemma) fail(`${occurrenceLabel} is not a literal exact occurrence of its WordSense lemma`);
    if ((start > 0 && /[A-Za-z]/u.test(text[start - 1])) || (end < text.length && /[A-Za-z]/u.test(text[end]))) {
      fail(`${occurrenceLabel} is not a whole-word occurrence`);
    }
    return { start, end, senseId };
  });
  if (!ranges.length) fail(`${label}.word_sense_occurrences must not be empty`);
  ranges.sort((left, right) => left.start - right.start || left.end - right.end || left.senseId.localeCompare(right.senseId));
  for (let index = 1; index < ranges.length; index += 1) {
    if (ranges[index].start < ranges[index - 1].end) fail(`${label} has overlapping WordSense ranges`);
  }
  const identities = ranges.map((range) => `${range.start}:${range.end}:${range.senseId}`);
  if (!unique(identities)) fail(`${label} repeats a WordSense range`);
  return ranges;
}

function projectRecord(rawRecord, index, packets, senses) {
  const label = `reading inventory records[${index}]`;
  const record = requireRecord(rawRecord, label);
  hasOnlyFields(record, new Set([
    "id", "band", "lesson_id", "packet_sha256", "source_kind", "source_id", "capability_labels", "word_sense_occurrences",
  ]), label);
  const id = requireSafeId(record.id, `${label}.id`);
  const band = requireString(record.band, `${label}.band`);
  if (!allowedBands.has(band)) fail(`${label}.band is outside the approved reading scope`);
  const lessonId = requireSafeId(record.lesson_id, `${label}.lesson_id`);
  const packetSha256 = requireSha256(record.packet_sha256, `${label}.packet_sha256`);
  const bound = packets.get(`${band}:${lessonId}:${packetSha256}`);
  if (!bound) fail(`${label} does not bind a declared current packet and hash`);
  const packet = bound.packet;
  const tier = requireString(packet.tier, `${bound.relativePath}.tier`);
  if (!new RegExp(`^${band}\\.[12]$`, "u").test(tier)) fail(`${bound.relativePath}.tier does not belong to ${band}`);
  const title = requireString(packet.title, `${bound.relativePath}.title`);
  const topic = requireString(packet.topic, `${bound.relativePath}.topic`);
  const sourceId = requireSafeId(record.source_id, `${label}.source_id`);
  const sourceKind = requireString(record.source_kind, `${label}.source_kind`);
  let mode;
  let text;
  let questions;
  if (sourceKind === "exercise") {
    if (!["A1", "A2", "B1"].includes(band)) fail(`${label} uses an exercise outside A1-B1`);
    const matches = requireArray(packet.exercises, `${bound.relativePath}.exercises`)
      .filter((exercise) => exercise && exercise.id === sourceId);
    if (matches.length !== 1 || matches[0].type !== "reading") fail(`${label} does not bind one reading exercise`);
    const exercise = matches[0];
    if (exercise.media_required !== false) fail(`${label} reading exercise requires media`);
    text = requireString(exercise.stimulus, `${label} source stimulus`);
    questions = projectQuestions(exercise, `${label} source exercise`);
    mode = "GRADED_OBJECTIVE";
  } else if (sourceKind === "section") {
    if (!["C1", "C2"].includes(band)) fail(`${label} uses a section outside C1-C2`);
    const matches = requireArray(packet.content_sections, `${bound.relativePath}.content_sections`)
      .filter((section) => section && section.id === sourceId);
    if (matches.length !== 1 || matches[0].section_type !== "reading") fail(`${label} does not bind one reading section`);
    text = requireString(matches[0].body, `${label} source body`);
    mode = "SUPPLIED_TEXT";
  } else {
    fail(`${label}.source_kind is unsupported`);
  }
  const capabilityLabels = record.capability_labels === undefined
    ? undefined
    : requireStringArray(record.capability_labels, `${label}.capability_labels`);
  if (capabilityLabels && (!capabilityLabels.length || !unique(capabilityLabels))) fail(`${label}.capability_labels is invalid`);
  const ranges = projectOccurrences(record.word_sense_occurrences, text, senses, label);
  return {
    id,
    band,
    tier,
    title,
    topic,
    mode,
    sourceText: text,
    ...(questions ? { questions } : {}),
    ...(ranges ? { wordSenseRanges: ranges } : {}),
    ...(capabilityLabels ? { capabilityLabels } : {}),
    contentStatus: "UNREVIEWED",
  };
}

export async function buildReadingSnapshot() {
  const [packets, senses] = await Promise.all([loadPacketIndex(), loadVocabularySenses()]);
  const entries = (await readdir(inventoryDirectory)).filter((entry) => entry.endsWith(".json")).sort();
  if (entries.length !== 1) fail("expected exactly one reading input mapping file");
  const input = requireRecord(JSON.parse(await readFile(path.join(inventoryDirectory, entries[0]), "utf8")), entries[0]);
  hasOnlyFields(input, new Set(["schema_version", "inventory_version", "content_status", "records"]), entries[0]);
  if (input.schema_version !== "1.0" || input.content_status !== "UNREVIEWED") fail(`${entries[0]} has unsupported metadata`);
  const inventoryVersion = requireString(input.inventory_version, `${entries[0]}.inventory_version`);
  const readers = requireArray(input.records, `${entries[0]}.records`).map((record, index) => projectRecord(record, index, packets, senses));
  readers.sort((left, right) => left.band.localeCompare(right.band) || left.id.localeCompare(right.id));
  if (!unique(readers.map((reader) => reader.id))) fail("reading inventory contains duplicate reader IDs");
  for (const [mode, expected] of expectedByMode) {
    const actual = readers.filter((reader) => reader.mode === mode).length;
    if (actual !== expected) fail(`expected ${expected} ${mode} readers, found ${actual}`);
  }
  if (readers.length !== 212) fail(`expected 212 readers, found ${readers.length}`);
  return { schemaVersion: "1.0", inventoryVersion, readers };
}

async function main() {
  const snapshot = await buildReadingSnapshot();
  const serialized = `${JSON.stringify(snapshot, null, 2)}\n`;
  if (process.argv.includes("--check")) {
    let current;
    try { current = await readFile(outputPath, "utf8"); } catch { fail("generated reading snapshot is missing; run npm run build:reading-snapshot"); }
    if (current !== serialized) fail("generated reading snapshot is stale; run npm run build:reading-snapshot");
    console.log(`Verified deterministic ${snapshot.readers.length}-reader reading snapshot.`);
  } else {
    await mkdir(path.dirname(outputPath), { recursive: true });
    await writeFile(outputPath, serialized, "utf8");
    console.log(`Built deterministic ${snapshot.readers.length}-reader reading snapshot.`);
  }
}

if (process.argv[1] && path.resolve(process.argv[1]) === fileURLToPath(import.meta.url)) await main();
