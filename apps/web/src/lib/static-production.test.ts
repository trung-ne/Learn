import path from "node:path";
import { describe, expect, it } from "vitest";
import { routeUrl, serviceWorkerSource } from "../../scripts/build-service-worker.mjs";
import { cacheControlFor, responseHeaders, safePath } from "../../scripts/serve-static.mjs";

describe("static cache and preview policies", () => {
  it("maps exported index documents to stable route URLs and generates a versioned worker", () => {
    expect(routeUrl("index.html")).toBe("/");
    expect(routeUrl("learn/en/index.html")).toBe("/learn/en/");
    const worker = serviceWorkerSource({
      version: "test-version",
      shell: ["/", "/_next/static/app.js"],
      routes: ["/", "/learn/en/A1/review/", "/learn/en/A1/U01/L01/"],
    });
    expect(worker).toContain("english-master-static-test-version");
    expect(worker).toContain('REVIEW_ROUTES = ["/learn/en/A1/review/"]');
    expect(worker).toContain("return REVIEW_ROUTES.includes(pathname)");
    expect(worker).toContain("response.ok && ROUTES.includes(pathname)");
  });

  it("uses immutable headers only for fingerprinted Next assets", () => {
    expect(cacheControlFor("_next/static/chunks/app-123.js")).toContain("immutable");
    expect(cacheControlFor("learn/index.html")).toBe("no-cache");
    expect(cacheControlFor("manifest.webmanifest")).toBe("no-cache");
    const root = path.resolve("out");
    expect(safePath(root, "/../secret")).toBeNull();
    expect(responseHeaders(root, path.join(root, "_next/static/app.js"))["Content-Security-Policy"]).toContain("frame-ancestors 'none'");
  });
});
