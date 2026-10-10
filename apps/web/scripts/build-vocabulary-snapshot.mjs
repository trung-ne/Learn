import { createHash } from "node:crypto";
import { mkdir, readFile, readdir, writeFile } from "node:fs/promises";
import path from "node:path";
import process from "node:process";
import { fileURLToPath } from "node:url";
import { repositoryRoot, sources } from "./lib/sources.mjs";

const scriptDirectory = path.dirname(fileURLToPath(import.meta.url));
const inventoryDirectory = path.resolve(repositoryRoot, "curriculum/web-vocabulary/v1");
const outputPath = path.resolve(scriptDirectory, "../src/content/generated/vocabulary-snapshot.json");
const objectiveExerciseTypes = new Set([
  "multiple_choice", "fill_blank", "selection", "completion", "matching", "ordering", "reading", "listening",
]);
const bands = new Set(["A1", "A2", "B1", "B2", "C1", "C2"]);

const fail = (message) => { throw new Error(`Vocabulary snapshot build failed: ${message}`); };
const sha256 = (value) => createHash("sha256").update(value).digest("hex");
const requireRecord = (value, label) => {
  if (!value || typeof value !== "object" || Array.isArray(value)) fail(`${label} must be an object`);
  return value;
};
const requireString = (value, label) => {
  if (typeof value !== "string" || value.trim().length === 0) fail(`${label} must be a non-empty string`);
  return value;
};
const requireArray = (value, label) => {
  if (!Array.isArray(value)) fail(`${label} must be an array`);
  return value;
};
const requireStringArray = (value, label) => requireArray(value, label).map((item, index) => requireString(item, `${label}[${index}]`));
const isSafeId = (value) => typeof value === "string" && /^[a-z][a-z0-9-]*$/u.test(value);
const requireSafeId = (value, label) => {
  if (!isSafeId(value)) fail(`${label} must be a safe identifier`);
  return value;
};
const requireTargetId = (value, label) => {
  if (typeof value !== "string" || !/^[a-z][a-z0-9_]*$/u.test(value)) fail(`${label} must be a safe source target identifier`);
  return value;
};
const optionalString = (value, label) => value === undefined ? undefined : requireString(value, label);
const unique = (values) => new Set(values).size === values.length;

function learnerRecord(record, label, packetIndex) {
  requireRecord(record, label);
  const allowed = new Set([
    "id", "language", "band", "tier", "lemma", "sense_number", "part_of_speech", "definition", "vietnamese_meaning", "ipa",
    "examples", "collocations", "introduction_lesson_id", "recall_prompt", "accepted_answers", "distractors", "exercise_bindings", "content_status",
  ]);
  if (Object.keys(record).some((key) => !allowed.has(key))) fail(`${label} contains unsupported fields`);
  const id = requireSafeId(record.id, `${label}.id`);
  if (record.language !== "en") fail(`${label}.language must be en`);
  const band = requireString(record.band, `${label}.band`);
  if (!bands.has(band)) fail(`${label}.band is unsupported`);
  const tier = requireString(record.tier, `${label}.tier`);
  if (!new RegExp(`^${band}\\.[12]$`, "u").test(tier)) fail(`${label}.tier must belong to its band`);
  if (!Number.isInteger(record.sense_number) || record.sense_number < 1) fail(`${label}.sense_number must be positive`);
  const acceptedAnswers = requireStringArray(record.accepted_answers, `${label}.accepted_answers`);
  const distractors = requireStringArray(record.distractors, `${label}.distractors`);
  if (!acceptedAnswers.length || distractors.length < 2 || !unique(acceptedAnswers) || !unique(distractors) ||
    distractors.some((item) => acceptedAnswers.includes(item))) {
    fail(`${label} has invalid answer or distractor data`);
  }
  if (record.content_status !== "UNREVIEWED") fail(`${label}.content_status must be UNREVIEWED`);
  const introductionLessonId = requireSafeId(record.introduction_lesson_id, `${label}.introduction_lesson_id`);
  const bindings = requireArray(record.exercise_bindings, `${label}.exercise_bindings`);
  if (!bindings.length) fail(`${label}.exercise_bindings must not be empty`);
  const projectedBindings = bindings.map((binding, index) => {
    const bindingLabel = `${label}.exercise_bindings[${index}]`;
    requireRecord(binding, bindingLabel);
    const allowedBinding = new Set(["lesson_id", "exercise_id", "source_target_id", "packet_sha256"]);
    if (Object.keys(binding).some((key) => !allowedBinding.has(key))) fail(`${bindingLabel} contains unsupported fields`);
    const lessonId = requireSafeId(binding.lesson_id, `${bindingLabel}.lesson_id`);
    const exerciseId = requireSafeId(binding.exercise_id, `${bindingLabel}.exercise_id`);
    const targetId = requireTargetId(binding.source_target_id, `${bindingLabel}.source_target_id`);
    const packetSha256 = requireString(binding.packet_sha256, `${bindingLabel}.packet_sha256`);
    if (!/^[a-f0-9]{64}$/u.test(packetSha256)) fail(`${bindingLabel}.packet_sha256 is invalid`);
    const packet = packetIndex.get(`${lessonId}:${packetSha256}`);
    if (!packet) fail(`${bindingLabel} does not bind a current immutable packet`);
    const exercise = packet.exercises.get(exerciseId);
    if (!exercise || !objectiveExerciseTypes.has(exercise.type)) fail(`${bindingLabel} does not reference an objective exercise`);
    if (!exercise.targetIds.includes(targetId)) fail(`${bindingLabel} target anchor does not match its exercise`);
    return { lessonId, exerciseId };
  });
  const identity = `${record.lemma}\u0000${record.part_of_speech}\u0000${record.sense_number}`;
  return {
    identity,
    sense: {
      id,
      language: "en",
      band,
      tier,
      lemma: requireString(record.lemma, `${label}.lemma`),
      senseNumber: record.sense_number,
      partOfSpeech: requireString(record.part_of_speech, `${label}.part_of_speech`),
      definition: requireString(record.definition, `${label}.definition`),
      ...(optionalString(record.vietnamese_meaning, `${label}.vietnamese_meaning`) ? { vietnameseMeaning: record.vietnamese_meaning } : {}),
      ...(optionalString(record.ipa, `${label}.ipa`) ? { ipa: record.ipa } : {}),
      examples: requireStringArray(record.examples, `${label}.examples`),
      collocations: requireStringArray(record.collocations, `${label}.collocations`),
      introductionLessonId,
      recallPrompt: requireString(record.recall_prompt, `${label}.recall_prompt`),
      acceptedAnswers,
      distractors,
      exerciseBindings: projectedBindings,
      contentStatus: "UNREVIEWED",
    },
  };
}

async function loadPacketIndex() {
  const index = new Map();
  for (const source of sources.filter((item) => item.language === "en")) {
    const manifestPath = path.resolve(repositoryRoot, source.manifest);
    const manifest = JSON.parse(await readFile(manifestPath, "utf8"));
    if (manifest.content_status !== "UNREVIEWED" || !Array.isArray(manifest.inventory)) {
      fail(`${source.manifest} is not a supported unreviewed manifest`);
    }
    for (const record of manifest.inventory) {
      const packetPath = path.resolve(path.dirname(manifestPath), requireString(record.path, "manifest inventory path"));
      const bytes = await readFile(packetPath);
      const packetSha256 = requireString(record.sha256, `manifest hash for ${record.path}`);
      if (sha256(bytes) !== packetSha256) fail(`hash mismatch for ${record.path}`);
      const packet = JSON.parse(bytes.toString("utf8"));
      if (packet.content_status !== "UNREVIEWED") fail(`${record.path} is not UNREVIEWED`);
      const lessonId = requireSafeId(packet.lesson_id, `${record.path}.lesson_id`);
      const exercises = new Map();
      for (const exercise of requireArray(packet.exercises ?? [], `${record.path}.exercises`)) {
        exercises.set(requireSafeId(exercise.id, `${record.path}.exercise.id`), {
          type: requireString(exercise.type, `${record.path}.exercise.type`),
          targetIds: requireStringArray(exercise.target_ids ?? [], `${record.path}.exercise.target_ids`),
        });
      }
      index.set(`${lessonId}:${packetSha256}`, { exercises });
    }
  }
  return index;
}

export async function buildVocabularySnapshot() {
  const packetIndex = await loadPacketIndex();
  const entries = (await readdir(inventoryDirectory)).filter((entry) => entry.endsWith(".json")).sort();
  if (!entries.length) fail("no vocabulary inventory batches were found");
  const senses = [];
  const seenIds = new Set();
  const seenIdentities = new Set();
  const versions = [];
  for (const entry of entries) {
    const source = JSON.parse(await readFile(path.join(inventoryDirectory, entry), "utf8"));
    requireRecord(source, entry);
    if (source.schema_version !== "1.0" || source.content_status !== "UNREVIEWED") fail(`${entry} has unsupported metadata`);
    const inventoryVersion = requireString(source.inventory_version, `${entry}.inventory_version`);
    versions.push(inventoryVersion);
    for (const [index, record] of requireArray(source.records, `${entry}.records`).entries()) {
      const projected = learnerRecord(record, `${entry}.records[${index}]`, packetIndex);
      if (seenIds.has(projected.sense.id) || seenIdentities.has(projected.identity)) fail(`${entry} contains a duplicate WordSense`);
      seenIds.add(projected.sense.id);
      seenIdentities.add(projected.identity);
      senses.push(projected.sense);
    }
  }
  senses.sort((left, right) => left.band.localeCompare(right.band) || left.introductionLessonId.localeCompare(right.introductionLessonId) || left.id.localeCompare(right.id));
  return { schemaVersion: "1.0", inventoryVersion: versions.join("+"), senses };
}

async function main() {
  const snapshot = await buildVocabularySnapshot();
  const serialized = `${JSON.stringify(snapshot, null, 2)}\n`;
  if (process.argv.includes("--check")) {
    let current;
    try { current = await readFile(outputPath, "utf8"); } catch { fail("generated vocabulary snapshot is missing; run npm run build:vocabulary-snapshot"); }
    if (current !== serialized) fail("generated vocabulary snapshot is stale; run npm run build:vocabulary-snapshot");
    console.log(`Verified deterministic ${snapshot.senses.length}-sense vocabulary snapshot.`);
  } else {
    await mkdir(path.dirname(outputPath), { recursive: true });
    await writeFile(outputPath, serialized, "utf8");
    console.log(`Built deterministic ${snapshot.senses.length}-sense vocabulary snapshot.`);
  }
}

if (process.argv[1] && path.resolve(process.argv[1]) === fileURLToPath(import.meta.url)) await main();
