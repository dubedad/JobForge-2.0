# Roadmap: JobForge 2.0

## Milestones

- v1.0 MVP - Phases 1-5 (shipped 2026-01-19)
- v2.0 Self-Imputing Model + Live Demo - Phases 6-10 (shipped 2026-01-20)

## Overview

v2.0 enables WiQ to impute its own missing data through hierarchical inheritance, O*NET API integration, and LLM calls — all with full provenance. The milestone culminates in a live demo via MCP showing Power BI building the model in real-time, plus compliance logs demonstrating DADM/DAMA observability and a conversational interface for querying data and metadata.

## Phases

**Phase Numbering:**
- Integer phases (1, 2, 3): Planned milestone work
- Decimal phases (2.1, 2.2): Urgent insertions (marked with INSERTED)

Decimal phases appear between their surrounding integers in numeric order.

<details>
<summary>v1.0 MVP (Phases 1-5) - SHIPPED 2026-01-19</summary>

### Phase 1: Pipeline Architecture
**Goal**: Establish medallion pipeline with staged -> bronze -> silver -> gold transformation
**Plans**: 2 plans (complete)

### Phase 2: Core Dimensions
**Goal**: Ingest NOC and Job Architecture dimensions
**Plans**: 3 plans (complete)

### Phase 3: Attributes and Forecasting
**Goal**: Ingest attribute tables and COPS forecasting data
**Plans**: 3 plans (complete)

### Phase 4: Semantic Model
**Goal**: Create WiQ schema with relationships for Power BI deployment
**Plans**: 2 plans (complete)

### Phase 5: Data Governance and Lineage
**Goal**: Generate data catalogue and enable lineage queries
**Plans**: 3 plans (complete)

</details>

## v2.0 Self-Imputing Model + Live Demo

**Milestone Goal:** Enable WiQ to impute missing data using authoritative sources, O*NET API, and LLM calls with full provenance, demonstrated live via MCP.

- [x] **Phase 6: Imputation Foundation** - Port and validate core imputation system with hierarchical inheritance
- [x] **Phase 7: External Data Integration** - O*NET API, LLM imputation, and TBS scraping with provenance
- [x] **Phase 8: Description Generation** - Multi-source descriptions with authoritative vs LLM provenance
- [x] **Phase 9: Demo Infrastructure** - MCP porting and live demo capability with basic UI
- [x] **Phase 10: Governance and Conversational Interface** - Compliance logs and data/metadata query interface

## Phase Details

### Phase 6: Imputation Foundation
**Goal**: Users can impute missing attribute values using hierarchical inheritance from authoritative sources
**Depends on**: Phase 5 (v1.0 complete)
**Requirements**: IMP-01, IMP-02
**Success Criteria** (what must be TRUE):
  1. Imputation system ported from prototype passes validation tests against known outputs
  2. User can trigger imputation on a job title and see attribute values inherited from L5 -> L6 -> L7 hierarchy
  3. Every imputed value has provenance showing which level provided the value
  4. Filtered context correctly scopes inheritance to relevant occupational domain
**Plans**: 2 plans

Plans:
- [x] 06-01-PLAN.md — Port NOC resolution service with Pydantic models and validation tests
- [x] 06-02-PLAN.md — Implement hierarchical attribute inheritance with provenance tracking

### Phase 7: External Data Integration
**Goal**: Users can enrich WiQ with O*NET attributes and TBS occupational group metadata
**Depends on**: Phase 6
**Requirements**: IMP-03, IMP-04, SRC-01, SRC-02, SRC-03
**Success Criteria** (what must be TRUE):
  1. User can query O*NET API for SOC-aligned attribute candidates given a NOC code
  2. LLM can impute attribute values for cells that remain empty after hierarchical inheritance
  3. TBS Occupational Groups page scraped with full provenance (URL, timestamp, extraction method)
  4. Embedded links on TBS page followed to retrieve occupational group metadata
  5. DIM Occupations schema extended with scraped fields, queryable in gold layer
**Plans**: 3 plans

Plans:
- [x] 07-01-PLAN.md — O*NET API integration with NOC-SOC crosswalk and attribute adapter
- [x] 07-02-PLAN.md — LLM-powered attribute imputation service with structured outputs
- [x] 07-03-PLAN.md — TBS scraping with bilingual support and schema extension

### Phase 8: Description Generation
**Goal**: Users can generate descriptions for job titles, families, and functions from multiple sources with clear provenance
**Depends on**: Phase 7
**Requirements**: IMP-05, IMP-06
**Success Criteria** (what must be TRUE):
  1. User can generate descriptions for job titles showing lead statement from L6 level
  2. User can generate descriptions for job families and functions
  3. Each description has provenance indicating source (authoritative text vs LLM-generated)
  4. Multiple description sources available with user ability to see which is which
**Plans**: 2 plans

Plans:
- [x] 08-01-PLAN.md — Description models and source cascade logic
- [x] 08-02-PLAN.md — DescriptionGenerationService with NOC-style prompts

### Phase 9: Demo Infrastructure
**Goal**: Users can run live demo showing Power BI building WiQ model in real-time via MCP
**Depends on**: Phase 8
**Requirements**: MCP-01, MCP-02, MCP-03
**Success Criteria** (what must be TRUE):
  1. MCP configuration ported from prototype and working with JobForge 2.0 codebase
  2. `/stagegold` command can be triggered via MCP and shows Power BI building model live
  3. Basic UI displays narration of what JobForge is doing during demo
  4. Split screen demo works: Power BI on one side, JobForge UI on other
**Plans**: 2 plans

Plans:
- [x] 09-01-PLAN.md — MCP configuration and SSE backend for live streaming
- [x] 09-02-PLAN.md — Wizard UI with bilingual support and real-time updates

### Phase 10: Governance and Conversational Interface
**Goal**: Users can demonstrate compliance via traceability logs and query data/metadata conversationally
**Depends on**: Phase 9
**Requirements**: GOV-02, GOV-03, GOV-04, GOV-05, GOV-06
**Success Criteria** (what must be TRUE):
  1. DADM traceability log shows observable compliance with Directive requirements (chapter and verse)
  2. DAMA traceability log shows observable compliance with DAMA DMBOK practices
  3. Job classification log shows observable compliance with Classification Policy, Process and Practice
  4. User can query data conversationally and get accurate responses from WiQ
  5. User can query metadata conversationally and get lineage/provenance information
**Plans**: 2 plans (Orbit integration deferred to v3.0)

Plans:
- [x] 10-01-PLAN.md — Compliance logs (DADM, DAMA, Classification RTM models and CLI)
- [x] 10-02-PLAN.md — JobForge HTTP API (data query with Claude, metadata query endpoints)

## Progress

**Execution Order:**
Phases execute in numeric order: 6 -> 7 -> 8 -> 9 -> 10

| Phase | Milestone | Plans Complete | Status | Completed |
|-------|-----------|----------------|--------|-----------|
| 1-5 | v1.0 | 13/13 | Complete | 2026-01-19 |
| 6. Imputation Foundation | v2.0 | 2/2 | Complete | 2026-01-19 |
| 7. External Data Integration | v2.0 | 3/3 | Complete | 2026-01-20 |
| 8. Description Generation | v2.0 | 2/2 | Complete | 2026-01-20 |
| 9. Demo Infrastructure | v2.0 | 2/2 | Complete | 2026-01-20 |
| 10. Governance and Conversational | v2.0 | 2/2 | Complete | 2026-01-20 |

---

## v3.0 Future Enhancements (Planned)

**Milestone Goal:** Intelligent query interface, manager-facing UX, and enhanced semantic search capabilities.

### Semantic Search & RAG

- **RAG-01**: Vector database for semantic similarity search (job titles, descriptions, skills)
- **RAG-02**: RAG pipeline for context-aware LLM responses using WiQ data
- **RAG-03**: Knowledge graph enhancement — extend lineage DAG to full entity-relationship graph

### Job Description Builder UX

- **JDB-01**: Manager-facing web UI for job description creation
- **JDB-02**: NOC-aware form with auto-populated fields from WiQ
- **JDB-03**: Real-time validation against classification requirements
- **JDB-04**: Export to GC-compliant formats (Word, PDF with bilingual support)
- **JDB-05**: Audit trail — who edited what, when, with what justification

### Enhanced Integration

- **INT-01**: Extended O*NET/SOC crosswalk beyond imputation use case
- **INT-02**: Confidence scoring refinements for NOC-SOC mappings
- **INT-03**: Real-time Job Bank posting ingestion for market intelligence
- **INT-04**: Orbit integration (DuckDBRetriever, adapter config, deployment)

### Power BI Enhancements

- **PBI-02**: Auto-populate table/column descriptions from business glossary
- **PBI-03**: DAX measures for standard reporting (headcount, FTE, vacancy rates)
- **PBI-04**: Status visuals for data management team
- **PBI-05**: Planning visuals for HR team

### Export & Interoperability

- **GOV-07**: Export to MS Purview format
- **GOV-08**: Export to Denodo format
- **EXP-01**: HRIS integration adapters (PeopleSoft, SAP SuccessFactors)

### Job Classification Automation

- **CLASS-01**: Classification recommendation engine using WiQ + rules
- **CLASS-02**: Classification audit log with rationale capture
- **CLASS-03**: Integration with TBS classification standards

---
*Roadmap created: 2026-01-19*
*v2.0 shipped: 2026-01-20*
*v2.0 phases: 5 (Phase 6-10)*
*v2.0 requirements: 17 mapped*
*v3.0 planned: 19 features across 6 categories*
