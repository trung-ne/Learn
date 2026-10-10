import { createReadStream } from "node:fs";
import { access, stat } from "node:fs/promises";
import { createServer } from "node:http";
import path from "node:path";
import { fileURLToPath } from "node:url";

export const contentTypes = {
  ".avif": "image/avif",
  ".css": "text/css; charset=utf-8",
  ".html": "text/html; charset=utf-8",
  ".ico": "image/x-icon",
  ".js": "text/javascript; charset=utf-8",
  ".json": "application/json; charset=utf-8",
  ".m4a": "audio/mp4",
  ".mp3": "audio/mpeg",
  ".ogg": "audio/ogg",
  ".png": "image/png",
  ".svg": "image/svg+xml",
  ".ttf": "font/ttf",
  ".txt": "text/plain; charset=utf-8",
  ".webmanifest": "application/manifest+json; charset=utf-8",
  ".webm": "video/webm",
  ".woff": "font/woff",
  ".woff2": "font/woff2",
};

export const securityHeaders = {
  "Content-Security-Policy": "default-src 'self'; base-uri 'self'; connect-src 'self'; font-src 'self'; form-action 'self'; frame-ancestors 'none'; img-src 'self' data:; manifest-src 'self'; media-src 'self'; object-src 'none'; script-src 'self' 'unsafe-inline'; style-src 'self' 'unsafe-inline'; worker-src 'self'",
  "Cross-Origin-Resource-Policy": "same-origin",
  "Permissions-Policy": "accelerometer=(), camera=(), geolocation=(), gyroscope=(), microphone=(), payment=(), usb=()",
  "Referrer-Policy": "no-referrer",
  "X-Content-Type-Options": "nosniff",
  "X-Frame-Options": "DENY",
};

export function cacheControlFor(relativePath) {
  if (relativePath.startsWith("_next/static/")) return "public, max-age=31536000, immutable";
  if (relativePath.endsWith(".html") || relativePath === "sw.js" || relativePath === "manifest.webmanifest" || relativePath === "cache-manifest.json") return "no-cache";
  return "public, max-age=3600";
}

export function safePath(root, urlPath) {
  let pathname;
  try {
    pathname = decodeURIComponent(urlPath.split("?")[0]);
  } catch {
    return null;
  }
  const relative = pathname === "/" ? "index.html" : pathname.replace(/^\/+/, "");
  const candidate = path.resolve(root, relative);
  if (candidate !== root && !candidate.startsWith(`${root}${path.sep}`)) return null;
  return candidate;
}

export function responseHeaders(root, target) {
  const relativePath = path.relative(root, target).replaceAll(path.sep, "/");
  return {
    "Cache-Control": cacheControlFor(relativePath),
    "Content-Type": contentTypes[path.extname(target)] ?? "application/octet-stream",
    ...securityHeaders,
  };
}

export function createStaticServer(root = path.resolve("out")) {
  return createServer(async (request, response) => {
    if (request.method !== "GET" && request.method !== "HEAD") {
      response.writeHead(405, { Allow: "GET, HEAD", ...securityHeaders }).end("Method not allowed");
      return;
    }
    const candidate = safePath(root, request.url ?? "/");
    if (!candidate) {
      response.writeHead(400, securityHeaders).end("Bad request");
      return;
    }
    let target = candidate;
    try {
      const details = await stat(target);
      if (details.isDirectory()) target = path.join(target, "index.html");
      await access(target);
    } catch {
      response.writeHead(404, securityHeaders).end("Not found");
      return;
    }
    response.writeHead(200, responseHeaders(root, target));
    if (request.method === "HEAD") {
      response.end();
      return;
    }
    createReadStream(target).pipe(response);
  });
}

const isEntrypoint = process.argv[1] === fileURLToPath(import.meta.url);
if (isEntrypoint) {
  const port = Number(process.env.PORT ?? 3000);
  const server = createStaticServer();
  server.listen(port, "127.0.0.1", () => console.log(`Serving static app preview at http://127.0.0.1:${port}`));
}
