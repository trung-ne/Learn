import { createHash } from "node:crypto";
import { mkdir, readdir, readFile, writeFile } from "node:fs/promises";
import path from "node:path";
import { fileURLToPath } from "node:url";

const directory = path.dirname(fileURLToPath(import.meta.url));
export const outputDirectory = path.resolve(directory, "../out");

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

export function routeUrl(file) {
  if (file === "index.html") return "/";
  if (file.endsWith("/index.html")) return `/${file.slice(0, -"index.html".length)}`;
  return `/${file}`;
}

export async function buildCacheManifest(root = outputDirectory) {
  const files = (await filesUnder(root)).filter((file) => file !== "sw.js" && file !== "cache-manifest.json" && file !== "static-output-report.json").sort();
  const assets = files.filter((file) => file.startsWith("_next/static/") || file === "manifest.webmanifest" || file.startsWith("icons/"));
  const routes = files.filter((file) => file === "index.html" || file.endsWith("/index.html")).map(routeUrl);
  const shellRoutes = ["/", "/learn/", "/data/", "/offline/"].filter((url) => routes.includes(url));
  const hash = createHash("sha256");
  for (const file of files) {
    hash.update(file);
    hash.update(await readFile(path.join(root, file)));
  }
  return {
    version: hash.digest("hex").slice(0, 20),
    shell: [...shellRoutes, ...assets.map((file) => `/${file}`)].sort(),
    routes,
  };
}

export function serviceWorkerSource(manifest) {
  const reviewRoutes = manifest.routes.filter((route) => /^\/learn\/(?:en|de)\/(?:A1|A2|B1|B2|C1|C2)\/review\/$/u.test(route));
  return `/* Generated from the static export. Do not edit manually. */
const CACHE_NAME = "english-master-static-${manifest.version}";
const SHELL = ${JSON.stringify(manifest.shell)};
const ROUTES = ${JSON.stringify(manifest.routes)};
const REVIEW_ROUTES = ${JSON.stringify(reviewRoutes)};
const OFFLINE_ROUTE = "/offline/";

self.addEventListener("install", (event) => {
  event.waitUntil(caches.open(CACHE_NAME).then((cache) => cache.addAll(SHELL)));
});

self.addEventListener("activate", (event) => {
  event.waitUntil(caches.keys().then((keys) => Promise.all(keys
    .filter((key) => key.startsWith("english-master-static-") && key !== CACHE_NAME)
    .map((key) => caches.delete(key)))).then(() => self.clients.claim()));
});

async function cachedNavigation(request) {
  const cache = await caches.open(CACHE_NAME);
  const url = new URL(request.url);
  const pathname = url.pathname.endsWith("/") ? url.pathname : url.pathname + "/";
  const cached = await cache.match(pathname);
  if (cached) return cached;
  try {
    const response = await fetch(request);
    if (response.ok && ROUTES.includes(pathname)) cache.put(pathname, response.clone());
    return response;
  } catch {
    return (await cache.match(OFFLINE_ROUTE)) || new Response("Offline", { status: 503, headers: { "Content-Type": "text/plain; charset=utf-8" } });
  }
}

self.addEventListener("fetch", (event) => {
  const request = event.request;
  if (request.method !== "GET" || new URL(request.url).origin !== self.location.origin) return;
  if (request.mode === "navigate") {
    event.respondWith(cachedNavigation(request));
    return;
  }
  event.respondWith(caches.match(request).then((cached) => cached || fetch(request).then((response) => {
    if (response.ok && new URL(request.url).pathname.startsWith("/_next/static/")) {
      caches.open(CACHE_NAME).then((cache) => cache.put(request, response.clone()));
    }
    return response;
  })));
});

function reviewRoute(value) {
  if (typeof value !== "string" || !value.startsWith("/") || value.includes("://") || value.includes("?") || value.includes("#")) return undefined;
  const pathname = value.endsWith("/") ? value : value + "/";
  return REVIEW_ROUTES.includes(pathname) ? pathname : undefined;
}

function reply(port, result) {
  if (port) port.postMessage(result);
}

self.addEventListener("message", (event) => {
  const data = event.data;
  if (!data || typeof data !== "object") return;
  if (data.type === "skip-waiting") {
    self.skipWaiting();
    return;
  }
  const path = reviewRoute(data.path);
  const port = event.ports[0];
  if (!path || (data.type !== "cache-route" && data.type !== "remove-route")) {
    reply(port, { ok: false });
    return;
  }
  if (data.type === "cache-route") {
    event.waitUntil(caches.open(CACHE_NAME).then((cache) => cache.add(path)).then(() => reply(port, { ok: true, cached: true })).catch(() => reply(port, { ok: false })));
    return;
  }
  event.waitUntil(caches.open(CACHE_NAME).then((cache) => cache.delete(path)).then(() => reply(port, { ok: true, cached: false })).catch(() => reply(port, { ok: false })));
});
`;
}

export async function writeServiceWorker(root = outputDirectory) {
  const manifest = await buildCacheManifest(root);
  await mkdir(root, { recursive: true });
  await writeFile(path.join(root, "cache-manifest.json"), `${JSON.stringify(manifest, null, 2)}\n`);
  await writeFile(path.join(root, "sw.js"), serviceWorkerSource(manifest));
  console.log(`Generated static cache manifest ${manifest.version} with ${manifest.shell.length} shell resource(s).`);
  return manifest;
}

if (process.argv[1] === fileURLToPath(import.meta.url)) await writeServiceWorker();
