# Phase 17: Governance Compliance Framework - Context

**Gathered:** 2026-02-05
**Status:** Ready for planning

<domain>
## Phase Boundary

Governance checks that trace to policy with quantitative evidence, enabling audit-ready compliance reports. DAMA audit, policy provenance, lineage-to-policy traceability. Users can view compliance evidence, trace data to policy clauses, run automated audits, and query which policies govern specific tables/relationships.

</domain>

<decisions>
## Implementation Decisions

### Audit Output Format
- Default to structured tables, with option to expand narrative per item (toggle)
- Radar/spider charts for visualizing compliance scores across DAMA dimensions
- Export formats: JSON + Markdown + PDF (PDF includes embedded static radar charts)
- Current state only — no historical comparisons
- Two audience modes: detailed view for technical data stewards, summary view for governance committees (toggle)
- Reports include gaps with prioritized recommendations (ranked by impact/effort)
- Evidence linked via deep links to catalog entries and lineage records

### Policy Mapping Granularity
- Three-level traceability: table-level, column-level, and relationship-level (FKs/lineage edges)
- Storage: policy_refs in catalog JSON + separate policy_mappings.json with full policy details
- Policy sources in scope:
  - TBS Directive on Service and Digital
  - DAMA DMBOK principles
  - Other GC instruments (ATIP, Privacy Act, Treasury Board policies)
  - GC HR ERD and Data Dictionary
  - Directive on Automated Decision-Making
  - Algorithmic Impact Assessment requirements
- Citation + full text — store actual policy clause text alongside references
- Version-dated mappings — track which policy version a mapping refers to (e.g., "TBS DSD 2024-04")
- Primary + secondary policy designation when multiple policies govern same element
- Each table/column/relationship shows current compliance status with its policies
- Support explicit N/A designations with justification (distinguishes "not yet mapped" from "intentionally exempt")

### Compliance Scoring
- Three scoring views: binary pass/fail, percentage scores (0-100%), and maturity levels (Initial/Managed/Defined/Optimized)
- Configurable weights per DAMA dimension with GC-aligned defaults (TBS priorities)
- Three-tier rollup: phase-level, milestone-level (v1/v2/v3), and overall project compliance

### Query Interface
- Both CLI commands + API endpoints — CLI wraps API
- Bidirectional queries: "What policies govern this table?" AND "What tables satisfy this policy clause?"
- Query results include: policy refs + current compliance status + supporting evidence
- CLI supports both single-shot commands (scripting) and interactive REPL mode (exploration)
- Dedicated governance commands + policy flags on existing catalog commands
- API filtering by policy source and DAMA dimension
- Single-element queries + bulk export of entire policy-to-data mappings (JSON/CSV)

### Claude's Discretion
- DuckDB exposure for governance data (policy_mappings and compliance_scores views)
- Exact structure of interactive REPL mode
- Technical implementation of radar chart generation for PDF reports
- Specific GC-aligned default weights per DAMA dimension

</decisions>

<specifics>
## Specific Ideas

- "Audit-ready" means the output should satisfy a GC internal audit or TBS compliance review
- Radar charts should show balance across DAMA dimensions — imbalanced profiles are easy to spot visually
- Policy text storage enables full-text search across policy requirements
- Prioritized recommendations should help governance committees focus remediation effort

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope

</deferred>

---

*Phase: 17-governance-compliance-framework*
*Context gathered: 2026-02-05*
