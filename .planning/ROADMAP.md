# Roadmap: JobForge 2.0

**Created:** 2026-01-18
**Depth:** Standard (5-8 phases)
**Coverage:** 10/10 v1 requirements mapped

## Overview

JobForge 2.0 delivers a workforce intelligence platform in five phases following natural dependency order: pipeline infrastructure enables data ingestion, ingested data feeds the semantic model, the semantic model deploys to Power BI, and governance artifacts plus conversational lineage complete the governed data product. Each phase delivers a verifiable capability that unblocks the next.

---

## Phase 1: Pipeline Infrastructure ✓

**Goal:** Establish medallion pipeline framework so data can flow from source to gold layer with full provenance tracking.

**Dependencies:** None (foundation)

**Requirements:**
- PIPE-01: Implement medallion pipeline (staged -> bronze -> silver -> gold with parquet files)

**Plans:** 3 plans

Plans:
- [x] 01-01-PLAN.md - Project setup and data directory structure with Pydantic models
- [x] 01-02-PLAN.md - Core pipeline engine with layer classes and provenance tracking
- [x] 01-03-PLAN.md - Metadata catalog, DuckDB query interface, and end-to-end tests

**Completed:** 2026-01-18

**Success Criteria:**
1. ✓ Pipeline can accept a source file and write it through all four layers (staged -> bronze -> silver -> gold)
2. ✓ Each layer produces parquet files with provenance columns (_source_file, _ingested_at, _batch_id)
3. ✓ Layer transitions are logged and queryable (which files moved when)
4. ✓ Gold layer output is queryable via DuckDB SQL

---

## Phase 2: Data Ingestion ✓

**Goal:** All five source tables are ingested through the pipeline and available in gold layer for semantic modeling.

**Dependencies:** Phase 1 (pipeline infrastructure must exist)

**Requirements:**
- PIPE-02: Ingest DIM NOC table
- PIPE-03: Ingest NOC attribute tables (Element, Oasis)
- PIPE-04: Ingest NOC COPS forecasting data
- PIPE-05: Ingest Job Architecture table
- PIPE-06: Ingest DIM Occupations (Occupational Groups) table

**Plans:** 3 plans

Plans:
- [x] 02-01-PLAN.md — Source registry infrastructure and DIM NOC ingestion to gold layer
- [x] 02-02-PLAN.md — NOC attribute tables (OASIS proficiency + Element text) ingestion
- [x] 02-03-PLAN.md — COPS forecasting, Job Architecture, and DIM Occupations ingestion

**Completed:** 2026-01-18

**Success Criteria:**
1. ✓ DIM NOC table exists in gold layer with all 516 NOC unit groups queryable by code
2. ✓ NOC Element and Oasis attribute tables exist in gold layer linked to NOC codes
3. ✓ NOC COPS forecasting facts exist in gold layer with NOC foreign keys
4. ✓ Job Architecture table exists in gold layer with job titles and classifications
5. ✓ DIM Occupations (Occupational Groups) table exists in gold layer linked to Job Architecture

---

## Phase 3: WiQ Semantic Model ✓

**Goal:** Gold layer tables are organized into a dimensional model with defined relationships and proper cardinality for Power BI consumption.

**Dependencies:** Phase 2 (all source tables must be ingested)

**Requirements:**
- WIQ-01: Create WiQ schema with relationships and proper cardinality

**Plans:** 2 plans

Plans:
- [x] 03-01-PLAN.md — Semantic model Pydantic definitions and parquet introspection utilities
- [x] 03-02-PLAN.md — WiQ schema definition, validation, and JSON export

**Completed:** 2026-01-19

**Success Criteria:**
1. ✓ WiQ schema defines all dimension and fact tables with explicit relationships
2. ✓ DIM NOC connects to Element, Oasis, and COPS tables with documented cardinality (1:M)
3. ✓ DIM Job Architecture connects to DIM Occupations with documented cardinality
4. ✓ Relationship definitions are machine-readable (can be consumed by deployment scripts)
5. ✓ Star schema validates for Power BI consumption (no circular relationships, single direction)

---

## Phase 4: Power BI Deployment ✓

**Goal:** The entire WiQ semantic model deploys to Power BI in one command with all metadata and relationships intact.

**Dependencies:** Phase 3 (WiQ schema must be defined)

**Requirements:**
- PBI-01: `/stagegold` command deploys entire WiQ model to Power BI in one operation

**Plans:** 2 plans

Plans:
- [x] 04-01-PLAN.md — Type mapping utilities and MCP client wrapper
- [x] 04-02-PLAN.md — WiQDeployer orchestrator, Rich UI, and /stagegold CLI command

**Completed:** 2026-01-19

**Note:** MCP server integration deferred; user will use VS Code Power BI Desktop integration (same workflow as prototype).

**Success Criteria:**
1. ✓ Running `/stagegold` creates deployment specifications from WiQ schema
2. ✓ All tables mapped with correct names and column types
3. ✓ All relationships mapped with correct cardinality
4. ✓ Deployment orchestrator ready for MCP or manual VS Code workflow
5. ✓ Rich terminal UI for deployment narration

---

## Phase 5: Data Governance and Lineage

**Goal:** WiQ produces data governance artifacts and can explain its own data pipeline through conversational queries.

**Dependencies:** Phase 4 (semantic model must be deployed for governance artifacts to document)

**Requirements:**
- GOV-01: Generate Data Catalogue for WiQ
- CONV-01: WiQ can answer lineage queries (explain its own data pipeline)

**Plans:** 3 plans

Plans:
- [ ] 05-01-PLAN.md — LineageGraph infrastructure with NetworkX DAG from transition logs
- [ ] 05-02-PLAN.md — Data Catalogue generation from WiQ schema and parquet metadata
- [ ] 05-03-PLAN.md — LineageQueryEngine with natural language parsing and /lineage CLI

**Success Criteria:**
1. Data Catalogue generation produces table and column documentation for all WiQ entities
2. Data Catalogue includes source system, data types, and business descriptions
3. Lineage query "Where does DIM NOC come from?" returns the pipeline path (source -> staged -> bronze -> silver -> gold)
4. Lineage query "What tables feed FACT NOC COPS?" returns upstream dependencies
5. Lineage answers include provenance metadata (source files, ingestion timestamps)

---

## Progress

| Phase | Name | Status | Requirements |
|-------|------|--------|--------------|
| 1 | Pipeline Infrastructure | ✓ Complete | PIPE-01 |
| 2 | Data Ingestion | ✓ Complete | PIPE-02, PIPE-03, PIPE-04, PIPE-05, PIPE-06 |
| 3 | WiQ Semantic Model | ✓ Complete | WIQ-01 |
| 4 | Power BI Deployment | ✓ Complete | PBI-01 |
| 5 | Data Governance and Lineage | Planned (3 plans) | GOV-01, CONV-01 |

**Total:** 4/5 phases complete | 8/10 requirements delivered

---

## Dependency Graph

```
Phase 1 (Pipeline Infrastructure)
    |
    v
Phase 2 (Data Ingestion)
    |
    v
Phase 3 (WiQ Semantic Model)
    |
    v
Phase 4 (Power BI Deployment)
    |
    v
Phase 5 (Data Governance and Lineage)
```

Linear dependency chain: each phase unblocks exactly one subsequent phase.

---
*Roadmap created: 2026-01-18*
*Last updated: 2026-01-19 - Phase 5 planned (3 plans in 2 waves)*
