# M5 Trusted Reviewer Registry Form

This is a blank operator form, not identity evidence, a trusted registry, review, or approval. A trusted administrator—not either reviewer—must verify identities out of band and create JSON conforming to `schemas/curriculum-reviewer-registry.schema.json`.

## Registry authority

- Issued by:
- Issued-at timestamp with timezone:
- Registry ID: derive as `m5reviewers_` plus the canonical JSON SHA-256 after excluding `registry_id`
- Trust policy: `EXTERNALLY_VERIFIED_IDENTITIES_V1`

## Reviewer record

- Canonical reviewer ID (NFKC-normalized, trimmed, case-folded):
- Display name:
- Verified qualifications:
- Permitted roles: LINGUISTIC / PEDAGOGICAL
- Status: VERIFIED

## External identity evidence

- Canonical evidence ID:
- Method: ORGANIZATIONAL_DIRECTORY / EXTERNAL_IDENTITY_PROVIDER / SIGNED_ATTESTATION / MANUAL_ID_CHECK
- Issuer:
- Provider-defined subject ID, preserving exact casing:
- Non-secret evidence reference:
- Verified-at timestamp with timezone:
- Verified by:

The same `(normalized issuer, exact subject ID)` must not support multiple reviewer records. Equal subject text from different issuers is not treated as the same identity. Evidence verification must not postdate registry issuance or any review that relies on it. Do not place credentials, authentication tokens, private identity documents, or other secrets in the registry.
