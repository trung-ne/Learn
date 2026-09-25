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
  if (typeof value !== "string" || value.length === 0) fail(`${label} must be a non-empty string`);
  return value;
};
const requireArray = (value, label) => {
  if (!Array.isArray(value)) fail(`${label} must be an array`);
  return value;
};

function adaptEnglishPacket(packet, source, sourceRecord) {
  requireArray(packet.content_sections, `${packet.packet_id}.content_sections`);
  const practice = packet.practice ?? {};
  return {
    language: source.language,
    packetFamily: "english-full",
    recordType: packet.record_type,
    languageName: source.languageName,
    band: source.band,
    tier: requireString(packet.tier, `${packet.packet_id}.tier`),
    unitId: requireString(packet.unit_id, `${packet.packet_id}.unit_id`),
    lessonId: requireString(packet.lesson_id, `${packet.packet_id}.lesson_id`),
    packetId: requireString(packet.packet_id, "packet_id"),
    sequence: packet.sequence,
    title: requireString(packet.title, `${packet.packet_id}.title`),
    topic: requireString(packet.topic, `${packet.packet_id}.topic`),
    durationMinutes: packet.duration_minutes,
    objectives: requireArray(packet.objectives, `${packet.packet_id}.objectives`),
    languageFocus: requireString(packet.language_focus, `${packet.packet_id}.language_focus`),
    prerequisites: requireArray(packet.prerequisite_lesson_ids, `${packet.packet_id}.prerequisites`),
    sections: packet.content_sections.map((section) => ({
      id: requireString(section.id, `${packet.packet_id}.section.id`),
      title: requireString(section.title, `${packet.packet_id}.section.title`),
      type: requireString(section.section_type, `${packet.packet_id}.section.type`),
      body: requireString(section.body, `${packet.packet_id}.section.body`),
    })),
    exercises: requireArray(packet.exercises, `${packet.packet_id}.exercises`),
    practice: {
      listening: practice.listening ?? null,
      speaking: practice.speaking ?? null,
      pronunciation: practice.pronunciation ?? null,
      writing: practice.writing ?? null,
    },
    contentStatus: packet.content_status,
    provenance: packet.provenance,
    packetPath: sourceRecord.path,
    packetSha256: sourceRecord.sha256,
  };
}

function adaptGermanExercise(exercise, packetId) {
  requireString(exercise.id, `${packetId}.exercise.id`);
  requireString(exercise.type, `${packetId}.exercise.type`);
  requireString(exercise.prompt, `${packetId}.exercise.prompt`);
  if (exercise.type !== "ordering") return exercise;

  const correctOrder = requireString(exercise.answer, `${packetId}.${exercise.id}.answer`)
    .split(",")
    .map((item) => item.trim())
    .filter(Boolean);
  if (correctOrder.length < 2) fail(`${packetId}.${exercise.id} has an unusable ordering answer`);
  return {
    ...exercise,
    items: [...correctOrder.slice(1), correctOrder[0]],
    correct_order: correctOrder,
  };
}

function adaptGermanPacket(packet, source, sourceRecord) {
  if (packet.language_code !== "de") fail(`${packet.packet_id} has an invalid language_code`);
  const prompts = Object.fromEntries(
    requireArray(packet.prompts, `${packet.packet_id}.prompts`).map((prompt) => [prompt.modality, prompt]),
  );
  for (const modality of ["listening", "speaking", "pronunciation", "writing"]) {
    if (!prompts[modality]) fail(`${packet.packet_id} is missing ${modality} practice`);
  }
  const unitMatch = requireString(packet.lesson_id, `${packet.packet_id}.lesson_id`).match(/^(.*)-l\d+$/);
  if (!unitMatch) fail(`${packet.packet_id} lesson ID does not identify a unit`);
  return {
    language: source.language,
    packetFamily: "german-pilot",
    recordType: packet.record_type,
    languageName: source.languageName,
    band: source.band,
    tier: requireString(packet.tier, `${packet.packet_id}.tier`),
    unitId: unitMatch[1],
    lessonId: packet.lesson_id,
    packetId: requireString(packet.packet_id, "packet_id"),
    sequence: packet.sequence,
    title: requireString(packet.title, `${packet.packet_id}.title`),
    topic: packet.title,
    durationMinutes: packet.duration_minutes,
    objectives: requireArray(packet.objectives, `${packet.packet_id}.objectives`),
    languageFocus: packet.objectives.join(" "),
    prerequisites: requireArray(packet.prerequisite_lesson_ids, `${packet.packet_id}.prerequisites`),
    sections: requireArray(packet.sections, `${packet.packet_id}.sections`).map((section, index) => ({
      id: `section-${index + 1}`,
      title: requireString(section.title, `${packet.packet_id}.section.title`),
      type: "explanation",
      body: requireString(section.body, `${packet.packet_id}.section.body`),
    })),
    exercises: requireArray(packet.exercises, `${packet.packet_id}.exercises`).map((exercise) => adaptGermanExercise(exercise, packet.packet_id)),
    practice: {
      listening: prompts.listening,
      speaking: prompts.speaking,
      pronunciation: prompts.pronunciation,
      writing: prompts.writing,
    },
    contentStatus: packet.content_status,
    provenance: packet.provenance,
    packetPath: sourceRecord.path,
    packetSha256: sourceRecord.sha256,
  };
}

export async function buildSnapshot() {
  const lessons = [];
  const sourceManifests = [];
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
          ? adaptGermanPacket(packet, source, record)
          : adaptEnglishPacket(packet, source, record),
      );
    }

    sourceManifests.push({
      language: source.language,
      band: source.band,
      path: source.manifest.replaceAll("\\", "/"),
      sha256: sha256(manifestBytes),
      declaredManifestSha256: manifest.manifest_sha256,
      packetCount: inventory.length,
    });
  }

  if (lessons.filter((lesson) => lesson.language === "en").length !== 300) fail("English inventory is not 300");
  if (lessons.filter((lesson) => lesson.language === "de").length !== 10) fail("German inventory is not 10");

  const payload = {
    schemaVersion: "1.0",
    contentStatus: "UNREVIEWED",
    sourceManifests,
    languages: [
      { code: "en", name: "English", lessonCount: 300, bands: ["A1", "A2", "B1", "B2", "C1", "C2"] },
      { code: "de", name: "German", lessonCount: 10, bands: ["A1"] },
    ],
    lessons,
  };
  return { ...payload, snapshotSha256: sha256(JSON.stringify(payload)) };
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
    console.log(`Verified deterministic snapshot ${snapshot.snapshotSha256} (${snapshot.lessons.length} lessons).`);
  } else {
    await mkdir(path.dirname(outputPath), { recursive: true });
    await writeFile(outputPath, serialized, "utf8");
    console.log(`Built deterministic snapshot ${snapshot.snapshotSha256} (${snapshot.lessons.length} lessons).`);
  }
}

if (process.argv[1] && path.resolve(process.argv[1]) === fileURLToPath(import.meta.url)) {
  await main();
}
