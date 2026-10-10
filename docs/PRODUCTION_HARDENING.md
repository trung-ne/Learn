# Production Hardening

## Scope

Step 13.17 hardens the static learner web application without changing its privacy and content boundaries. The app remains a static export with browser-local learner state. It does not add accounts, server routes, a database, live AI, audio recording, analytics, remote error reporting, media authorization, or public-distribution authority.

All learner content remains `UNREVIEWED`. A static build, an offline cache, or a successful local backup does not establish pedagogical quality, CEFR suitability, provider behavior, approval, release authority, or distribution permission.

## Static performance and caching

The production build verifies its deterministic content snapshots before export. After the static export, it emits:

- a versioned same-origin service worker and cache manifest;
- a deterministic static-output size report; and
- no fetched runtime curriculum or external font/analytics assets.

The worker precaches only the application shell, manifest/icons, and fingerprinted Next assets. It does not silently cache an entire course, cross-origin resources, learner state, or unavailable media. A learner can explicitly save the review page they are currently viewing for offline use and remove that local offline copy later.

HTML, the web manifest, cache manifest, and service-worker entrypoint must revalidate. Fingerprinted `/_next/static/` assets can use long immutable caching. Other assets receive conservative caching unless they are explicitly versioned. The local preview server applies this policy for testing; production hosting must apply an equivalent edge policy.

## Offline and update behavior

Service-worker registration occurs only in a secure context or on localhost. The UI does not claim install/offline support until registration succeeds. A waiting update is shown to the learner; activation and reload require an explicit **Update and reload** action. The worker does not automatically replace a cached version during study.

Current listening remains `NO_AUTHORIZED_MEDIA`. A service worker does not grant media rights. Future audio caching is possible only for explicit, same-origin, permission-bound media entries with a source-approved browser-delivery contract; it must be learner initiated and removable.

## Browser-local data and recovery

Progress, review state, assessment drafts, writing drafts, and local preferences remain in this browser. They can be lost if browser data is cleared, private browsing ends, local storage is unavailable, quota is exhausted, or the learner changes devices. A browser-local backup is not account sync, durable backup, or a recovery guarantee.

The **Data and offline tools** page provides explicit export, validate-before-write restore, and confirmed local reset actions. Backup envelopes allow only English Master storage keys and bounded JSON records. Restore rejects unknown, malformed, unsupported, or oversized records and does not change unrelated browser storage. Backup files can contain learner-authored writing drafts and a browser-local learner identifier; learners must store them safely.

The app displays a local storage warning when a monitored write/remove/import fails. It does not transmit diagnostic or learner data. Local diagnostics are bounded/sanitized and may only be explicitly exported by a learner in a future support interaction; they are not analytics.

## Security headers and static preview

`npm start` is a local static-preview server, not a production edge. It binds only to IPv4 loopback (`127.0.0.1`), accepts only `GET` and `HEAD`, prevents traversal, emits appropriate MIME and cache headers, and adds:

- restrictive same-origin Content Security Policy;
- `X-Content-Type-Options: nosniff`;
- `X-Frame-Options: DENY` and CSP `frame-ancestors 'none'`;
- `Referrer-Policy: no-referrer`;
- restrictive `Permissions-Policy`; and
- `Cross-Origin-Resource-Policy: same-origin`.

The local HTTP preview intentionally does **not** emit HSTS. A real managed static host/CDN must enforce HTTPS redirect and, only after a real HTTPS domain is operational, HSTS. The host must separately validate its final CSP against the actual generated app and retain atomic versioned releases with rollback.

## Remote operational features not present today

- **Rate limiting:** there are no application endpoints. Browser-side throttling would not protect a future API. A future API, upload, authentication, provider proxy, or media-token service requires edge limits, request-size limits, identity-aware quotas where applicable, and abuse monitoring from its initial design.
- **AI cost control:** the app calls no provider and has no runtime AI cost. Stored prompts copied by the learner do not invoke an English Master provider. Future AI use requires server-side secret isolation, explicit budget ceilings, request/output caps, retry policy, and a privacy/retention design.
- **Analytics and remote error monitoring:** none are added. Use host/CDN operational signals only (availability, TLS, HTTP status, cache behavior, bandwidth, deployment errors) and do not collect learner answers, drafts, local identifiers, session replay, or audio without a separate data-policy decision.
- **Audio caching:** no playable audio is currently shipped. Do not infer authorization from transcript-only practice or local cache capability.

## Managed hosting and release contract

A future deployment should use an immutable static release on a managed host/CDN rather than treating the preview server as the Internet-facing security boundary. Before deployment, verify the exact artifact digest, source commit, Node version, content snapshot checks, static export, cache/security headers, deep links, update/rollback behavior, offline fallback, mobile keyboard flow, and accessibility checks.

Public hosting requires an independent authorization decision for every artifact. It is outside this step and is not granted by this documentation or any validation result.

## Validation

Use a pinned app-local lockfile and `npm ci` when dependencies are available. The normal static-app gate is snapshot checks, lint, strict type checking, Vitest, static build, local server header/deep-link checks, and accessibility/responsive smoke checks. Dependency audit/SBOM and CI configuration are follow-up operational actions once deterministic installation is available.
