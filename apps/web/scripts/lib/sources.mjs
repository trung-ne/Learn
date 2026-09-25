import path from "node:path";
import { fileURLToPath } from "node:url";

const scriptDirectory = path.dirname(fileURLToPath(import.meta.url));

export const repositoryRoot = path.resolve(scriptDirectory, "../../../../");

export const sources = [
  {
    language: "en",
    languageName: "English",
    band: "A1",
    manifest: "curriculum/a1-full/v1/runs/a1full_a45a6b574127a4328b518da37be8f15ac83696d3ae77b0af4ff1e637740edc87/manifest.json",
    expectedCount: 50,
  },
  {
    language: "en",
    languageName: "English",
    band: "A2",
    manifest: "curriculum/a2-full/v1/runs/a2full_9855332711d456bd54e38eea6d83400629e1dd29725533f22687a98c23499833/manifest.json",
    expectedCount: 50,
  },
  {
    language: "en",
    languageName: "English",
    band: "B1",
    manifest: "curriculum/b1-full/v1/runs/b1full_e374b17202742db639b0a4dcda188995b9366ab01b3f5f897bb128b4d543b95c/manifest.json",
    expectedCount: 50,
  },
  {
    language: "en",
    languageName: "English",
    band: "B2",
    manifest: "curriculum/b2-full/v1/runs/b2full_2baff83eaca7c530d364fcc81f6d69261dbe3a1e3a2bb1c1009c1411e4a0d2ec/manifest.json",
    expectedCount: 50,
  },
  {
    language: "en",
    languageName: "English",
    band: "C1",
    manifest: "curriculum/c1-full/v1/runs/c1full_17d6807f312a392a98fb6fac4d83f84e75e9b24f19faa3b420bbc9f03ccd9f1c/manifest.json",
    expectedCount: 50,
  },
  {
    language: "en",
    languageName: "English",
    band: "C2",
    manifest: "curriculum/c2-full/v1/runs/c2full_770443bc0757a702f6d273de7fbf26e41bca701ad0123662b7f0aefb33369b83/manifest.json",
    expectedCount: 50,
  },
  {
    language: "de",
    languageName: "German",
    band: "A1",
    manifest: "course/de/a1/runs/dea1pilot_078dd4b3e746d82f6f382e50ab7f17b84414e07cb6a1a089dcd73cf7c17cd6ee/manifest.json",
    expectedCount: 10,
  },
];
