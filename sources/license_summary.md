# Source licensing and evidence summary

**Review date:** 2026-08-30  
**Scope:** M1 governance metadata only. No corpus, audio, video, transcript, or other source payload was downloaded or stored. This document is operational guidance, not legal advice.

The machine-readable authority is [registry.yaml](registry.yaml), validated by [source-registry.schema.json](../schemas/source-registry.schema.json). Every approval is deliberately narrow: a source is usable only when it is `APPROVED` **and** the specific requested media operation is true. A valid registry entry alone never authorizes use.

## Approved, bounded source lanes

| Source | Scope and license decision | Key conditions |
| --- | --- | --- |
| Tatoeba text | CC BY 2.0 FR by default; a record-level compatible license can supersede it | Retain sentence ID, author, license, attribution, source URL, and modification notice. Audio is a separate source decision. |
| Tatoeba CC BY 4.0 audio | Only recordings whose official metadata affirmatively says CC BY 4.0 and provides attribution data | Retain audio ID, sentence ID, creator, attribution URL, and license. Transcript/exercise redistribution additionally requires cleared underlying sentence text. |
| Mozilla Common Voice Scripted Speech | Release-labelled CC0 material subject to Mozilla Data Collective release terms | Controlled download, storage, processing, clipping, transcript generation, and internal exercise use are allowed. Re-hosting/re-sharing original or derived material is denied; never attempt speaker identification. |
| LibriVox recordings | Public domain **in the United States** | Recording rights and underlying edition/translation rights are distinct. Do not imply worldwide clearance or create distributable transcripts without item and jurisdiction review. |
| NASA SVS ID 5587 plain video | Selected non-music video variants under NASA media guidance | Acknowledge NASA/SVS, avoid endorsement and marks, and exclude third-party/musical variants. Video is approved; audio extraction and transcript generation are denied. |
| English Wiktionary official dumps | CC BY-SA 4.0 text reuse with GFDL context | Use official dumps, retain attribution and change notice, and meet ShareAlike obligations. Non-text media is excluded. |

## Reference-only and quarantine decisions

| Source | Status | Reason |
| --- | --- | --- |
| Council of Europe CEFR Companion Volume | `REFERENCE_ONLY` | It is authoritative for taxonomy, but availability of a PDF does not grant corpus extraction, adaptation, translation, or redistribution. |
| Cambridge public specifications | `REFERENCE_ONLY` | Public documents and sample materials are not a general reuse or corpus license. |
| British Council public resources | `REFERENCE_ONLY` | Rights vary by item; source-wide automated ingestion and reuse are not established. |
| English Profile EVP | `QUARANTINED` | Current official evidence did not establish bulk extraction, API, storage, or redistribution permission. |
| VOA Learning English mixed-media pages | `QUARANTINED` | A page may include third-party agency, stock, music, image, video, or audio components. Only a separately reviewed asset record could be considered later. |
| Tatoeba audio with unknown/offsite-prohibited license | `QUARANTINED` | Attribution alone is insufficient; an affirmative record-level offsite-use license is required. |

## Evidence rules

1. Each registry record identifies official evidence URLs, what they support, and the date checked.
2. A future review must recheck evidence when terms change, an approval reaches its review deadline, or an importer needs a right not represented in the record.
3. Unclear rights, incompatible license terms, missing attribution fields, and asset-level third-party uncertainty mean `QUARANTINED`.
4. Do not use blog posts, mirrors, or model output as the sole basis for approval.
5. Every future retained record must carry the common provenance fields defined in [DATA_POLICY.md](../docs/DATA_POLICY.md), plus media provenance specified in [approved_sources.md](approved_sources.md).
