# Data Policy — English Master

## Overview

This document defines how external data is handled throughout the English Master project.

---

## Source Registration

Every external data source must be registered in `sources/` before ingestion.

Registration includes:

- source_name: human-readable name
- source_type: dataset | API | dump | crawlable | other
- source_url: primary URL or homepage
- status: APPROVED | REFERENCE_ONLY | QUARANTINED | REJECTED
- license: identified license identifier; use `UNKNOWN` only while status is QUARANTINED
- license_url: link to license text when the license is identified
- terms_of_use: any specific ToS that apply
- registered_at: date registered
- registered_by: person or agent who registered
- notes: special considerations

---

## License Handling

### Permitted Sources

- Public domain works
- Creative Commons licenses (CC0, CC-BY, CC-BY-SA with proper attribution)
- Official open datasets with explicit permission
- Works where copyright holders have granted permission
- Official APIs with terms permitting educational use

### Prohibited Sources

- Copyrighted educational materials without license
- Paywalled content accessed without authorization
- Content behind authentication accessed without permission
- Materials with "no commercial use" restrictions (unless purely educational)
- Content explicitly marked for non-redistribution

### Unknown Licensing

If a source's license is unclear or unstated:

**Default status: QUARANTINED**

Do not ingest quarantined content.

Do not generate new content based on quarantined material.

Quarantined sources may be studied for reference purposes only.

---

## Permitted Ingestion Methods

### Prefer

- Official data downloads from primary sources
- Official REST/GraphQL APIs with documented limits
- Official data exports and dumps
- Academic repositories with clear licensing (eg. Zenodo, OSF)
- Public Wikipedia dumps (with CC-BY-SA compliance)

### Prohibited

Never bypass:

- HTTP authentication
- Request rate limits (imposed as access control)
- robots.txt restrictions
- Captcha systems
- Paywalls or login requirements
- Geographic IP restrictions
- Terms of service that explicitly forbid automated access

### Gray Areas

Scraping is permitted only when:

- Terms of service explicitly allow it, OR
- Content is explicitly in the public domain, OR
- Source author grants permission

In doubt: inquire or register as QUARANTINED.

---

## Provenance

Every record ingested from external sources must retain:

### Minimum Provenance Fields

- source_id: registered source identifier
- source_name: name of source
- source_url: where data originated
- source_record_id: unique ID in source system
- retrieved_at: ISO 8601 timestamp
- retrieved_by: script/agent name
- license: license applicable to this record
- attribution: required attribution text
- content_hash: SHA-256 of original content
- ingestion_version: version of ingestion process

### Example

```json
{
  "vocabulary_entry": {
    "word": "hello",
    "definition": "..."
  },
  "provenance": {
    "source_id": "src_001",
    "source_name": "Example Dictionary",
    "source_url": "https://example.com/api/dict",
    "source_record_id": "entry_12345",
    "retrieved_at": "2026-08-28T10:30:00Z",
    "retrieved_by": "ingestion/v1",
    "license": "CC-BY-SA-4.0",
    "attribution": "Dictionary Widget",
    "content_hash": "abc123...",
    "ingestion_version": "1.0"
  }
}
```

---

## Generated Content

Content produced by the generator must retain:

- generator: name/ID of generator
- generator_version: version of generator
- model: language model or tool used (if known)
- prompt_version: version of prompt template
- generated_at: ISO 8601 timestamp
- curriculum_version: curriculum schema version used
- qa_status: UNREVIEWED | IN_REVIEW | NEEDS_REVISION | REVISION_SUBMITTED | APPROVED | REJECTED | ARCHIVED
- qa_notes: reviewer feedback

### Example

```json
{
  "exercise": { ... },
  "generation_metadata": {
    "generator": "exercise_generator_v1",
    "model": "claude-3-5-sonnet",
    "prompt_version": "ex_prompt_v2",
    "generated_at": "2026-08-28T11:00:00Z",
    "curriculum_version": "1.0",
    "qa_status": "APPROVED",
    "qa_notes": "Reviewed by human educator"
  }
}
```

---

## Quarantine

### What Gets Quarantined

Quarantined source metadata and review notes remain in `sources/`; future payloads remain separately stored in `data/quarantine/`. Neither may be used in approved materials or generated content until the source becomes `APPROVED`.

- Content with unknown or unclear licensing
- Sources that do not respond to permission inquiries
- Content marked copyright without clear redistribution rights
- Materials whose status changed after ingestion

### Handling Quarantined Content

- Store separately in data/quarantine/
- Tag with reason for quarantine
- Never include in approved materials
- May be used for internal reference/study
- Review periodically for potential approval

### Releasing from Quarantine

Quarantine status changes to APPROVED only when:

- License is definitively identified and verified
- Permission is obtained from rights holder
- Content is confirmed to be in public domain
- New authoritative source is found

---

## Raw Data

### Ingestion

Raw data is downloaded or exported from sources and stored in:

data/raw/{source_id}/{timestamp}/

### Retention

Raw data should be:

- Retained during active usage
- Not committed to Git by default
- Listed in .gitignore
- Documented with retrieval scripts

### Removal

Raw data may be deleted when:

- Normalized versions exist in data/approved/
- Source provides archive/history
- Storage becomes a constraint

---

## Normalized Data

Normalized data (cleaned, deduplicated, schema-validated) is stored in:

data/normalized/{source_id}/

---

## Approved Data

Data approved for use in curriculum:

data/approved/

Only APPROVED sources contribute to approved data.

---

## Copyright Safety

### Never

- Copy entire textbooks or courses without permission
- Claim authorship of others' materials
- Violate fair-use doctrine (context matters; wholesale copying is risky)
- Assume Educational use exempts copyright

### Always

- Retain attribution
- Document source and license
- Obtain permission when uncertain
- Consult PROJECT_RULES.md copyright section
- When in doubt, quarantine

---

## Data Retention

### Minimum Retention

- Source metadata: permanent
- Provenance records: permanent
- Normalized data: during active project
- Raw data: for 1-2 cycles after approval
- Failed/rejected content: 90 days

### Deletion

Deletion must be:

- Logged
- Reversible (archive backup first)
- Justified in data_retention_log.md

---

## Summary

The project prioritizes:

1. **Authorization**: only use content you have legal right to use
2. **Transparency**: retain and declare provenance
3. **Attribution**: credit original creators
4. **Caution**: when uncertain, quarantine
5. **Control**: never bypass technical access restrictions

All ingestion decisions are auditable and defensible.
