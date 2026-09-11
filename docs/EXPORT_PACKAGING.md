# M11 Export & Packaging

## Local-batch export

The active export path accepts one hash-bound local batch and emits JSON, CSV, static web, and static mobile output. Print HTML and IMS Common Cartridge are optional.

```bash
python -m english_master.export_packaging build-batch \
  --batch-input path/to/m11-export-batch-input.json \
  --repository-root . \
  --output-root data/exports \
  --exported-at <ISO-8601>

python -m english_master.export_packaging verify-batch \
  data/exports/<export-id> \
  --repository-root .
```

The batch contract verifies schema-valid artifacts, repository-contained paths, exact hashes, source redistribution permissions, closed input/output inventories, consistent `UNREVIEWED` lifecycle status, deterministic renderers, and atomic no-overwrite storage.

The default formats are deliberately small. Use `--include-print` and `--include-ims` only when those outputs are needed.

A passing batch verification is not human review, release approval, public-distribution authority, provider behavior, or pedagogical-quality evidence.

## Historical authority exporter

The `inspect-authority`, `build`, and `verify` commands retain the prior strict authority contract solely for existing immutable historical records. Their M9/M10 requirements do not apply to `build-batch`.
