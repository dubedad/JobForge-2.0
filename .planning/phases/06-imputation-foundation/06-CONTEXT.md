# Phase 6: Imputation Foundation - Context

**Gathered:** 2026-01-19
**Status:** Ready for planning

<domain>
## Phase Boundary

Enable users to impute missing attribute values using hierarchical inheritance from authoritative NOC sources, with full provenance tracking. This phase establishes the confidence framework architecture (NOC → O*NET → LLM) but only activates the NOC tier. O*NET and LLM imputation are Phase 7.

</domain>

<decisions>
## Implementation Decisions

### Inheritance Behavior
- Authority-specificity trade-off: L5 (NOC) is most authoritative but generalized; L7 is most specific but has no direct attribute data
- Inheritance cascades DOWN from NOC through the hierarchy (L5 → L6 → L7)
- Each job title maps to exactly ONE NOC code — no multi-NOC ambiguity
- The L5 → L6 → L7 hierarchy IS the natural scope — no additional filtering needed
- All NOC attributes inherit through the hierarchy (skills, knowledge, abilities, work context, etc.)

### Confidence Framework
- Architecture supports 3-tier confidence: NOC (highest) → O*NET (lower) → LLM (lowest)
- Phase 6 implements NOC tier only; framework ready for Phase 7 additions
- Imputed values track confidence level based on source tier
- Job description factors can show aggregate confidence broken down by factor and statement

### Persistence Strategy
- Hybrid approach: cache imputed results but allow re-computation when source data changes
- Results stored in gold layer with provenance columns
- Invalidation approach: Claude's discretion based on pipeline architecture

### Claude's Discretion
- Validation approach for prototype port (snapshot comparison vs test coverage vs spot-check)
- Cache invalidation mechanism (automatic on pipeline run vs manual trigger)
- Exact provenance column structure in gold tables

</decisions>

<specifics>
## Specific Ideas

- "If L6 Labels, Leading Statements and L7 example titles could inherit a more specific subset of their parent NOC attributes, then using the data INSIDE the model they would become more specific WHILE maintaining authoritative source authority"
- Confidence system enables future job description generation where managers can choose authoritative-but-general vs specific-but-less-authoritative statements
- Aggregate job description confidence = weighted combination of factor confidence scores

</specifics>

<deferred>
## Deferred Ideas

- O*NET API imputation (lower confidence tier) — Phase 7
- LLM agent imputation (lowest confidence tier) — Phase 7
- Job description generation with selectable confidence levels — Phase 8

</deferred>

---

*Phase: 06-imputation-foundation*
*Context gathered: 2026-01-19*
