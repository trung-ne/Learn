# M5 Independent Review and Approval Snapshots

## Purpose and boundary

This workflow lets qualified humans review the exact M5 outline architecture, its referenced taxonomy closure, and the Vietnamese learner annotations attached to that review target without editing the historical M5 source bundle. It is M5 governance infrastructure only. It does not approve or generate lesson content, exercises, prompts, or any M7 artifact.

The authoritative source records retain their committed states:

- `curriculum/structure.json` remains `OUTLINE_ONLY`;
- referenced taxonomy records remain `DRAFT`;
- `blocks_content_generation` remains `true`; and
- an approval snapshot is a separate, hash-bound review overlay, not a status mutation.

No committed approval snapshot is supplied by the project. Schema-valid automated output is not human approval.

The current M6 authorization contract does not yet load or hash-bind this new snapshot format. A real snapshot is therefore necessary governance evidence but is not yet a mechanically enforced M6 preflight input. Do not resume production lesson generation until M6 is explicitly bound to a verified real snapshot; the synthetic M6 fixtures are tests only.

## Roles and independence

Publication requires exactly two completed human submissions in this order:

1. `LINGUISTIC`
2. `PEDAGOGICAL`

They must use distinct normalized reviewer IDs. Reviewer IDs and evidence IDs are canonicalized with Unicode NFKC, surrounding-whitespace removal, and case folding. Provider subjects are different: person uniqueness uses `(normalized issuer, exact subject_id)` because a provider's subject identifiers may be case-sensitive. The same issuer/exact-subject pair cannot back two reviewer records, while equal subject text from different issuers is not assumed to identify one person.

Reviewer identity is not trusted from the review JSON itself. `publish` and `verify` require a separately loaded `curriculum-reviewer-registry.schema.json` authority supplied by the operator. Each normalized reviewer ID, display name, qualifications, permitted role, `VERIFIED` status, and evidence ID must match that registry. The registry carries externally checked identity evidence and is retained and hash-bound in the snapshot. The software verifies these bindings, but it cannot determine whether an issuer, directory, signature, manual check, or human claim is truthful. Establishing and protecting the registry is an explicit out-of-band trust responsibility; never let a reviewer supply or approve their own authority record.

Each person must also attest that they are independent of authorship, disclose conflicts, review all four artifact versions named by the manifest, review the exact referenced taxonomy closure and complete annotation scope, and bind the decision to the prepared manifest hash. The attestation covers the manifest and artifacts available at review time; it does not claim the reviewer saw the approval snapshot, which is constructed only after both reviews pass publication gates.

The linguistic checklist covers CEFR alignment, linguistic accuracy, dependency soundness, vocabulary-sense integrity, and Vietnamese learner relevance. The pedagogical checklist covers sequence, objective coherence, skill balance, review spirals, assessment alignment, and credibility of scope/hour estimates.

A snapshot cannot be published unless both decisions are `APPROVE`, every required check is `PASS`, and neither review contains a `MAJOR` or `CRITICAL` finding.

## Canonical hashes and identities

All hashes are SHA-256 over canonical parsed JSON values: UTF-8, keys sorted, compact separators, Unicode retained, and non-finite numbers rejected. Whitespace and object-key formatting do not affect a hash; semantic value changes do. Every JSON or YAML input to the review CLI—including all four M5 artifacts, submitted reviews, manifests, reviewer registries, and published approval records—is loaded with duplicate-key rejection at every mapping depth. Contradictory values can therefore never be hidden by last-key-wins parsing.

Identifiers are deterministic:

- `manifest_id` hashes the complete manifest except `manifest_id`;
- `review_id` hashes the complete finalized review except `review_id`;
- `registry_id` hashes the complete trusted reviewer registry except `registry_id`; and
- `snapshot_id` hashes the complete snapshot except `snapshot_id`.

These are unkeyed content hashes, not digital signatures. They provide deterministic addressing and detect accidental or internally inconsistent changes, but they cannot authenticate a reviewer or defeat an actor who can replace a complete bundle and recompute every hash. Operators must protect the trusted reviewer registry and an approved snapshot ID or digest in an independently controlled authenticated system, such as a signed source-control record or access-controlled write-once store. This workflow does not implement signature verification.

`manifest_sha256` and review-reference hashes cover the complete identified records. The manifest contains the actual normalized paths loaded by the CLI—including any graph, coverage, taxonomy, or source-registry path—plus schema mappings; hashes for structure, graph, coverage, taxonomy, the complete transitive taxonomy prerequisite closure referenced by M5, and every reviewed Vietnamese learner annotation; and the source registry's schema version and complete canonical hash. Taxonomy records authorized by an approval and reviewed annotations are separate arrays: annotation review provides governed learner-context evidence but never makes an annotation a lesson-generation authority. The workflow reloads every claimed artifact and source-registry path and rejects a caller-supplied value that differs from the file, so a library caller cannot attach an arbitrary path label to different data. Inputs under the structure directory use relative POSIX paths; external inputs use `..`-relative paths, or a file URI when a cross-volume relative path is unavailable. An override can therefore never retain a misleading default label. The approval snapshot repeats the source-registry binding, while the published bundle retains the exact parsed registry as `source-registry.json`.

The manifest also binds `M5_INDEPENDENT_REVIEW_V2`, semantic-validator and canonicalization profile versions, both exact role checklists, and canonical hashes for the transitive local JSON Schema dependency closure used by M5 review. Changes to those rules or schemas therefore produce a different manifest rather than silently reinterpreting an existing review target.

Every command independently and strictly loads the operator-supplied source registry. Before preparing, publishing, or verifying, the workflow validates the registry schema and duplicate source IDs, then checks every citation in the manifest's referenced taxonomy and annotation scopes. Externally grounded evidence must name a source. A cited source is eligible only when it exists, has status `APPROVED` or `REFERENCE_ONLY`, grants `permissions.reference_allowed: true`, and the citation URL falls under one of its explicit `taxonomy_reference_url_prefixes` (or its primary `source_url` when no override is declared). If a registered prefix contains a query string, the citation query must match exactly; this prevents a record-specific locator from authorizing a different record on the same path. Unknown, missing, mislabeled, `QUARANTINED`, `REJECTED`, reference-denied, malformed, drifted, or tampered source authority fails closed. Citation eligibility never grants ingestion, copying, transformation, exercise use, or redistribution rights. Unreferenced taxonomy records are not approved by this snapshot and remain outside this approval gate.

## Workflow

### 1. Prepare

Validate M5 and atomically publish a new immutable manifest directory:

```bash
python -m english_master.curriculum_review prepare curriculum/structure.json \
  --source-registry sources/registry.yaml \
  --output data/reviews/m5/prepared/<review-cycle-id>
```

The output contains only `manifest.json`. Preparing a manifest is not review or approval. Reviewers use the blank forms in `docs/templates/`, inspect the files named and hashed by the manifest, then create completed draft JSON submissions matching `curriculum-independent-review-draft.schema.json`. Validate a canonical draft with:

```bash
python -m english_master.schema_validation --schema curriculum-independent-review-draft <completed-review-draft.json>
```

The draft schema intentionally forbids `review_id`. `publish` normalizes reviewer and evidence IDs, validates the draft, derives `review_id`, validates the finalized record against `curriculum-independent-review.schema.json`, and refuses a conflicting ID on an already-finalized input.

### 2. Publish

After both humans complete their independent submissions:

```bash
python -m english_master.curriculum_review publish curriculum/structure.json \
  --source-registry sources/registry.yaml \
  --manifest data/reviews/m5/prepared/<review-cycle-id>/manifest.json \
  --linguistic-review <completed-linguistic-review.json> \
  --pedagogical-review <completed-pedagogical-review.json> \
  --reviewer-registry <trusted-reviewer-registry.json> \
  --approved-at <trusted-RFC3339-publication-time> \
  --published-by <administrative-publisher-id> \
  --output data/reviews/m5/approved/<snapshot-id>
```

The trusted publisher timestamp must include a known timezone offset, cannot precede either `reviewed_at` timestamp or cited-source authority, and cannot be later than the trusted publication clock. Reviewer identity evidence and reviewer-registry issuance must precede review use; source registration, license review, and evidence checks must not follow the source's recorded review, and cited-source review must precede both human reviews. Chronology comparisons preserve every supplied fractional-second digit. RFC 3339's unknown-local-offset form `-00:00`, leap seconds unsupported by the runtime, and any other timestamp that cannot be ordered fail both the standalone review schemas and semantic publication checks. Publication revalidates M5, the independently loaded source registry, taxonomy citation eligibility, all hashes, exact scopes, external reviewer authority, human attestations, checklist outcomes, findings, roles, and reviewer separation. It then atomically publishes exactly:

```text
manifest.json
review-linguistic.json
review-pedagogical.json
reviewer-registry.json
source-registry.json
snapshot.json
```

The destination is checked before staging and must not already exist; the exclusive rename remains the race-safe commit check. The complete directory becomes visible at one no-replace rename commit point, and pre-commit failures clean staging files. POSIX publication fsyncs the staged directory and parent directory. A post-commit parent-fsync failure is reported explicitly while identifying that the destination is already visible; it is never silently converted to success or rejection. Windows has no supported directory-fsync primitive in this profile, so that specific durability step is an explicit no-op there.

The M5 implementation keeps its canonicalization and atomic-publication profile in `english_master.curriculum_review` rather than importing from the later M6 `lesson_generation` package. This avoids a backwards M5-to-M6 dependency and changing already verified M6 code. The algorithms intentionally match the established M6 primitives; future consolidation should move both to a milestone-neutral shared module in a separately scoped refactor.

### 3. Verify

Recheck a published snapshot against current M5 values:

```bash
python -m english_master.curriculum_review verify curriculum/structure.json \
  --source-registry sources/registry.yaml \
  --snapshot data/reviews/m5/approved/<snapshot-id> \
  --reviewer-registry <trusted-reviewer-registry.json>
```

Any source-value change, source-registry path/value/version drift, newly ineligible taxonomy or annotation citation, retained source-registry mismatch, taxonomy/annotation scope drift, internally inconsistent review hash, unexpected bundle member, ID mismatch, failed M5 invariant, or incomplete strict taxonomy overlay fails closed. Verification compares the retained `source-registry.json` with the independently loaded current registry and also reconstructs both manifest and snapshot bindings. Detecting coordinated replacement additionally requires the independently protected snapshot ID or digest described above.

`--source-registry` is mandatory on all commands so authority is never inferred from the manifest or retained snapshot. Optional `--graph`, `--coverage`, and `--taxonomy` overrides are available on all commands for controlled testing or alternate bundle locations.

## Outcomes, revision, and retention

- `APPROVE`: eligible for mechanical publication only when every gate passes.
- `REQUEST_CHANGES`: blocks publication; revise M5 through normal source control, prepare a new manifest, and obtain fresh reviews.
- `REJECT`: blocks publication; retain the human submission in the governed review system if policy requires it, but it cannot be placed in an approved snapshot.

Never overwrite a prepared or approved directory. A changed artifact necessarily has a new manifest and snapshot identity. Supersession is represented by retaining prior immutable bundles and separately selecting the current approved snapshot; this implementation does not silently archive or delete evidence.

## Exit codes

- `0`: prepare, publish, or verify succeeded.
- `1`: semantic/schema/review gate failed.
- `2`: setup, malformed-input, or immutable-publication failure.

All operations are local and offline.
