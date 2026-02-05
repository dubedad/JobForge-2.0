# JobForge 2.0

## What This Is

A workforce intelligence platform that deploys a governed, self-imputing semantic model (WiQ) to Power BI with full data lineage and provenance tracking. JobForge ingests authoritative Canadian occupational data (NOC, COPS forecasts, OaSIS proficiencies) through a medallion pipeline (staged → bronze → silver → gold), producing 24 queryable gold tables with a star schema. The model imputes missing data using hierarchical inheritance, O*NET API (1,467 NOC-SOC mappings), and LLM calls — with full provenance and DADM/DAMA compliance traceability.

## Core Value

Auditable provenance from source to output — every artifact traces back to authoritative sources. When asked "where did this come from?", JobForge can answer with the complete pipeline path, including DADM directive chapter and verse.

## Current Milestone: v3.0 Data Layer Expansion

**Goal:** Expand the WiQ data layer with TBS Occupational Groups and CAF Careers data, enabling downstream apps (JD Builder Lite, veteran transition tools) to query governed gold models instead of scraping.

**Target features:**
- TBS Occupational Groups suite (65 groups, ~200 subgroups, qualification standards, job evaluation standards, rates of pay)
- CAF Careers data (107 military occupations from forces.ca with civilian equivalence mappings)
- NOC → Occupational Group concordance (group/subgroup level, not classification levels)
- CAF → Job Architecture bridge with confidence scoring
- CAF → NOC linkage for military-to-civilian transition planning
- DMBOK practice provenance (track HOW model was engineered)

**Consumer apps:**
- JD Builder Lite — deterministic OG classification via concordance
- Veteran transition tools — CAF → civilian career pathways

## Current State (v2.1 Shipped 2026-01-21)

**Milestone delivered:** Orbit integration with Docker Compose deployment, enhanced text-to-SQL, workforce domain intelligence, and comprehensive documentation.

**Capabilities:**
- Medallion pipeline producing 24 gold tables with star schema
- 5-tier NOC resolution with hierarchical attribute inheritance
- O*NET API integration with 1,467 NOC-SOC crosswalk mappings
- LLM imputation via OpenAI Structured Outputs (gpt-4o)
- Description generation with authoritative lead statement → LLM fallback
- TBS Occupational Groups scraping (217 groups, 307 linked pages, bilingual)
- Live demo via MCP with Power BI real-time model building
- Compliance traceability logs (DADM, DAMA DMBOK, Classification)
- Conversational query API (text-to-SQL + metadata queries)
- **NEW (v2.1):** RFC 9457 error handling with actionable guidance
- **NEW (v2.1):** CORS middleware for cross-origin Orbit access
- **NEW (v2.1):** Enhanced DDL with semantic COMMENT clauses and relationship hints
- **NEW (v2.1):** Workforce domain intelligence (demand/supply patterns, entity recognition)
- **NEW (v2.1):** Source attribution in query results (table provenance mapping)
- **NEW (v2.1):** Docker Compose one-command deployment with healthchecks
- **NEW (v2.1):** Integration documentation with architecture diagram and tutorials

## Requirements

### Validated

**v1.0 (Shipped 2026-01-19):**
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

**v2.0 (Shipped 2026-01-20):**
- [x] **IMP-01**: Validate and port imputation system from prototype — v2.0
- [x] **IMP-02**: Hierarchical attribute inheritance (L5→L6→L7 filtered context) — v2.0
- [x] **IMP-03**: O*NET API integration for SOC-aligned attribute candidates — v2.0
- [x] **IMP-04**: LLM-powered attribute imputation for empty cells — v2.0
- [x] **IMP-05**: Description generation (job titles, families, functions) — v2.0
- [x] **IMP-06**: Multiple description sources with provenance (authoritative vs LLM-generated) — v2.0
- [x] **SRC-01**: Scrape TBS Occupational Groups page with full provenance — v2.0
- [x] **SRC-02**: Follow embedded links for occupational group metadata — v2.0
- [x] **SRC-03**: Extend DIM Occupations schema with scraped fields — v2.0
- [x] **MCP-01**: Port MCP configuration from prototype to JobForge 2.0 — v2.0
- [x] **MCP-02**: `/stagegold` live demo via MCP (Power BI + UI split screen) — v2.0
- [x] **MCP-03**: Basic UI for demo narration (what JobForge is doing) — v2.0
- [x] **GOV-02**: DADM traceability log with chapter-and-verse compliance — v2.0
- [x] **GOV-03**: DAMA traceability log with 11 knowledge areas — v2.0
- [x] **GOV-04**: Classification traceability log with NOC hierarchy compliance — v2.0
- [x] **GOV-05**: Conversational interface for data queries (text-to-SQL) — v2.0
- [x] **GOV-06**: Conversational interface for metadata queries — v2.0

**v2.1 (Shipped 2026-01-21):**
- [x] **ORB-01**: HTTP adapter configuration routes Orbit queries to JobForge API endpoints — v2.1
- [x] **ORB-02**: Intent configuration classifies queries (data, metadata, compliance, lineage) — v2.1
- [x] **ORB-03**: DuckDBRetriever validated with all 24 gold tables — v2.1
- [x] **ORB-04**: Error responses are user-friendly with actionable guidance (RFC 9457) — v2.1
- [x] **ORB-05**: Schema DDL includes column descriptions for improved SQL accuracy — v2.1
- [x] **ORB-06**: Relationship hints in DDL for multi-table joins — v2.1
- [x] **ORB-07**: Domain-specific intent patterns for workforce intelligence queries — v2.1
- [x] **ORB-08**: Entity recognition for NOC codes, occupational groups, job titles — v2.1
- [x] **ORB-09**: Provenance-aware responses include source attribution — v2.1
- [x] **ORB-10**: Docker Compose configuration for Orbit + JobForge stack — v2.1
- [x] **ORB-11**: Environment variables for API URLs, ports, credentials — v2.1
- [x] **ORB-12**: CORS middleware configured for cross-origin Orbit requests — v2.1
- [x] **ORB-13**: Orbit integration guide with architecture diagram — v2.1
- [x] **ORB-14**: Intent configuration reference for extending patterns — v2.1

### Future (v3.0+ Scope)

**Semantic Search & RAG:**
- [ ] **RAG-01**: Vector database for semantic similarity search
- [ ] **RAG-02**: RAG pipeline for context-aware LLM responses
- [ ] **RAG-03**: Knowledge graph enhancement — extend lineage DAG to full entity-relationship graph

**Job Description Builder UX:**
- [ ] **JDB-01**: Manager-facing web UI for job description creation
- [ ] **JDB-02**: NOC-aware form with auto-populated fields from WiQ
- [ ] **JDB-03**: Real-time validation against classification requirements
- [ ] **JDB-04**: Export to GC-compliant formats (Word, PDF with bilingual support)
- [ ] **JDB-05**: Audit trail — who edited what, when, with what justification

**Enhanced Integration:**
- [ ] **INT-01**: Extended O*NET/SOC crosswalk beyond imputation use case
- [ ] **INT-02**: Confidence scoring refinements for NOC-SOC mappings
- [ ] **INT-03**: Real-time Job Bank posting ingestion for market intelligence
- [ ] **INT-04**: Orbit integration (DuckDBRetriever, adapter config, deployment)

**Power BI Enhancements:**
- [ ] **PBI-02**: Auto-populate table/column descriptions from business glossary
- [ ] **PBI-03**: DAX measures for standard reporting (headcount, FTE, vacancy rates)
- [ ] **PBI-04**: Status visuals for data management team
- [ ] **PBI-05**: Planning visuals for HR team

**Export & Interoperability:**
- [ ] **GOV-07**: Export to MS Purview format
- [ ] **GOV-08**: Export to Denodo format
- [ ] **EXP-01**: HRIS integration adapters (PeopleSoft, SAP SuccessFactors)

### Out of Scope

- Automated hiring decisions — DADM compliance risk
- Employee-level data — privacy constrained
- Departmental position data integration — privacy constrained
- Real-time sync with org HR systems — manual export/import for now
- Full HRIS functionality — existing government systems handle this

## Context

**Current State (v2.1 shipped 2026-01-21):**
- 24 gold tables in parquet format
- 22 relationships in WiQ semantic model
- 610 tests passing
- Docker Compose deployment ready
- 3 documentation pages (1,493 lines)
- Stack: Python 3.11, Polars, DuckDB, Pydantic 2, NetworkX, Rich, rapidfuzz, httpx, tenacity, beautifulsoup4, openai, anthropic, fastapi, uvicorn, starlette, sse-starlette, Docker

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
| Fresh build, not fork | Reference implementation is prototype quality; clean architecture preferred | ✓ Good — clean codebase |
| Data governance first | Build governed foundation before consumer experiences | ✓ Good — lineage works |
| Power BI primary target | Proven in reference implementation; enterprise standard | ✓ Good — /stagegold ready |
| Parquet for pipeline stages | Good performance characteristics, schema preservation | ✓ Good — DuckDB queries fast |
| Python stack | User's known language; good for data pipelines | ✓ Good — 19.5k LOC in 4 days |
| Rule-based NLP for lineage | Deterministic, fast, no ML dependencies | ✓ Good — 34 query tests pass |
| NetworkX for lineage DAG | Battle-tested graph library, simple API | ✓ Good — 106 nodes, 79 edges |
| Brookfield NOC-SOC crosswalk | MIT-licensed, 1,467 validated mappings | ✓ Good — full NOC coverage |
| OpenAI Structured Outputs | Guaranteed schema compliance for LLM | ✓ Good — reliable imputation |
| SSE for demo streaming | Real-time narration without WebSockets | ✓ Good — simple, reliable |
| RTM for compliance logs | Industry-standard traceability format | ✓ Good — auditable compliance |
| RFC 9457 error format | Standard, interoperable, tool support | ✓ Good — ProblemDetail model |
| Environment-based CORS | Flexible deployment without code changes | ✓ Good — CORS_ORIGINS env var |
| DDL comments from catalog | Single source of truth for metadata | ✓ Good — semantic COMMENT clauses |
| Workforce dynamic taxonomy | Preserve bronze folder semantics | ✓ Good — demand/supply classification |
| Docker healthcheck ordering | Reliable service startup | ✓ Good — demo waits for API |
| Mermaid architecture diagrams | Renders in GitHub/VS Code | ✓ Good — visual documentation |

---
*Last updated: 2026-02-04 after v3.0 milestone initialization*
