import { createHash } from "node:crypto";
import { mkdir, readFile, writeFile } from "node:fs/promises";
import path from "node:path";
import process from "node:process";
import { fileURLToPath } from "node:url";
import { repositoryRoot, sources } from "./lib/sources.mjs";

const scriptDirectory = path.dirname(fileURLToPath(import.meta.url));
const outputPath = path.resolve(scriptDirectory, "../src/content/generated/grammar-snapshot.json");
const bands = new Set(["A1", "A2", "B1", "B2", "C1", "C2"]);
const objectiveExerciseTypes = new Set([
  "multiple_choice", "fill_blank", "selection", "completion", "matching", "ordering", "reading", "listening",
]);
const allocationPaths = {
  A1: "curriculum/a1-full/v1/allocation.json",
  A2: "curriculum/a2-full/v1/allocation.json",
  B1: "curriculum/b1-full/v1/allocation.json",
  B2: "curriculum/b2-full/v1/allocation.json",
  C1: "curriculum/c1-full/v1/allocation.json",
  C2: "curriculum/c2-full/v1/allocation.json",
};

const fail = (message) => { throw new Error(`Grammar snapshot build failed: ${message}`); };
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
  if (typeof value !== "string" || value.trim().length === 0) fail(`${label} must be a non-empty string`);
  return value;
};
const requireStringArray = (value, label) => requireArray(value, label).map((item, index) => requireString(item, `${label}[${index}]`));
const isSafeId = (value) => typeof value === "string" && /^[a-z][a-z0-9-]*$/u.test(value);
const requireSafeId = (value, label) => {
  if (!isSafeId(value)) fail(`${label} must be a safe identifier`);
  return value;
};
const requireSourceTargetId = (value, label) => {
  if (typeof value !== "string" || !/^[a-z][a-z0-9_]*$/u.test(value)) fail(`${label} must be a safe source target identifier`);
  return value;
};
const unique = (values) => new Set(values).size === values.length;

function grammarId(sourceTargetId) {
  return `grammar-en-${sha256(sourceTargetId).slice(0, 20)}`;
}

function parseAllocation(source, expectedBand) {
  requireRecord(source, `${expectedBand} allocation`);
  if (!new Set(["1.0", "2.0"]).has(source.schema_version) || !Array.isArray(source.targets) || !Array.isArray(source.lessons)) {
    fail(`${expectedBand} allocation has unsupported metadata`);
  }
  const targets = new Map();
  for (const [index, rawTarget] of source.targets.entries()) {
    const label = `${expectedBand} allocation target ${index}`;
    requireRecord(rawTarget, label);
    const id = requireSourceTargetId(rawTarget.id, `${label}.id`);
    if (rawTarget.dimension !== "grammar") continue;
    const tier = requireString(rawTarget.tier, `${label}.tier`);
    if (!new RegExp(`^${expectedBand}\\.[12]$`, "u").test(tier)) fail(`${label}.tier does not belong to ${expectedBand}`);
    if (targets.has(id)) fail(`${expectedBand} allocation has duplicate grammar target ${id}`);
    targets.set(id, {
      id,
      appId: grammarId(id),
      tier,
      prerequisites: requireStringArray(rawTarget.prerequisites, `${label}.prerequisites`),
    });
  }
  if (!targets.size) fail(`${expectedBand} allocation has no grammar targets`);

  const lessons = new Map();
  for (const [index, rawLesson] of source.lessons.entries()) {
    const label = `${expectedBand} allocation lesson ${index}`;
    requireRecord(rawLesson, label);
    const lessonId = requireSafeId(rawLesson.lesson_id, `${label}.lesson_id`);
    const tier = requireString(rawLesson.tier, `${label}.tier`);
    const topic = requireString(rawLesson.topic, `${label}.topic`);
    const title = requireString(rawLesson.language_focus, `${label}.language_focus`);
    const targetUsage = requireArray(rawLesson.target_usage, `${label}.target_usage`).map((usage, usageIndex) => {
      requireRecord(usage, `${label}.target_usage[${usageIndex}]`);
      return {
        targetId: requireSourceTargetId(usage.target_id, `${label}.target_usage[${usageIndex}].target_id`),
        usage: requireString(usage.usage, `${label}.target_usage[${usageIndex}].usage`),
      };
    });
    lessons.set(lessonId, { lessonId, tier, topic, title, targetUsage });
  }

  const introductions = new Map();
  for (const lesson of lessons.values()) {
    for (const usage of lesson.targetUsage) {
      if (!targets.has(usage.targetId) || usage.usage !== "INTRODUCE") continue;
      if (introductions.has(usage.targetId)) fail(`${expectedBand} grammar target ${usage.targetId} has multiple introduction lessons`);
      introductions.set(usage.targetId, lesson);
    }
  }
  for (const target of targets.values()) {
    const lesson = introductions.get(target.id);
    if (!lesson) fail(`${expectedBand} grammar target ${target.id} has no introduction lesson`);
    if (lesson.tier !== target.tier) fail(`${expectedBand} grammar target ${target.id} introduction tier drifted`);
    target.introductionLesson = lesson;
  }
  return { targets, lessons };
}

async function loadPacketIndex(source) {
  const manifestPath = path.resolve(repositoryRoot, source.manifest);
  const manifest = JSON.parse(await readFile(manifestPath, "utf8"));
  if (manifest.content_status !== "UNREVIEWED" || !Array.isArray(manifest.inventory)) {
    fail(`${source.manifest} is not a supported unreviewed manifest`);
  }
  const packets = new Map();
  for (const [index, record] of manifest.inventory.entries()) {
    requireRecord(record, `${source.band} manifest inventory ${index}`);
    const relativePath = requireString(record.path, `${source.band} manifest inventory path`);
    const expectedHash = requireString(record.sha256, `${source.band} manifest inventory hash`);
    if (!/^[a-f0-9]{64}$/u.test(expectedHash)) fail(`${source.band} manifest has invalid packet hash`);
    const packetPath = path.resolve(path.dirname(manifestPath), relativePath);
    const bytes = await readFile(packetPath);
    if (sha256(bytes) !== expectedHash) fail(`${source.band} packet hash mismatch for ${relativePath}`);
    const packet = JSON.parse(bytes.toString("utf8"));
    if (packet.content_status !== "UNREVIEWED") fail(`${source.band} packet ${relativePath} is not UNREVIEWED`);
    const lessonId = requireSafeId(packet.lesson_id, `${source.band} packet lesson_id`);
    if (packets.has(lessonId)) fail(`${source.band} manifest repeats lesson ${lessonId}`);
    const exercises = new Map();
    for (const [exerciseIndex, exercise] of requireArray(packet.exercises ?? [], `${lessonId}.exercises`).entries()) {
      requireRecord(exercise, `${lessonId}.exercises[${exerciseIndex}]`);
      const exerciseId = requireSafeId(exercise.id, `${lessonId}.exercise id`);
      if (exercises.has(exerciseId)) fail(`${lessonId} repeats exercise ${exerciseId}`);
      exercises.set(exerciseId, {
        type: requireString(exercise.type, `${lessonId}.${exerciseId}.type`),
        targetIds: requireStringArray(exercise.target_ids ?? [], `${lessonId}.${exerciseId}.target_ids`),
      });
    }
    packets.set(lessonId, exercises);
  }
  if (packets.size !== source.expectedCount) fail(`${source.band} manifest packet count drifted`);
  return packets;
}

export async function buildGrammarSnapshot() {
  const englishSources = sources.filter((source) => source.language === "en");
  if (englishSources.length !== bands.size || new Set(englishSources.map((source) => source.band)).size !== bands.size) {
    fail("English course source inventory is incomplete");
  }
  const targets = [];
  const seenAppIds = new Set();
  for (const source of englishSources) {
    if (!bands.has(source.band) || !allocationPaths[source.band]) fail(`unsupported English band ${source.band}`);
    const allocationPath = path.resolve(repositoryRoot, allocationPaths[source.band]);
    const allocation = parseAllocation(JSON.parse(await readFile(allocationPath, "utf8")), source.band);
    const packets = await loadPacketIndex(source);

    for (const target of allocation.targets.values()) {
      if (seenAppIds.has(target.appId)) fail(`duplicate grammar target identity ${target.appId}`);
      seenAppIds.add(target.appId);
      const bindings = [];
      for (const [lessonId, exercises] of packets) {
        for (const [exerciseId, exercise] of exercises) {
          if (objectiveExerciseTypes.has(exercise.type) && exercise.targetIds.includes(target.id)) {
            bindings.push({ lessonId, exerciseId });
          }
        }
      }
      if (!bindings.length) fail(`${source.band} grammar target ${target.id} has no bound objective activity`);
      bindings.sort((left, right) => left.lessonId.localeCompare(right.lessonId) || left.exerciseId.localeCompare(right.exerciseId));
      const bindingKeys = bindings.map((binding) => `${binding.lessonId}\u0000${binding.exerciseId}`);
      if (!unique(bindingKeys)) fail(`${source.band} grammar target ${target.id} has duplicate activity bindings`);
      const prerequisiteIds = target.prerequisites
        .filter((sourceId) => allocation.targets.has(sourceId))
        .map((sourceId) => allocation.targets.get(sourceId).appId)
        .sort();
      targets.push({
        id: target.appId,
        language: "en",
        band: source.band,
        tier: target.tier,
        title: target.introductionLesson.title,
        topic: target.introductionLesson.topic,
        introductionLessonId: target.introductionLesson.lessonId,
        prerequisiteIds,
        exerciseBindings: bindings,
        contentStatus: "UNREVIEWED",
      });
    }
  }
  targets.sort((left, right) => left.band.localeCompare(right.band) || left.introductionLessonId.localeCompare(right.introductionLessonId) || left.id.localeCompare(right.id));
  const inventoryVersion = `grammar-${sha256(JSON.stringify(targets)).slice(0, 16)}`;
  return { schemaVersion: "1.0", inventoryVersion, targets };
}

async function main() {
  const snapshot = await buildGrammarSnapshot();
  const serialized = `${JSON.stringify(snapshot, null, 2)}\n`;
  if (process.argv.includes("--check")) {
    let current;
    try { current = await readFile(outputPath, "utf8"); } catch { fail("generated grammar snapshot is missing; run npm run build:grammar-snapshot"); }
    if (current !== serialized) fail("generated grammar snapshot is stale; run npm run build:grammar-snapshot");
    console.log(`Verified deterministic ${snapshot.targets.length}-target grammar snapshot.`);
  } else {
    await mkdir(path.dirname(outputPath), { recursive: true });
    await writeFile(outputPath, serialized, "utf8");
    console.log(`Built deterministic ${snapshot.targets.length}-target grammar snapshot.`);
  }
}

if (process.argv[1] && path.resolve(process.argv[1]) === fileURLToPath(import.meta.url)) await main();
