import { createHash } from "node:crypto";
import { mkdir, readFile, readdir, writeFile } from "node:fs/promises";
import path from "node:path";
import process from "node:process";
import { fileURLToPath } from "node:url";
import { repositoryRoot, sources } from "./lib/sources.mjs";

const outputPath = path.resolve(
  path.dirname(fileURLToPath(import.meta.url)),
  "../src/content/generated/curriculum-snapshot.json",
);

const sha256 = (value) => createHash("sha256").update(value).digest("hex");
const canonicalize = (value) => {
  if (Array.isArray(value)) return `[${value.map(canonicalize).join(",")}]`;
  if (value !== null && typeof value === "object") {
    return `{${Object.keys(value)
      .sort()
      .map((key) => `${JSON.stringify(key)}:${canonicalize(value[key])}`)
      .join(",")}}`;
  }
  return JSON.stringify(value);
};
const canonicalHashWithout = (record, identityField) => {
  const projected = { ...record };
  delete projected[identityField];
  return sha256(canonicalize(projected));
};
export const assertUnreviewed = (status, label) => {
  if (status !== "UNREVIEWED") fail(`${label} content status drifted`);
};
export const assertSafeInventoryPaths = (inventory, label) => {
  const paths = inventory.map((record) => requireString(record.path, `${label}.inventory.path`).replaceAll("\\", "/"));
  if (paths.some((entry) => !/^packets\/[A-Za-z0-9._-]+\.json$/.test(entry))) {
    fail(`${label} contains an unsafe or unsupported packet path`);
  }
  return paths;
};
export const assertBytesHash = (bytes, expected, label) => {
  if (sha256(bytes) !== expected) fail(`hash mismatch for ${label}`);
};
export const addUniqueIdentity = (identities, language, lessonId) => {
  const identity = `${language}:${lessonId}`;
  if (identities.has(identity)) fail(`duplicate lesson identity ${identity}`);
  identities.add(identity);
};
const fail = (message) => {
  throw new Error(`Snapshot build failed: ${message}`);
};
const requireString = (value, label) => {
  if (typeof value !== "string" || value.trim().length === 0) fail(`${label} must be a non-empty string`);
  return value;
};
const requireArray = (value, label) => {
  if (!Array.isArray(value)) fail(`${label} must be an array`);
  return value;
};
const requireRecord = (value, label) => {
  if (typeof value !== "object" || value === null || Array.isArray(value)) fail(`${label} must be an object`);
  return value;
};
const requirePositiveInteger = (value, label) => {
  if (!Number.isInteger(value) || value < 1) fail(`${label} must be a positive integer`);
  return value;
};
const requireStringArray = (value, label) =>
  requireArray(value, label).map((item, index) => requireString(item, `${label}[${index}]`));
const optionalString = (value, label) => value === undefined ? undefined : requireString(value, label);
const optionalStringArray = (value, label) => value === undefined ? undefined : requireStringArray(value, label);
const optionalArray = (value, label) => {
  if (value === undefined) return undefined;
  return requireArray(value, label);
};
const requireUniqueIds = (records, label) => {
  const identities = new Set();
  for (const record of records) {
    if (identities.has(record.id)) fail(`${label} contains duplicate ${record.id} IDs`);
    identities.add(record.id);
  }
  return records;
};
const optionalUniqueIds = (records, label) => records === undefined ? undefined : requireUniqueIds(records, label);
const requireSafeSegment = (value, label) => {
  const segment = requireString(value, label);
  if (!/^[A-Za-z0-9][A-Za-z0-9._-]*$/.test(segment)) fail(`${label} contains an unsafe route segment`);
  return segment;
};
const practiceStringFields = [
  "goal",
  "instruction",
  "question",
  "answer",
  "transcript",
  "target",
  "without_audio",
  "assessment",
  "feedback_boundary",
  "mode",
  "situation",
  "learner_role",
  "ai_role",
  "explanation",
];
const practiceArrayFields = ["constraints", "checklist", "useful_language", "examples"];
export const projectPracticeProtocol = (protocol, label) => {
  requireRecord(protocol, label);
  const projected = {};
  for (const field of practiceStringFields) {
    if (protocol[field] === undefined || protocol[field] === null) continue;
    projected[field] = requireString(protocol[field], `${label}.${field}`);
  }
  if (!projected.instruction) fail(`${label}.instruction must be supplied`);
  for (const field of practiceArrayFields) {
    if (protocol[field] === undefined || protocol[field] === null) continue;
    projected[field] = requireStringArray(protocol[field], `${label}.${field}`);
  }
  return projected;
};
const optionalPractice = (value, label) => {
  if (value === undefined || value === null) return undefined;
  if (typeof value !== "object" || Array.isArray(value)) fail(`${label} must be an object when supplied`);
  const result = {};
  for (const modality of ["listening", "speaking", "pronunciation", "writing"]) {
    const protocol = value[modality];
    if (protocol === undefined || protocol === null) continue;
    result[modality] = projectPracticeProtocol(protocol, `${label}.${modality}`);
  }
  return result;
};

const VIETNAMESE_TIP_MARKER = "Mẹo tiếng Việt:";
const projectEnglishSection = (section, packetId, source) => {
  requireRecord(section, `${packetId}.section`);
  const id = requireSafeSegment(section.id, `${packetId}.section.id`);
  const type = requireString(section.section_type, `${packetId}.section.type`);
  const title = requireString(section.title, `${packetId}.section.title`);
  const originalBody = requireString(section.body, `${packetId}.section.body`);
  if (source.vietnameseTipProjection !== "A1_V2_EXPLANATION_MARKER" || type !== "explanation") {
    return { id, title, type, body: originalBody };
  }
  const markerCount = originalBody.split(VIETNAMESE_TIP_MARKER).length - 1;
  if (markerCount !== 1) fail(`${packetId}.${id} must contain exactly one Vietnamese tip marker`);
  const [body, vietnameseTip] = originalBody.split(VIETNAMESE_TIP_MARKER).map((part) => part.trim());
  if (!body || !vietnameseTip) fail(`${packetId}.${id} has an empty Vietnamese tip boundary`);
  return { id, title, type, body, vietnameseTip };
};

function adaptEnglishPacket(packet, source) {
  requireRecord(packet, "English packet");
  requireArray(packet.content_sections, `${packet.packet_id}.content_sections`);
  return {
    language: source.language,
    band: source.band,
    courseAvailability: source.courseAvailability,
    tier: requireString(packet.tier, `${packet.packet_id}.tier`),
    unitId: requireSafeSegment(packet.unit_id, `${packet.packet_id}.unit_id`),
    lessonId: requireSafeSegment(packet.lesson_id, `${packet.packet_id}.lesson_id`),
    sequence: requirePositiveInteger(packet.sequence, `${packet.packet_id}.sequence`),
    title: requireString(packet.title, `${packet.packet_id}.title`),
    topic: requireString(packet.topic, `${packet.packet_id}.topic`),
    durationMinutes: requirePositiveInteger(packet.duration_minutes, `${packet.packet_id}.duration_minutes`),
    objectives: optionalStringArray(packet.objectives, `${packet.packet_id}.objectives`),
    languageFocus: optionalString(packet.language_focus, `${packet.packet_id}.language_focus`),
    prerequisites: optionalStringArray(packet.prerequisite_lesson_ids, `${packet.packet_id}.prerequisites`),
    sections: requireUniqueIds(
      packet.content_sections.map((section) => projectEnglishSection(section, packet.packet_id, source)),
      `${packet.packet_id}.sections`,
    ),
    exercises: optionalUniqueIds(
      optionalArray(packet.exercises, `${packet.packet_id}.exercises`)?.map((exercise, index) =>
        projectExercise(exercise, `${packet.packet_id}.exercises[${index}]`),
      ),
      `${packet.packet_id}.exercises`,
    ),
    practice: optionalPractice(packet.practice, `${packet.packet_id}.practice`),
  };
}

export function projectExercise(exercise, label) {
  requireRecord(exercise, label);
  const projected = {
    id: requireSafeSegment(exercise.id, `${label}.id`),
    type: requireString(exercise.type, `${label}.type`),
    prompt: requireString(exercise.prompt, `${label}.prompt`),
  };
  for (const field of ["options", "acceptable_answers", "items", "correct_order"]) {
    const value = optionalStringArray(exercise[field], `${label}.${field}`);
    if (value !== undefined) projected[field] = value;
  }
  for (const field of ["correct_answer", "answer", "stimulus", "explanation"]) {
    const value = optionalString(exercise[field], `${label}.${field}`);
    if (value !== undefined) projected[field] = value;
  }
  if (exercise.pairs !== undefined) {
    projected.pairs = requireArray(exercise.pairs, `${label}.pairs`).map((pair, index) => {
      requireRecord(pair, `${label}.pairs[${index}]`);
      return {
        left: requireString(pair.left, `${label}.pairs[${index}].left`),
        right: requireString(pair.right, `${label}.pairs[${index}].right`),
      };
    });
  }
  if (exercise.questions !== undefined) {
    projected.questions = requireArray(exercise.questions, `${label}.questions`).map((question, index) => {
      requireRecord(question, `${label}.questions[${index}]`);
      return {
        question: requireString(question.question, `${label}.questions[${index}].question`),
        acceptable_answers: requireStringArray(
          question.acceptable_answers,
          `${label}.questions[${index}].acceptable_answers`,
        ),
      };
    });
  }
  if (exercise.rubric !== undefined) {
    if (typeof exercise.rubric === "string") {
      projected.rubric = requireString(exercise.rubric, `${label}.rubric`);
    } else {
      requireRecord(exercise.rubric, `${label}.rubric`);
      const criteria = optionalStringArray(exercise.rubric.criteria, `${label}.rubric.criteria`);
      if (criteria === undefined) fail(`${label}.rubric must be a string or contain criteria`);
      projected.rubric = { criteria };
    }
  }
  validateProjectedExercise(projected, label);
  return projected;
}

const simpleObjectiveTypes = new Set(["multiple_choice", "fill_blank", "selection", "completion"]);
const questionObjectiveTypes = new Set(["reading", "listening"]);

const hasUniqueStrings = (values) => new Set(values).size === values.length;

function validateProjectedExercise(exercise, label) {
  if (simpleObjectiveTypes.has(exercise.type)) {
    const answers = exercise.correct_answer
      ? [exercise.correct_answer]
      : exercise.acceptable_answers ?? (exercise.answer ? [exercise.answer] : []);
    if (answers.length === 0) fail(`${label} requires supplied answer data`);
    if (exercise.type === "multiple_choice") {
      if (!exercise.options?.length || !hasUniqueStrings(exercise.options)) {
        fail(`${label} requires unique multiple-choice options`);
      }
      if (!answers.every((answer) => exercise.options.includes(answer))) {
        fail(`${label} answer data must be included in its multiple-choice options`);
      }
    }
    return;
  }
  if (exercise.type === "matching") {
    if (!exercise.pairs?.length || !hasUniqueStrings(exercise.pairs.map((pair) => pair.left)) ||
      !hasUniqueStrings(exercise.pairs.map((pair) => pair.right))) {
      fail(`${label} requires uniquely labeled matching pairs`);
    }
    return;
  }
  if (exercise.type === "ordering") {
    if (!exercise.items?.length || !exercise.correct_order?.length ||
      exercise.items.length !== exercise.correct_order.length ||
      !hasUniqueStrings(exercise.items) || !hasUniqueStrings(exercise.correct_order) ||
      JSON.stringify([...exercise.items].sort()) !== JSON.stringify([...exercise.correct_order].sort())) {
      fail(`${label} requires compatible unique ordering items and answer data`);
    }
    return;
  }
  if (questionObjectiveTypes.has(exercise.type) &&
    (!exercise.questions?.length || !hasUniqueStrings(exercise.questions.map((question) => question.question)) ||
      exercise.questions.some((question) => !question.acceptable_answers.length))) {
    fail(`${label} requires answerable, uniquely labeled questions`);
  }
}

function adaptGermanExercise(exercise, packetId) {
  const label = `${packetId}.exercise`;
  requireString(exercise.id, `${label}.id`);
  requireString(exercise.type, `${label}.type`);
  requireString(exercise.prompt, `${label}.prompt`);
  if (exercise.type !== "ordering") return projectExercise(exercise, label);

  const correctOrder = requireString(exercise.answer, `${label}.${exercise.id}.answer`)
    .split(",")
    .map((item) => item.trim())
    .filter(Boolean);
  if (correctOrder.length < 2) fail(`${packetId}.${exercise.id} has an unusable ordering answer`);
  return projectExercise({
    ...exercise,
    items: [...correctOrder.slice(1), correctOrder[0]],
    correct_order: correctOrder,
  }, label);
}

function germanSectionType(title) {
  if (/^Modell\s+\d+/u.test(title)) return "example";
  if (/^Hinweis\s+\d+/u.test(title)) return "explanation";
  return "lesson";
}

export function adaptGermanPacket(packet, source) {
  requireRecord(packet, "German packet");
  if (packet.language_code !== "de") fail(`${packet.packet_id} has an invalid language_code`);
  const practices = {};
  const seenModalities = new Set();
  for (const prompt of optionalArray(packet.prompts, `${packet.packet_id}.prompts`) ?? []) {
    requireRecord(prompt, `${packet.packet_id}.prompt`);
    const modality = requireString(prompt.modality, `${packet.packet_id}.prompt.modality`);
    if (!["listening", "speaking", "pronunciation", "writing"].includes(modality)) continue;
    if (seenModalities.has(modality)) fail(`${packet.packet_id} has duplicate ${modality} practice`);
    seenModalities.add(modality);
    practices[modality] = projectPracticeProtocol(
      prompt,
      `${packet.packet_id}.prompts.${modality}`,
    );
  }
  const lessonId = requireSafeSegment(packet.lesson_id, `${packet.packet_id}.lesson_id`);
  const unitMatch = lessonId.match(/^(.*)-l\d+$/);
  if (!unitMatch) fail(`${packet.packet_id} lesson ID does not identify a unit`);
  const objectives = optionalStringArray(packet.objectives, `${packet.packet_id}.objectives`);
  return {
    language: source.language,
    band: source.band,
    courseAvailability: source.courseAvailability,
    tier: requireString(packet.tier, `${packet.packet_id}.tier`),
    unitId: requireSafeSegment(unitMatch[1], `${packet.packet_id}.unit_id`),
    lessonId,
    sequence: requirePositiveInteger(packet.sequence, `${packet.packet_id}.sequence`),
    title: requireString(packet.title, `${packet.packet_id}.title`),
    topic: requireString(packet.title, `${packet.packet_id}.title`),
    durationMinutes: requirePositiveInteger(packet.duration_minutes, `${packet.packet_id}.duration_minutes`),
    objectives,
    languageFocus: objectives?.join(" "),
    prerequisites: optionalStringArray(packet.prerequisite_lesson_ids, `${packet.packet_id}.prerequisites`),
    sections: requireUniqueIds(
      requireArray(packet.sections, `${packet.packet_id}.sections`).map((section, index) => {
        requireRecord(section, `${packet.packet_id}.section[${index}]`);
        const title = requireString(section.title, `${packet.packet_id}.section.title`);
        return {
          id: `section-${index + 1}`,
          title,
          type: germanSectionType(title),
          body: requireString(section.body, `${packet.packet_id}.section.body`),
        };
      }),
      `${packet.packet_id}.sections`,
    ),
    exercises: optionalUniqueIds(
      optionalArray(packet.exercises, `${packet.packet_id}.exercises`)?.map((exercise) => adaptGermanExercise(exercise, packet.packet_id)),
      `${packet.packet_id}.exercises`,
    ),
    practice: Object.keys(practices).length ? practices : undefined,
  };
}

export async function buildSnapshot() {
  const lessons = [];
  const seenLessonIds = new Set();

  for (const source of sources) {
    const manifestPath = path.resolve(repositoryRoot, source.manifest);
    const manifestBytes = await readFile(manifestPath);
    const manifest = JSON.parse(manifestBytes.toString("utf8"));
    const inventory = requireArray(manifest.inventory, `${source.manifest}.inventory`);
    const lessonIds = requireArray(manifest.lesson_ids, `${source.manifest}.lesson_ids`);
    const manifestDirectory = path.dirname(manifestPath);
    const expectedManifestType = source.language === "de"
      ? "german_a1_pilot_manifest"
      : `${source.band.toLowerCase()}_full_run_manifest`;
    const expectedManifestSchema = source.language === "en" && source.band === "A1" ? "2.0" : "1.0";
    if (manifest.record_type !== expectedManifestType || manifest.schema_version !== expectedManifestSchema) {
      fail(`${source.manifest} has an unsupported manifest shape`);
    }
    assertUnreviewed(manifest.content_status, source.manifest);
    if (canonicalHashWithout(manifest, "manifest_sha256") !== manifest.manifest_sha256) {
      fail(`${source.manifest} canonical manifest hash mismatch`);
    }
    if (inventory.length !== source.expectedCount || lessonIds.length !== source.expectedCount) {
      fail(`${source.manifest} must contain exactly ${source.expectedCount} packets`);
    }
    const inventoryPaths = assertSafeInventoryPaths(inventory, source.manifest).sort();
    const packetDirectoryEntries = await readdir(path.join(manifestDirectory, "packets"));
    if (packetDirectoryEntries.some((entry) => !/^[A-Za-z0-9._-]+\.json$/.test(entry))) {
      fail(`${source.manifest} packet directory contains an unexpected file`);
    }
    const packetFiles = packetDirectoryEntries
      .map((entry) => `packets/${entry}`)
      .sort();
    if (JSON.stringify(packetFiles) !== JSON.stringify(inventoryPaths)) {
      fail(`${source.manifest} packet directory is not a closed inventory`);
    }
    if (source.language === "de" && manifest.language_code !== "de") {
      fail(`${source.manifest} does not declare German scope`);
    }

    for (let index = 0; index < inventory.length; index += 1) {
      const record = inventory[index];
      requireString(record.path, `${source.manifest}.inventory.path`);
      requireString(record.sha256, `${source.manifest}.inventory.sha256`);
      const packetPath = path.resolve(manifestDirectory, record.path);
      if (!packetPath.startsWith(`${manifestDirectory}${path.sep}`)) fail(`unsafe packet path ${record.path}`);
      const packetBytes = await readFile(packetPath);
      assertBytesHash(packetBytes, record.sha256, record.path);
      const packet = JSON.parse(packetBytes.toString("utf8"));
      const expectedPacketType = source.language === "de"
        ? "german_a1_pilot_lesson_packet"
        : `${source.band.toLowerCase()}_full_packet`;
      if (packet.record_type !== expectedPacketType || packet.schema_version !== expectedManifestSchema) {
        fail(`${record.path} has an unsupported packet shape`);
      }
      if (canonicalHashWithout(packet, "packet_sha256") !== packet.packet_sha256) {
        fail(`canonical packet hash mismatch for ${record.path}`);
      }
      if (packet.lesson_id !== lessonIds[index]) fail(`lesson order mismatch for ${record.path}`);
      assertUnreviewed(packet.content_status, record.path);
      addUniqueIdentity(seenLessonIds, source.language, packet.lesson_id);
      lessons.push(
        source.language === "de"
          ? adaptGermanPacket(packet, source)
          : adaptEnglishPacket(packet, source),
      );
    }

  }

  for (const source of sources.filter((item) => item.vietnameseTipProjection === "A1_V2_EXPLANATION_MARKER")) {
    const tipCount = lessons
      .filter((lesson) => lesson.language === source.language && lesson.band === source.band)
      .flatMap((lesson) => lesson.sections ?? [])
      .filter((section) => section.vietnameseTip).length;
    if (tipCount !== source.expectedCount) fail(`${source.language} ${source.band} must contain ${source.expectedCount} supplied Vietnamese tips`);
  }

  const languages = [...new Set(sources.map((source) => source.language))].map((code) => {
    const languageSources = sources.filter((source) => source.language === code);
    const languageLessons = lessons.filter((lesson) => lesson.language === code);
    return {
      code,
      name: languageSources[0].languageName,
      lessonCount: languageLessons.length,
      bands: [...new Set(languageSources.map((source) => source.band))],
    };
  });

  return {
    schemaVersion: "1.1",
    languages,
    lessons,
  };
}

async function main() {
  const snapshot = await buildSnapshot();
  const serialized = `${JSON.stringify(snapshot, null, 2)}\n`;
  if (process.argv.includes("--check")) {
    let current;
    try {
      current = await readFile(outputPath, "utf8");
    } catch {
      fail("generated snapshot is missing; run npm run snapshot");
    }
    if (current !== serialized) fail("generated snapshot is stale; run npm run snapshot");
    console.log(`Verified deterministic ${snapshot.lessons.length}-packet curriculum snapshot.`);
  } else {
    await mkdir(path.dirname(outputPath), { recursive: true });
    await writeFile(outputPath, serialized, "utf8");
    console.log(`Built deterministic ${snapshot.lessons.length}-packet curriculum snapshot.`);
  }
}

if (process.argv[1] && path.resolve(process.argv[1]) === fileURLToPath(import.meta.url)) {
  await main();
}
