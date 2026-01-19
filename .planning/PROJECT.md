# JobForge 2.0

## What This Is

A workforce intelligence platform that deploys a governed semantic model (WiQ) to Power BI with full data lineage and provenance tracking. JobForge ingests authoritative Canadian occupational data (NOC, COPS forecasts, OaSIS proficiencies) through a medallion pipeline (staged -> bronze -> silver -> gold), producing 24 queryable gold tables with a star schema ready for enterprise analytics. The model can impute its own missing data using hierarchical inheritance, O*NET API, and LLM calls with full provenance.

## Core Value

Auditable provenance from source to output — every artifact traces back to authoritative sources. When asked "where did this come from?", JobForge can answer with the complete pipeline path, including DADM directive chapter and verse.

## Current Milestone: v2.0 Self-Imputing Model + Live Demo

**Goal:** Enable the WiQ model to impute missing data using its own authoritative sources, O*NET API, and LLM calls — then demonstrate this live via MCP while Power BI builds the model in real-time.

**Target features:**
- Hierarchical attribute imputation (L5→L6→L7 inheritance with filtered context)
- O*NET API integration for SOC-aligned attribute candidates
- LLM-powered description generation (job titles, families, functions)
- Occupational Groups scraping from TBS with embedded link metadata
- MCP-driven live demo (Power BI + JobForge UI split screen)
- Conversational interface for data and metadata queries
- DADM chapter-and-verse traceability

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

### Active (v2.0 Scope)

**Imputation & Data Quality:**
- [ ] **IMP-01**: Validate and port imputation system from prototype
- [ ] **IMP-02**: Hierarchical attribute inheritance (L5→L6→L7 filtered context)
- [ ] **IMP-03**: O*NET API integration for SOC-aligned attribute candidates
- [ ] **IMP-04**: LLM-powered attribute imputation for empty cells
- [ ] **IMP-05**: Description generation (job titles, families, functions)
- [ ] **IMP-06**: Multiple description sources with provenance (authoritative vs LLM-generated)

**New Data Sources:**
- [ ] **SRC-01**: Scrape TBS Occupational Groups page with full provenance
- [ ] **SRC-02**: Follow embedded links for occupational group metadata
- [ ] **SRC-03**: Extend DIM Occupations schema with scraped fields

**Demo & MCP:**
- [ ] **MCP-01**: Port MCP configuration from prototype to JobForge 2.0
- [ ] **MCP-02**: `/stagegold` live demo via MCP (Power BI + UI split screen)
- [ ] **MCP-03**: Basic UI for demo narration (what JobForge is doing)

**Governance & Compliance:**
- [ ] **GOV-02**: DADM chapter-and-verse traceability
- [ ] **GOV-03**: Conversational interface for data queries
- [ ] **GOV-04**: Conversational interface for metadata queries

**Deferred (v3+):**
- [ ] **INT-01**: Extended O*NET/SOC crosswalk beyond imputation use case
- [ ] **INT-02**: Confidence scoring refinements for NOC-SOC mappings
- [ ] **PBI-02**: Auto-populate table/column descriptions from business glossary
- [ ] **PBI-03**: DAX measures for standard reporting (headcount, FTE, vacancy rates)
- [ ] **PBI-04**: Status visuals for data management team
- [ ] **PBI-05**: Planning visuals for HR team
- [ ] **GOV-05**: Export to MS Purview format
- [ ] **GOV-06**: Export to Denodo format

### Out of Scope

- Job classification automation — v3 after model refinement complete
- Manager artifact building (JD builder, performance agreements) — v3+
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

**Prototype Reference:**
The JobForge prototype (`/JobForge/` sibling directory) contains working implementations of:
- Imputation system with 5-step deterministic resolution (L5→L6→L7)
- Description generation with L6 lead_statement priority (F-072 fix)
- O*NET adapter with 26 NOC-SOC crosswalk mappings
- LLM service for section intros and content ranking
- MCP `/stage-gold` command with Power BI integration
- Basic React UI for content selection

**Government of Canada Context:**
HR job data across federal government is unstructured, non-standardized, fragmented, siloed, and unreliable. This makes evidence-based workforce planning impossible. Meanwhile, mandate letters require AI-driven operational efficiencies and international workforce planning interoperability — while demonstrating DADM compliance.

**WiQ Model Structure:**
- Two hub dimensions: DIM NOC and DIM Job Architecture
- DIM NOC connects to Element and OaSIS attribute tables (1:M)
- DIM NOC connects to COPS forecasting facts (1:M)
- DIM Job Architecture connects to DIM Occupations (M:1)
- NOC hierarchy extends to L6 (labels) and L7 (example titles) for imputation

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
*Last updated: 2026-01-19 after v2.0 milestone initialization*
