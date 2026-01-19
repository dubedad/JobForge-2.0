# Phase 7: External Data Integration - Context

**Gathered:** 2026-01-19
**Status:** Ready for planning

<domain>
## Phase Boundary

Enrich WiQ with external data sources: O*NET API for SOC-aligned attributes, LLM imputation for remaining gaps, and TBS scraping for occupational group metadata. All external data must have full provenance.

</domain>

<decisions>
## Implementation Decisions

### O*NET Mapping Strategy
- Researcher must investigate NOC-SOC cardinality (1:1, 1:N, N:1) before implementation
- Pull all available O*NET attributes for mapped SOC codes
- Require O*NET API key setup for authenticated access
- If O*NET has no data for a mapped SOC → fall through to LLM imputation

### LLM Imputation Behavior
- Trigger LLM only after all other sources exhausted (hierarchical → O*NET → LLM)
- Provider: ChatGPT Pro (OpenAI API)
- LLM must return structured confidence scores (0.0-1.0)
- Accept all LLM answers regardless of confidence — store score + rationale in provenance
- Include full job architecture context in prompts (title, function, family, known attributes)
- Auto-commit results with confidence and rationale stored for downstream filtering

### TBS Scraping Approach
- Scrape multiple pages: main classification page + linked detail pages
- Traversal depth: two levels deep from main page
- Extract all available structured content
- Fail loudly on page structure changes — require manual update, no silent degradation
- Scheduled refresh: monthly
- Bilingual: scrape both English and French content into separate files

### Provenance Design
- Source precedence: Authoritative > O*NET > LLM (fixed hierarchy)
- Higher-precedence sources auto-override existing LLM-imputed values
- Log all override events for audit
- Summary provenance inline with data + detailed provenance in separate table
- Support filtering by source AND by confidence
- Retention: per GC Data Archiving Policy for information management

### Claude's Discretion
- O*NET caching strategy (local cache vs fresh fetch vs bulk download)
- O*NET confidence scoring based on mapping strength
- LLM batching strategy for cost/quality optimization
- TBS historical version storage approach
- TBS schema integration design (extend DIM Occupations vs new table)
- Provenance schema specifics based on research into governance requirements

</decisions>

<specifics>
## Specific Ideas

- "Researcher should investigate NOC-SOC cardinality — we can't assume the relationship type yet"
- LLM should store rationale explaining imputed values so future features can continuously improve
- TBS scraping should fail loudly rather than silently degrading on structure changes
- Provenance retention must align with GC Data Archiving Policy

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope

</deferred>

---

*Phase: 07-external-data-integration*
*Context gathered: 2026-01-19*
