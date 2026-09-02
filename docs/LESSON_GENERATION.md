# M6 Lesson Generation

## Status and boundary

The constrained M6 generator repair is implemented and covered by offline tests. This is pipeline infrastructure, not completed lesson production. The repository still has no set of ten independently reviewed lessons, no manual language-quality review output, and no M6-approved lesson content. Generated fixture output remains `UNREVIEWED`.

M6 produces one lesson JSON record from separately loaded M5 artifacts, an independent authorization, a source registry, and a bounded request. It does not generate exercises, answer keys, assessments, AI practice prompts, media, UI, or approval decisions.

## Authoritative inputs

The request is not its own authority. `LessonGenerationAuthority` separately loads:

- `curriculum/structure.json`;
- its declared prerequisite graph, coverage roadmap, and taxonomy;
- an independent M6 authorization record; and
- `sources/registry.yaml`.

The request and authorization must pin canonical hashes for all five artifacts. M5 validation is reused in strict mode for the exact referenced taxonomy closure. The authorization must name the lesson, match the pinned taxonomy records byte-for-byte through record hashes, and document an independent `APPROVED_FOR_M6_GENERATION` decision.

The committed M5 bundle remains `OUTLINE_ONLY`; its taxonomy remains `DRAFT`, and its own gate blocks content generation. It does not become authorized merely because it passes M5 architecture validation. The test success authorization is a separate project-authored fixture review overlay bound to the exact committed artifact hashes and all seven records required by its lesson allocation (including five supporting taxonomy concepts). A missing, stale, malformed, incomplete, or mismatched authorization fails before the backend is called.

## Derived graph and identity contracts

M6 derives and checks, rather than trusts:

- lesson order and direct/transitive lesson prerequisites;
- incoming lesson-to-lesson review edges for the target and target introduction edges;
- previous knowledge from earlier authoritative introduction edges;
- every lesson `taxonomy_concepts` allocation and the full taxonomy prerequisite closure; and
- the target lesson's identity, parent unit, number, CEFR tier, objectives, and allocated references.

Missing, reversed, fabricated, stale, or surplus declarations are rejected. Shared common-schema contracts govern tier-qualified unit IDs, lesson IDs, concept IDs, and vocabulary-sense IDs. Semantic checks also reconcile the CEFR band/tier and numeric suffixes across lesson and unit fields.

## Provenance authorization

Project-authored records require explicit independent approval and an exact pinned taxonomy-record hash. External records additionally require complete provenance, the authorized source payload, a matching SHA-256 over its UTF-8 bytes, sufficient attribution, and resolution against the independently loaded source registry. M6 checks source registration, `APPROVED` status, identity, license name and URL, and the reference/transform/redistribution permissions applicable to the declared content type. Caller-supplied authorization booleans are not accepted.

## Backend and trusted metadata

The backend may return only `content_sections`. The orchestration layer injects all trusted fields:

- lesson identity, parent, tier, objectives, references, and prerequisites;
- schema, curriculum, generator, model, and prompt versions;
- trusted generation timestamp;
- an empty M7 `exercises` array; and
- `qa_status: UNREVIEWED` with the independent-review notice.

Non-object, non-finite, noncanonical, or over-scoped backend values are controlled rejections before unsafe hashing or publication. Section bounds and forbidden-term checks cover both titles and bodies. Byte-identical reproducibility is claimed only when the concrete backend explicitly declares that capability, never from caller-supplied provider metadata.

## Audit and storage

Check outcomes are stage-aware: `PASS`, `FAIL`, or `NOT_RUN`. A failed preflight cannot report skipped backend or lesson checks as successful. Audits include the automated reviewer, timestamp, outcome, checks performed, issues, and explicit outstanding independent CEFR, grammar/lexical, language-quality, and pedagogical reviews.

Accepted `lesson.json` and `audit.json` are published together using an atomic platform no-replace operation. Rejected `rejection.json` and `audit.json` use the same immutable directory-bundle mechanism. Concurrent destinations are never replaced. The exclusive rename is the publication commit point; a later POSIX parent-directory fsync is best-effort because the complete bundle is already visible and cannot truthfully be reported as rejected. Pre-commit publication and rejection-persistence failures are reported as publication-stage failures; invalid output never creates a partial lesson bundle.

## Offline CLI

The successful fixture path is fully offline:

```bash
python -m english_master.lesson_generate \
  --request tests/fixtures/m6/approved-request.json \
  --authorization tests/fixtures/m6/approved-authorization.json \
  --mock-response tests/fixtures/m6/approved-mock-lesson.json \
  --output-dir data/generated/m6/A1-U01-L01 \
  --rejection-dir data/reports/m6/A1-U01-L01-rejection
```

The authoritative structure and source registry default to the committed paths. `--graph`, `--coverage`, and `--taxonomy` exist only to load a complete alternate pinned bundle; every override changes the required artifact hashes.

Exit codes are `0` for accepted publication, `1` for a validated generation rejection, and `2` for setup or persistence failure. Output directories are immutable.

Validate records offline with:

```bash
python -m english_master.schema_validation --schema lesson-generation-authorization tests/fixtures/m6/approved-authorization.json
python -m english_master.schema_validation --schema lesson-generation-request tests/fixtures/m6/approved-request.json
```

The mock response is deliberately a backend-content fragment, not a final lesson record; the CLI assembles and validates the final lesson.
