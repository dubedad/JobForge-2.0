# Phase 15: CAF Core - Context

**Gathered:** 2026-02-05
**Status:** Ready for planning

<domain>
## Phase Boundary

CAF Careers data scraped and loaded into gold tables with bridges to NOC and Job Architecture. Users can query all 107 CAF occupations, 12 job families, find civilian equivalents, look up associated NOC codes, and find Job Architecture matches with confidence scores. All tables have full provenance.

</domain>

<decisions>
## Implementation Decisions

### Data Acquisition
- Authoritative source: forces.ca (provenance must trace back to this source)
- On-demand refresh via CLI command (not scheduled)
- Capture all available fields from the website — don't filter during scrape
- Bilingual support: scrape both EN and FR versions (forces.ca/en and forces.ca/fr)
- Existing POC files in proposals/ or src/poc/ should be referenced for structure

### Matching Strategy
- Hybrid approach: automated fuzzy matching suggests candidates, human-reviewed mappings stored for reuse
- Two-level Job Architecture matching:
  - CAF career streams → JA job families
  - CAF individual careers → JA job roles/titles
- Match cardinality (one-to-one vs one-to-many vs many-to-many) determined by data analysis during research
- NOC matching uses same hybrid approach

### Confidence Scoring
- All matches returned regardless of confidence — user filters, not system
- Full audit trail explaining what contributed to each score
- Audit trail includes: matching factors, intermediate scores, algorithm used, verification status

### Provenance & Metadata
- Full extraction metadata per record: source URL, scrape timestamp, content hash, scraper version, raw HTML reference
- Full match lineage: algorithm, version, input sources, intermediate scores, who verified (if applicable)
- Data catalog entries must be consistent with existing WiQ table patterns
- Catalog management must follow DAMA-DMBOK best practices

### Claude's Discretion
- Bilingual storage pattern (separate columns vs separate rows with lang flag)
- Error handling strategy for failed/partial scrapes
- Mapping storage location (JSON in data/reference/, database table, or both)
- Confidence score format (numeric 0-100, named tiers, or both)
- How to distinguish human-verified from automated matches
- Whether to preserve raw scraped HTML
- Specific catalog generation approach (auto, manual, or template-based)

</decisions>

<specifics>
## Specific Ideas

- "Provenance is what matters" — the audit trail back to forces.ca is critical
- Two-level JA matching may require more data analysis to determine feasibility
- Match confidence with full audit trail aligns with JobForge's core value of auditable provenance
- Use the managing-data-governance skill for DAMA-DMBOK alignment

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope

</deferred>

---

*Phase: 15-caf-core*
*Context gathered: 2026-02-05*
