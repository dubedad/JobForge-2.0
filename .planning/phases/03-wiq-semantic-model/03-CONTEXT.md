# Phase 3: WiQ Semantic Model - Context

**Gathered:** 2026-01-18
**Status:** Ready for planning

<domain>
## Phase Boundary

Define dimensional model relationships and cardinality so gold layer tables form a proper star schema for Power BI consumption. The schema must be machine-readable for Phase 4's deployment scripts. This phase defines the model — deployment is Phase 4.

</domain>

<decisions>
## Implementation Decisions

### Model Structure (from PROJECT.md)
- Two hub dimensions: DIM NOC and DIM Job Architecture
- DIM NOC connects to Element, Oasis, and COPS tables (1:M from NOC to attributes/facts)
- DIM Job Architecture connects to DIM Occupations (job families)
- unit_group_id is the FK linking attribute tables to DIM NOC

### Table Classification
- **Dimensions:** dim_noc, dim_occupations, job_architecture
- **Facts:** cops_* tables (forecasting data with year projections)
- **Attribute tables:** oasis_*, element_* (proficiency scores and text descriptions linked to NOC)

### Relationship Direction
- Single direction for Power BI (dimension to fact)
- DIM NOC → all attribute and fact tables (one-to-many)
- DIM Occupations → Job Architecture (one-to-many by family/function)

### Schema Format
- Python Pydantic models for schema definition (consistent with existing codebase)
- Machine-readable output (JSON/dict) for deployment scripts to consume
- Relationship definitions include: from_table, to_table, from_column, to_column, cardinality

### Claude's Discretion
- Exact Pydantic model structure for schema representation
- Validation approach for circular relationship detection
- How to represent cardinality types (1:1, 1:M, M:M with bridge)

</decisions>

<specifics>
## Specific Ideas

From PROJECT.md WiQ Model Structure:
- "Knowledge graph indexes vocabulary across NOC, attributes, and Job Architecture" — this is Phase 5 (conversational lineage), not this phase
- "Semantic matching links org position titles to Job Architecture job titles" — out of scope for v1

The reference implementation at `C:\Users\Administrator\Dropbox\++ Results Kit\JobForge` has a working `/stagegold` command — Phase 4 can reference its approach while using the new schema definitions from this phase.

</specifics>

<deferred>
## Deferred Ideas

- Bridge table for Job Architecture to organizational positions — requires position data (out of scope)
- Knowledge graph vocabulary indexing — Phase 5 (conversational lineage)
- DAX measures — Phase 4 (Power BI deployment)
- Business glossary terms in table properties — Phase 5 (data governance)

</deferred>

---

*Phase: 03-wiq-semantic-model*
*Context gathered: 2026-01-18*
