# Phase 8: Description Generation - Context

**Gathered:** 2026-01-20
**Status:** Ready for planning

<domain>
## Phase Boundary

Generate descriptions for job architecture entities (titles, families, functions) using multiple sources — authoritative Canadian text (NOC lead statements) and LLM fallbacks — with full provenance tracking. Users can see which source provided each description.

</domain>

<decisions>
## Implementation Decisions

### Description Resolution Path
- **L6 match:** If job title semantically matches L6 label → use L6 lead statement directly
- **L7 fallback:** If no L6 match → check L7 example titles for semantic match
- **L7 inheritance:** If L7 match found → inherit that L7's parent L6 lead statement
- **Rationale:** L7 specificity compensates for absent L6 match; creates stronger connection than weak L6-only match

### NOC as Authoritative Anchor
- NOC vocabulary acts as "boundary words" — semantic anchors for all descriptions
- Use NOC title + Unit Group description as context constraints for O*NET/LLM queries
- This keeps generated content semantically tethered to NOC universe
- Applies at all levels: titles (L7), families (L5), functions (L4+)

### Source Cascade
1. Direct NOC lead statement (when semantic match exists)
2. O*NET query (informed by NOC boundary words)
3. LLM synthesis (prompted with NOC context)
- NOC is always authoritative source — either directly or as context for downstream sources

### Tone and Style
- LLM-generated descriptions must match NOC style
- Formal, third-person, occupational classification voice
- Example: "Software engineers design..." not "This role involves designing..."

### Unmapped Titles
- Titles with no NOC mapping get LLM-only descriptions
- Mark as low-authority in provenance
- Still generated (not skipped) to ensure coverage

### Provenance Metadata
- Full lineage for every description:
  - Source type (authoritative/O*NET/LLM)
  - Confidence score
  - Timestamp
  - Model version (for LLM)
  - Input context used (boundary words, prompts)

### Quality Flagging
- Low-confidence descriptions flagged for human review
- Queryable for QA workflows
- Threshold for "low-confidence" to be determined during implementation

### Claude's Discretion
- **Storage approach:** Multiple descriptions per entity vs single best with provenance
- **Description length:** Match source length vs standardize
- **Caching strategy:** Generate during pipeline vs on-demand

</decisions>

<specifics>
## Specific Ideas

### The Knowledge Ball Mental Model
User envisions the NOC hierarchy as concentric layers:
- Outer shell: L1 terms (broad, authoritative, abstract)
- Inner layers: L2 → L6 (increasingly specific)
- Core: L7 (maximum detail, "semantic purebreds")

L7 is where you "strike oil" for:
- Canonical scoring
- Semantic purity
- High-confidence differentiation

### Cross-Attribute Semantic Strength
The power emerges when constructing a strong L7 slice across multiple attributes:
- More attributes aligned at L7 = higher semantic similarity across columns
- Creates a second scoring dimension (breadth) orthogonal to depth

</specifics>

<deferred>
## Deferred Ideas

### Two-Dimensional Scoring Framework (Phase 10 or v2.1)
- **X-axis:** Authority (hierarchical certainty, L1→L7)
- **Y-axis:** Specificity/semantic coherence (cross-attribute alignment)
- Each quadrant maps to appropriate imputation agent:
  - High authority, low specificity → Native source inheritance
  - High specificity, low authority → L7-backed inference, O*NET, LLM
  - High-high → Ideal but rare
  - Low-low → Avoid
- Latitude/longitude scoring for attributes
- Outcome-based agent selection menu (4 choices aligned to quadrants)

This framework turns imputation from a liability into a controlled, explainable design choice. Better suited for Phase 10 (Governance) where compliance and observability are the focus.

</deferred>

---

*Phase: 08-description-generation*
*Context gathered: 2026-01-20*
