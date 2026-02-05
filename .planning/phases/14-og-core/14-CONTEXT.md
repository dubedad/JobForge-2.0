# Phase 14: OG Core - Context

**Gathered:** 2026-02-04
**Status:** Ready for planning

<domain>
## Phase Boundary

TBS Occupational Groups data scraped and loaded into gold tables with NOC concordance. Enables JD Builder Lite to deterministically classify positions by occupational group.

Includes: 65 OGs, ~200 subgroups, NOC-OG bridge table, qualification standards, pay scales.
Does NOT include: CAF data (Phase 15), job evaluation standards (Phase 16).

</domain>

<decisions>
## Implementation Decisions

### NOC-OG Matching Logic

**Classification output:**
- Return ranked list (top 3-5 matches) with confidence scores
- Always provide a suggestion, even for weak matches (best guess + low confidence)

**Source attribution:**
- Flag whether each mapping is TBS-published or algorithmically derived
- Store rationale text explaining why this NOC maps to this OG (supports auditing)

**NOC version:**
- Use NOC 2021 (current) as primary reference

**Mapping granularity:**
- Support NOC→OG subgroup mappings (not just parent OGs) for more precise classification

**Query patterns:**
- Support both "given NOC, what OGs?" AND "given job description text, what OGs?"
- Both patterns equally important for JD Builder integration

**Explainability:**
- Generate human-readable explanation templates for each mapping
- E.g., "This NOC maps to OG-AS because..." for user-facing UI

### Data Capture Scope

**OG attributes:**
- Comprehensive capture: code, name, definition, subgroups, descriptions, pay rates, qualifications
- Everything TBS publishes about each occupational group

**PDF processing:**
- Download and index TBS Qualification Standards PDFs
- Extract text for searchable qualification data

**Pay rate detail:**
- Full pay scales with all steps within each level
- Track both represented and unrepresented pay/terms

### Table Structure

**Naming convention:**
- Follow existing JobForge pattern: dim_og, dim_og_subgroup, bridge_noc_og
- Consistent with dim_*, bridge_*, fact_* conventions

**Qualification structure:**
- Structured fields where possible (education, experience, etc.) for filtering
- Plus raw text for completeness and full-text search

### Claude's Discretion

**NOC-OG matching (researcher/planner decides):**
- Mapping relationship type (one-to-one vs many-to-many) — discover from data
- Confidence scoring algorithm — design based on available TBS data
- Query direction support (both directions likely needed)
- Historical mapping versioning — based on TBS data availability
- Primary OG indicator for multi-match cases — based on data patterns
- Match tolerance (recall vs precision) — balance based on downstream needs
- Conditional mapping logic — if TBS data has such nuances
- Mutation policy (immutable vs mutable) — based on governance needs
- Confidence thresholds — design appropriate mechanism
- Temporal decay — based on data freshness needs
- Internal enrichment from existing COPS data — based on data quality

**Gap handling (researcher/planner decides):**
- Missing data strategy — log/continue vs fail based on data criticality
- Archived OG inclusion — based on TBS data structure
- Conflict resolution — apply judgment case-by-case
- Unmappable OGs — load anyway if data valuable without NOC bridge

**Table structure (planner decides):**
- OG/subgroup separation vs combined hierarchy — based on query patterns
- Pay table normalization — based on data complexity

</decisions>

<specifics>
## Specific Ideas

- Rationale capture supports JobForge's "auditable provenance" principle
- Classification should feel deterministic for JD Builder users — ranked list with confidence lets user make final call
- Qualification standards are key differentiator — structured parsing enables "find OGs requiring X education"

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope

</deferred>

---

*Phase: 14-og-core*
*Context gathered: 2026-02-04*
