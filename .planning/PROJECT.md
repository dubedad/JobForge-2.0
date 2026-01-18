# JobForge 2.0

## What This Is

A workforce intelligence platform that deploys a governed semantic model (WiQ) to enterprise platforms like Power BI, then generates compliant business and data artifacts traceable to DADM and DAMA DMBOK. JobForge ingests authoritative occupational data (NOC, O*NET/SOC), harmonizes it through a staged → bronze → silver → gold pipeline, and exposes it as a "golden apple tree" where data governance teams and business users can harvest governed artifacts.

## Core Value

Auditable provenance from source to output — every artifact traces back to authoritative sources with DADM compliance scoring. When asked "where did this come from and why is it compliant?", JobForge can answer.

## Requirements

### Validated

(None yet — ship to validate)

### Active

- [ ] `/stagegold` deploys WiQ model to Power BI with all metadata, relationships, and cardinality
- [ ] DIM NOC connected to all NOC attribute tables (Element, Oasis)
- [ ] DIM NOC connected to NOC COPS forecasting facts
- [ ] DIM Job Architecture connected to NOC model
- [ ] DIM Occupation Group connected to Job Architecture job titles
- [ ] Business glossary terms populate table and column properties
- [ ] DAX measures in place for standard reporting
- [ ] Status visuals for data management team
- [ ] Planning visuals for HR team
- [ ] Data dictionary export in Purview-compatible format
- [ ] Data dictionary export in Denodo-compatible format
- [ ] Lineage documentation export
- [ ] Conversational interface for querying WiQ (jobs and forecasts)
- [ ] WiQ can explain its own data pipeline (lineage queries)
- [ ] WiQ can explain DADM compliance mapping (compliance queries)
- [ ] Cross-model queries work (e.g., "which skills are at risk of shortage and what job titles use them")

### Out of Scope

- Manager artifact building (JD builder, performance agreements, etc.) — v2 after data governance layer is solid
- Departmental position data integration — privacy constrained, deferred
- Employee data — privacy constrained, deferred
- O*NET imputation agent — later milestone
- Authority/differentiation quadrant controls — later milestone (manager experience)
- Real-time sync with org HR systems — manual export/import for now

## Context

**Reference Implementation:**
`C:\Users\Administrator\Dropbox\++ Results Kit\JobForge` contains a working prototype with:
- `/stagegold` command deploying MVP gold model to Power BI
- Staged, bronze, silver, gold parquet files
- Half-baked UI for job title selection and JD factor display
- Repository of policies, practices, example outputs
- Feature backlog and documentation

This is a fresh build using the reference for understanding, not code reuse.

**Government of Canada Context:**
HR job data across federal government is unstructured, non-standardized, fragmented, siloed, and unreliable. This makes evidence-based workforce planning impossible. Meanwhile, mandate letters require AI-driven operational efficiencies (Priority 7) and international workforce planning interoperability (Priority 6) — while demonstrating DADM compliance.

**WiQ Model Structure:**
- Two hub dimensions: DIM NOC and DIM Job Architecture
- DIM NOC connects to Element and Oasis attribute tables (qualifiers)
- DIM NOC connects to NOC COPS forecasting facts
- DIM Job Architecture connects via bridge table to organizational positions
- Knowledge graph indexes vocabulary across NOC, attributes, and Job Architecture
- Semantic matching links org position titles to Job Architecture job titles

**The Quadrant Model (for future reference):**
- Low authority: Pure LLM generation (expressive, no provenance)
- Medium authority: LLM + O*NET agent (SOC intel informing)
- High authority: NOC data only (authoritative, less differentiated)
- Each position scores against DADM requirements rubric

## Constraints

- **Language**: Python (user's known language)
- **Deployment target**: Power BI semantic model (primary); Denodo, Fabric, Databricks later
- **Export formats**: MS Purview, Denodo (platform-native import formats)
- **Compliance**: Must map to DADM directive requirements with traceable provenance
- **Data governance**: Must align with DAMA DMBOK practices
- **Data format**: Parquet files for pipeline stages (validated in reference implementation)

## Key Decisions

| Decision | Rationale | Outcome |
|----------|-----------|---------|
| Fresh build, not fork | Reference implementation is prototype quality; clean architecture preferred | — Pending |
| Data governance first | Build governed foundation before consumer experiences (manager artifacts) | — Pending |
| Power BI primary target | Proven in reference implementation; enterprise standard | — Pending |
| Parquet for pipeline stages | Validated in reference implementation; good performance characteristics | — Pending |
| Python stack | User's known language; good for data pipelines and ML | — Pending |

---
*Last updated: 2026-01-18 after initialization*
