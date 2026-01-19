# JobForge 2.0

## What This Is

A workforce intelligence platform that deploys a governed semantic model (WiQ) to Power BI with full data lineage and provenance tracking. JobForge ingests authoritative Canadian occupational data (NOC, COPS forecasts, OaSIS proficiencies) through a medallion pipeline (staged -> bronze -> silver -> gold), producing 24 queryable gold tables with a star schema ready for enterprise analytics.

## Core Value

Auditable provenance from source to output — every artifact traces back to authoritative sources. When asked "where did this come from?", JobForge can answer with the complete pipeline path.

## Requirements

### Validated

- [x] **PIPE-01**: Implement medallion pipeline (staged -> bronze -> silver -> gold with parquet files) — v1.0
- [x] **PIPE-02**: Ingest DIM NOC table (516 occupations) — v1.0
- [x] **PIPE-03**: Ingest NOC attribute tables (Element text, OaSIS proficiencies) — v1.0
- [x] **PIPE-04**: Ingest NOC COPS forecasting data (10-year projections) — v1.0
- [x] **PIPE-05**: Ingest Job Architecture table (1,987 job titles) — v1.0
- [x] **PIPE-06**: Ingest DIM Occupations (Occupational Groups) table — v1.0
- [x] **WIQ-01**: Create WiQ schema with relationships and proper cardinality (22 relationships) — v1.0
- [x] **PBI-01**: `/stagegold` command deploys WiQ model specifications — v1.0
- [x] **GOV-01**: Generate Data Catalogue for WiQ (24 table metadata files) — v1.0
- [x] **CONV-01**: WiQ can answer lineage queries via `/lineage` CLI — v1.0

### Active

- [ ] **INT-01**: O*NET/SOC integration with crosswalk mapping
- [ ] **INT-02**: Confidence scoring for NOC-SOC mappings
- [ ] **PBI-02**: Auto-populate table/column descriptions from business glossary
- [ ] **PBI-03**: DAX measures for standard reporting (headcount, FTE, vacancy rates)
- [ ] **PBI-04**: Status visuals for data management team
- [ ] **PBI-05**: Planning visuals for HR team
- [ ] **GOV-02**: Business glossary with standard workforce terms
- [ ] **GOV-03**: Lineage documentation export
- [ ] **GOV-04**: Export to MS Purview format
- [ ] **GOV-05**: Export to Denodo format
- [ ] **CONV-02**: Natural language queries on jobs and forecasts
- [ ] **CONV-03**: Query explanation with source citations
- [ ] **CONV-04**: DADM compliance queries

### Out of Scope

- Manager artifact building (JD builder, performance agreements) — v2+ after data governance is solid
- Departmental position data integration — privacy constrained
- Employee-level data — privacy constrained
- Real-time sync with org HR systems — manual export/import for now
- Real-time job posting ingestion — Job Bank already does this
- Full HRIS functionality — existing government systems handle this
- Automated hiring decisions — DADM compliance risk

## Context

**Current State (v1.0 shipped 2026-01-19):**
- 5,779 lines of Python across 35 modules
- 24 gold tables in parquet format
- 22 relationships in WiQ semantic model
- 100 tests passing
- Stack: Python 3.11, Polars, DuckDB, Pydantic 2, NetworkX, Rich

**Government of Canada Context:**
HR job data across federal government is unstructured, non-standardized, fragmented, siloed, and unreliable. This makes evidence-based workforce planning impossible. Meanwhile, mandate letters require AI-driven operational efficiencies and international workforce planning interoperability — while demonstrating DADM compliance.

**WiQ Model Structure:**
- Two hub dimensions: DIM NOC and DIM Job Architecture
- DIM NOC connects to Element and OaSIS attribute tables (1:M)
- DIM NOC connects to COPS forecasting facts (1:M)
- DIM Job Architecture connects to DIM Occupations (M:1)

## Constraints

- **Language**: Python (user's known language)
- **Deployment target**: Power BI semantic model (primary); Denodo, Fabric, Databricks later
- **Export formats**: MS Purview, Denodo (platform-native import formats)
- **Compliance**: Must map to DADM directive requirements with traceable provenance
- **Data governance**: Must align with DAMA DMBOK practices
- **Data format**: Parquet files for pipeline stages

## Key Decisions

| Decision | Rationale | Outcome |
|----------|-----------|---------|
| Fresh build, not fork | Reference implementation is prototype quality; clean architecture preferred | Good — clean codebase |
| Data governance first | Build governed foundation before consumer experiences | Good — lineage works |
| Power BI primary target | Proven in reference implementation; enterprise standard | Good — /stagegold ready |
| Parquet for pipeline stages | Good performance characteristics, schema preservation | Good — DuckDB queries fast |
| Python stack | User's known language; good for data pipelines | Good — 5.8k LOC in 2 days |
| Rule-based NLP for lineage | Deterministic, fast, no ML dependencies | Good — 34 query tests pass |
| NetworkX for lineage DAG | Battle-tested graph library, simple API | Good — 106 nodes, 79 edges |

---
*Last updated: 2026-01-19 after v1.0 milestone*
