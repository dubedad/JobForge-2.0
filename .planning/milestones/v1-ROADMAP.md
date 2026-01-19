# Milestone v1.0: MVP

**Status:** SHIPPED 2026-01-19
**Phases:** 1-5
**Total Plans:** 13

## Overview

JobForge 2.0 delivers a workforce intelligence platform in five phases following natural dependency order: pipeline infrastructure enables data ingestion, ingested data feeds the semantic model, the semantic model deploys to Power BI, and governance artifacts plus conversational lineage complete the governed data product. Each phase delivers a verifiable capability that unblocks the next.

## Phases

### Phase 1: Pipeline Infrastructure

**Goal**: Establish medallion pipeline framework so data can flow from source to gold layer with full provenance tracking.
**Depends on**: None (foundation)
**Plans**: 3 plans

Plans:
- [x] 01-01-PLAN.md - Project setup and data directory structure with Pydantic models
- [x] 01-02-PLAN.md - Core pipeline engine with layer classes and provenance tracking
- [x] 01-03-PLAN.md - Metadata catalog, DuckDB query interface, and end-to-end tests

**Completed:** 2026-01-18

**Success Criteria (all met):**
1. Pipeline can accept a source file and write it through all four layers
2. Each layer produces parquet files with provenance columns
3. Layer transitions are logged and queryable
4. Gold layer output is queryable via DuckDB SQL

---

### Phase 2: Data Ingestion

**Goal**: All five source tables are ingested through the pipeline and available in gold layer for semantic modeling.
**Depends on**: Phase 1 (pipeline infrastructure must exist)
**Plans**: 3 plans

Plans:
- [x] 02-01-PLAN.md - Source registry infrastructure and DIM NOC ingestion to gold layer
- [x] 02-02-PLAN.md - NOC attribute tables (OASIS proficiency + Element text) ingestion
- [x] 02-03-PLAN.md - COPS forecasting, Job Architecture, and DIM Occupations ingestion

**Completed:** 2026-01-18

**Success Criteria (all met):**
1. DIM NOC table exists in gold layer with all 516 NOC unit groups
2. NOC Element and Oasis attribute tables exist in gold layer
3. NOC COPS forecasting facts exist in gold layer
4. Job Architecture table exists in gold layer
5. DIM Occupations table exists in gold layer

---

### Phase 3: WiQ Semantic Model

**Goal**: Gold layer tables are organized into a dimensional model with defined relationships and proper cardinality for Power BI consumption.
**Depends on**: Phase 2 (all source tables must be ingested)
**Plans**: 2 plans

Plans:
- [x] 03-01-PLAN.md - Semantic model Pydantic definitions and parquet introspection utilities
- [x] 03-02-PLAN.md - WiQ schema definition, validation, and JSON export

**Completed:** 2026-01-19

**Success Criteria (all met):**
1. WiQ schema defines all dimension and fact tables with explicit relationships
2. DIM NOC connects to Element, Oasis, and COPS tables with documented cardinality (1:M)
3. DIM Job Architecture connects to DIM Occupations with documented cardinality
4. Relationship definitions are machine-readable
5. Star schema validates for Power BI consumption

---

### Phase 4: Power BI Deployment

**Goal**: The entire WiQ semantic model deploys to Power BI in one command with all metadata and relationships intact.
**Depends on**: Phase 3 (WiQ schema must be defined)
**Plans**: 2 plans

Plans:
- [x] 04-01-PLAN.md - Type mapping utilities and MCP client wrapper
- [x] 04-02-PLAN.md - WiQDeployer orchestrator, Rich UI, and /stagegold CLI command

**Completed:** 2026-01-19

**Note:** MCP server integration deferred; user will use VS Code Power BI Desktop integration.

**Success Criteria (all met):**
1. Running `/stagegold` creates deployment specifications from WiQ schema
2. All tables mapped with correct names and column types
3. All relationships mapped with correct cardinality
4. Deployment orchestrator ready for MCP or manual VS Code workflow
5. Rich terminal UI for deployment narration

---

### Phase 5: Data Governance and Lineage

**Goal**: WiQ produces data governance artifacts and can explain its own data pipeline through conversational queries.
**Depends on**: Phase 4 (semantic model must be deployed for governance artifacts to document)
**Plans**: 3 plans

Plans:
- [x] 05-01-PLAN.md - LineageGraph infrastructure with NetworkX DAG from transition logs
- [x] 05-02-PLAN.md - Data Catalogue generation from WiQ schema and parquet metadata
- [x] 05-03-PLAN.md - LineageQueryEngine with natural language parsing and /lineage CLI

**Completed:** 2026-01-19

**Success Criteria (all met):**
1. Data Catalogue generation produces table and column documentation for all WiQ entities
2. Data Catalogue includes source system, data types, and business descriptions
3. Lineage query "Where does DIM NOC come from?" returns the pipeline path
4. Lineage query "What tables feed FACT NOC COPS?" returns upstream dependencies
5. Lineage answers include provenance metadata

---

## Milestone Summary

**Key Decisions:**

- Linear phase dependency: Each phase produces output consumed by next
- Pipeline before semantic model: Cannot define relationships without data to relate
- GOV + CONV in same phase: Both require stable semantic model; both about explainability
- Rule-based NLP for lineage: Deterministic, fast, no ML dependencies
- NetworkX for lineage DAG: Battle-tested graph library, simple API

**Issues Resolved:**

- Polars CSV type inference casting numeric-looking strings as int64
- Pydantic field naming restrictions for underscore-prefixed provenance columns
- Float reconstruction for OaSIS codes inferred as f64
- UTF-8 encoding requirements for JSON I/O on Windows

**Technical Debt:**

- Phase 3 & 4 missing SUMMARY.md files (code verified via integration)
- MCP server integration deferred to future milestone

---

*For current project status, see .planning/PROJECT.md*
*Archived: 2026-01-19 as part of v1.0 milestone completion*
