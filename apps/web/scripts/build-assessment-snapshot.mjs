import { createHash } from "node:crypto";
import { mkdir, readFile, writeFile } from "node:fs/promises";
import path from "node:path";
import process from "node:process";
import { fileURLToPath } from "node:url";
import { repositoryRoot } from "./lib/sources.mjs";

const scriptDirectory = path.dirname(fileURLToPath(import.meta.url));
const runId = "assessment_38118701d2db5edb1013b6584591b78bd3d697cd3d47367af8c05eebc261c1d3";
const runDirectory = path.resolve(repositoryRoot, "curriculum/assessments/v1/runs", runId);
const outputPath = path.resolve(scriptDirectory, "../src/content/generated/assessment-snapshot.json");
const expectedCounts = { LESSON_QUIZ: 300, UNIT_TEST: 60, LEVEL_TEST: 6, PLACEMENT: 1 };
const supportedTypes = new Set(["multiple_choice", "fill_blank", "matching", "ordering", "reading", "listening"]);
const safeId = /^[A-Za-z0-9][A-Za-z0-9._-]*$/u;
const sha256 = (value) => createHash("sha256").update(value).digest("hex");
const fail = (message) => { throw new Error(`Assessment snapshot build failed: ${message}`); };
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
const requireSafeId = (value, label) => {
  const id = requireString(value, label);
  if (!safeId.test(id)) fail(`${label} is not a safe identifier`);
  return id;
};
const requireHash = (value, label) => {
  const hash = requireString(value, label);
  if (!/^[a-f0-9]{64}$/u.test(hash)) fail(`${label} is not a SHA-256 hash`);
  return hash;
};
const requireStringArray = (value, label) => requireArray(value, label).map((item, index) => requireString(item, `${label}[${index}]`));
const canonicalize = (value) => {
  if (Array.isArray(value)) return `[${value.map(canonicalize).join(",")}]`;
  if (value !== null && typeof value === "object") {
    return `{${Object.keys(value).sort().map((key) => `${JSON.stringify(key)}:${canonicalize(value[key])}`).join(",")}}`;
  }
  return JSON.stringify(value);
};
const canonicalHashWithout = (record, field) => {
  const copy = { ...record };
  delete copy[field];
  return sha256(canonicalize(copy));
};
const requireOnly = (record, allowed, label) => {
  if (Object.keys(record).some((key) => !allowed.has(key))) fail(`${label} contains unsupported fields`);
};
const unique = (values) => new Set(values).size === values.length;

function projectAnswerContract(value, label, type) {
  const contract = requireRecord(value, `${label}.answer_contract`);
  if (type === "multiple_choice") {
    requireOnly(contract, new Set(["correct_answer"]), `${label}.answer_contract`);
    return { correctAnswer: requireString(contract.correct_answer, `${label}.answer_contract.correct_answer`) };
  }
  if (type === "fill_blank" || type === "reading" || type === "listening") {
    requireOnly(contract, new Set(["acceptable_answers"]), `${label}.answer_contract`);
    const acceptableAnswers = requireStringArray(contract.acceptable_answers, `${label}.answer_contract.acceptable_answers`);
    if (!acceptableAnswers.length || !unique(acceptableAnswers)) fail(`${label}.answer_contract has invalid acceptable answers`);
    return { acceptableAnswers };
  }
  if (type === "matching") {
    requireOnly(contract, new Set(["pairs"]), `${label}.answer_contract`);
    const pairs = requireArray(contract.pairs, `${label}.answer_contract.pairs`).map((pair, index) => {
      requireOnly(requireRecord(pair, `${label}.answer_contract.pairs[${index}]`), new Set(["left", "right"]), `${label}.answer_contract.pairs[${index}]`);
      return {
        left: requireString(pair.left, `${label}.answer_contract.pairs[${index}].left`),
        right: requireString(pair.right, `${label}.answer_contract.pairs[${index}].right`),
      };
    });
    if (!pairs.length || !unique(pairs.map((pair) => pair.left)) || !unique(pairs.map((pair) => pair.right))) fail(`${label}.answer_contract has invalid matching pairs`);
    return { pairs };
  }
  if (type === "ordering") {
    requireOnly(contract, new Set(["correct_order"]), `${label}.answer_contract`);
    const correctOrder = requireStringArray(contract.correct_order, `${label}.answer_contract.correct_order`);
    if (!correctOrder.length || !unique(correctOrder)) fail(`${label}.answer_contract has invalid correct order`);
    return { correctOrder };
  }
  fail(`${label} has unsupported item type`);
}

function projectItem(value, label) {
  const item = requireRecord(value, label);
  requireOnly(item, new Set(["item_id", "item_type", "media_required", "source", "target_ids", "target_dimensions", "concept_ids", "prompt", "stimulus", "question", "options", "items", "answer_contract", "item_sha256"]), label);
  const itemType = requireString(item.item_type, `${label}.item_type`);
  if (!supportedTypes.has(itemType)) fail(`${label}.item_type is unsupported`);
  if (item.media_required !== false) fail(`${label}.media_required must be false`);
  if (item.item_sha256 !== canonicalHashWithout(item, "item_sha256")) fail(`${label}.item_sha256 does not match content`);
  const source = requireRecord(item.source, `${label}.source`);
  requireOnly(source, new Set(["level", "tier", "unit_id", "lesson_id", "packet_id", "packet_sha256", "exercise_id", "question_index"]), `${label}.source`);
  if (source.level === undefined || !["A1", "A2", "B1", "B2", "C1", "C2"].includes(requireString(source.level, `${label}.source.level`))) fail(`${label}.source.level is invalid`);
  const projectedSource = {
    level: source.level,
    tier: requireString(source.tier, `${label}.source.tier`),
    unitId: requireSafeId(source.unit_id, `${label}.source.unit_id`),
    lessonId: requireSafeId(source.lesson_id, `${label}.source.lesson_id`),
    packetId: requireSafeId(source.packet_id, `${label}.source.packet_id`),
    packetSha256: requireHash(source.packet_sha256, `${label}.source.packet_sha256`),
    exerciseId: requireSafeId(source.exercise_id, `${label}.source.exercise_id`),
    ...(source.question_index === undefined ? {} : { questionIndex: source.question_index }),
  };
  if (projectedSource.questionIndex !== undefined && (!Number.isInteger(projectedSource.questionIndex) || projectedSource.questionIndex < 1)) fail(`${label}.source.question_index is invalid`);
  const targetIds = requireStringArray(item.target_ids, `${label}.target_ids`);
  const targetDimensions = requireStringArray(item.target_dimensions, `${label}.target_dimensions`);
  const conceptIds = requireStringArray(item.concept_ids, `${label}.concept_ids`);
  if (!targetIds.length || !targetDimensions.length || !conceptIds.length || !unique(targetIds) || !unique(targetDimensions) || !unique(conceptIds)) fail(`${label} has invalid target bindings`);
  const projected = {
    id: requireSafeId(item.item_id, `${label}.item_id`),
    type: itemType,
    prompt: requireString(item.prompt, `${label}.prompt`),
    source: projectedSource,
    targetIds,
    targetDimensions,
    conceptIds,
    answerContract: projectAnswerContract(item.answer_contract, label, itemType),
  };
  if (item.stimulus !== undefined) projected.stimulus = requireString(item.stimulus, `${label}.stimulus`);
  if (item.question !== undefined) projected.question = requireString(item.question, `${label}.question`);
  if (item.options !== undefined) {
    const options = requireStringArray(item.options, `${label}.options`);
    if (!options.length || !unique(options)) fail(`${label}.options are invalid`);
    projected.options = options;
  }
  if (item.items !== undefined) {
    const items = requireStringArray(item.items, `${label}.items`);
    if (!items.length || !unique(items)) fail(`${label}.items are invalid`);
    projected.items = items;
  }
  if (itemType === "multiple_choice" && (!projected.options || !projected.options.includes(projected.answerContract.correctAnswer))) fail(`${label} has an invalid multiple choice answer`);
  if (itemType === "ordering" && (!projected.items || projected.items.length !== projected.answerContract.correctOrder.length || JSON.stringify([...projected.items].sort()) !== JSON.stringify([...projected.answerContract.correctOrder].sort()))) fail(`${label} has an invalid ordering contract`);
  if ((itemType === "reading" || itemType === "listening") && (!projected.stimulus || !projected.question || !projectedSource.questionIndex)) fail(`${label} has an incomplete question item`);
  return projected;
}

function projectPackage(value, label) {
  const assessment = requireRecord(value, label);
  requireOnly(assessment, new Set(["schema_version", "record_type", "assessment_id", "assessment_type", "policy_version", "content_status", "scope", "items", "package_sha256"]), label);
  if (assessment.schema_version !== "1.0" || assessment.record_type !== "assessment_package" || assessment.policy_version !== "ASSESSMENT_MASTERY_V1" || assessment.content_status !== "UNREVIEWED") fail(`${label} has unsupported package metadata`);
  if (assessment.package_sha256 !== canonicalHashWithout(assessment, "package_sha256")) fail(`${label}.package_sha256 does not match content`);
  const type = requireString(assessment.assessment_type, `${label}.assessment_type`);
  if (!Object.hasOwn(expectedCounts, type)) fail(`${label}.assessment_type is unsupported`);
  const scope = requireRecord(assessment.scope, `${label}.scope`);
  const knownScopeKeys = new Set(["levels", "tiers", "unit_ids", "lesson_ids", "target_dimensions", "outline_assessment_id", "items_per_tier", "passing_correct_per_tier", "output_field"]);
  requireOnly(scope, knownScopeKeys, `${label}.scope`);
  const levels = requireStringArray(scope.levels, `${label}.scope.levels`);
  if (!levels.length || levels.some((level) => !["A1", "A2", "B1", "B2", "C1", "C2"].includes(level))) fail(`${label}.scope.levels is invalid`);
  const items = requireArray(assessment.items, `${label}.items`).map((item, index) => projectItem(item, `${label}.items[${index}]`));
  if (!items.length || !unique(items.map((item) => item.id))) fail(`${label}.items is invalid`);
  return {
    id: requireSafeId(assessment.assessment_id, `${label}.assessment_id`),
    type,
    packageSha256: requireHash(assessment.package_sha256, `${label}.package_sha256`),
    scope: {
      levels,
      tiers: requireStringArray(scope.tiers, `${label}.scope.tiers`),
      unitIds: requireStringArray(scope.unit_ids, `${label}.scope.unit_ids`),
      lessonIds: requireStringArray(scope.lesson_ids, `${label}.scope.lesson_ids`),
      ...(scope.target_dimensions === undefined ? {} : { targetDimensions: requireStringArray(scope.target_dimensions, `${label}.scope.target_dimensions`) }),
      ...(scope.outline_assessment_id === undefined ? {} : { outlineAssessmentId: requireSafeId(scope.outline_assessment_id, `${label}.scope.outline_assessment_id`) }),
      ...(scope.items_per_tier === undefined ? {} : { itemsPerTier: scope.items_per_tier }),
      ...(scope.passing_correct_per_tier === undefined ? {} : { passingCorrectPerTier: scope.passing_correct_per_tier }),
      ...(scope.output_field === undefined ? {} : { outputField: requireString(scope.output_field, `${label}.scope.output_field`) }),
    },
    items,
    contentStatus: "UNREVIEWED",
  };
}

export async function buildAssessmentSnapshot() {
  const manifestPath = path.join(runDirectory, "manifest.json");
  const manifest = JSON.parse(await readFile(manifestPath, "utf8"));
  requireRecord(manifest, "manifest");
  if (manifest.record_type !== "assessment_run_manifest" || manifest.run_id !== runId || manifest.policy_version !== "ASSESSMENT_MASTERY_V1" || manifest.content_status !== "UNREVIEWED" || manifest.manifest_sha256 !== canonicalHashWithout(manifest, "manifest_sha256")) fail("assessment run manifest drifted");
  const inventory = requireArray(manifest.package_inventory, "manifest.package_inventory");
  if (inventory.length !== 367 || !manifest.counts ||
    manifest.counts.lesson_quizzes !== 300 || manifest.counts.unit_tests !== 60 ||
    manifest.counts.level_tests !== 6 || manifest.counts.placement_packages !== 1 ||
    manifest.counts.packages !== 367 || Object.keys(manifest.counts).length !== 5) fail("assessment run inventory count drifted");
  const packages = [];
  const counts = Object.fromEntries(Object.keys(expectedCounts).map((type) => [type, 0]));
  const packageIds = new Set();
  for (const [index, entry] of inventory.entries()) {
    requireRecord(entry, `manifest.package_inventory[${index}]`);
    const packageId = requireSafeId(entry.assessment_id, `manifest.package_inventory[${index}].assessment_id`);
    const relativePath = requireString(entry.path, `manifest.package_inventory[${index}].path`);
    if (!/^packages\/[A-Za-z0-9._-]+\.json$/u.test(relativePath)) fail(`manifest package path ${relativePath} is unsafe`);
    const expectedHash = requireHash(entry.package_sha256, `manifest.package_inventory[${index}].package_sha256`);
    const projected = projectPackage(JSON.parse(await readFile(path.join(runDirectory, relativePath), "utf8")), relativePath);
    if (projected.id !== packageId || projected.packageSha256 !== expectedHash || entry.item_count !== projected.items.length || packageIds.has(projected.id)) fail(`manifest package entry ${packageId} drifted`);
    packageIds.add(projected.id);
    counts[projected.type] += 1;
    packages.push(projected);
  }
  if (JSON.stringify(counts) !== JSON.stringify(expectedCounts)) fail(`assessment package type counts drifted: ${JSON.stringify(counts)}`);
  packages.sort((left, right) => left.id.localeCompare(right.id));
  return { schemaVersion: "1.0", runId, manifestSha256: requireHash(manifest.manifest_sha256, "manifest.manifest_sha256"), contentStatus: "UNREVIEWED", packages };
}

async function main() {
  const snapshot = await buildAssessmentSnapshot();
  const serialized = `${JSON.stringify(snapshot, null, 2)}\n`;
  if (process.argv.includes("--check")) {
    let current;
    try { current = await readFile(outputPath, "utf8"); } catch { fail("generated assessment snapshot is missing; run npm run build:assessment-snapshot"); }
    if (current !== serialized) fail("generated assessment snapshot is stale; run npm run build:assessment-snapshot");
    console.log(`Verified deterministic ${snapshot.packages.length}-package English assessment snapshot.`);
    return;
  }
  await mkdir(path.dirname(outputPath), { recursive: true });
  await writeFile(outputPath, serialized, "utf8");
  console.log(`Built deterministic ${snapshot.packages.length}-package English assessment snapshot.`);
}

if (process.argv[1] && path.resolve(process.argv[1]) === fileURLToPath(import.meta.url)) await main();
