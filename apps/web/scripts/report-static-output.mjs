import { readdir, stat, writeFile } from "node:fs/promises";
import path from "node:path";
import { fileURLToPath } from "node:url";
import { outputDirectory } from "./build-service-worker.mjs";

async function filesUnder(root, relative = "") {
  const entries = await readdir(path.join(root, relative), { withFileTypes: true });
  const files = [];
  for (const entry of entries) {
    const entryPath = path.join(relative, entry.name);
    if (entry.isDirectory()) files.push(...await filesUnder(root, entryPath));
    else if (entry.isFile()) files.push(entryPath.replaceAll(path.sep, "/"));
  }
  return files;
}

export async function staticOutputReport(root = outputDirectory) {
  const files = (await filesUnder(root)).sort();
  const sizes = await Promise.all(files.map(async (file) => ({ file, bytes: (await stat(path.join(root, file))).size })));
  const categoryBytes = (predicate) => sizes.filter(({ file }) => predicate(file)).reduce((total, { bytes }) => total + bytes, 0);
  const report = {
    schemaVersion: 1,
    totalBytes: sizes.reduce((total, { bytes }) => total + bytes, 0),
    fileCount: sizes.length,
    routeHtmlCount: sizes.filter(({ file }) => file === "index.html" || file.endsWith("/index.html")).length,
    javascriptBytes: categoryBytes((file) => file.endsWith(".js")),
    cssBytes: categoryBytes((file) => file.endsWith(".css")),
    localMediaBytes: categoryBytes((file) => /\.(?:mp3|m4a|ogg|wav|mp4|webm)$/u.test(file)),
    largestFiles: sizes.sort((left, right) => right.bytes - left.bytes || left.file.localeCompare(right.file)).slice(0, 20),
  };
  await writeFile(path.join(root, "static-output-report.json"), `${JSON.stringify(report, null, 2)}\n`);
  console.log(`Static output report: ${report.fileCount} files, ${report.totalBytes} bytes, ${report.routeHtmlCount} HTML routes.`);
  return report;
}

if (process.argv[1] === fileURLToPath(import.meta.url)) await staticOutputReport();
