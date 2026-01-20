# Roadmap: JobForge 2.0

## Milestones

- v1.0 MVP - Phases 1-5 (shipped 2026-01-19)
- v2.0 Self-Imputing WiQ - Phases 6-10 (shipped 2026-01-20)
- **v2.1 Orbit Integration** - Phases 11-13 (in progress)

## Phases

<details>
<summary>v1.0 MVP (Phases 1-5) - SHIPPED 2026-01-19</summary>

See archived roadmap: `.planning/milestones/v1.0-ROADMAP.md`

</details>

<details>
<summary>v2.0 Self-Imputing WiQ (Phases 6-10) - SHIPPED 2026-01-20</summary>

See archived roadmap: `.planning/milestones/v2.0-ROADMAP.md`

</details>

### v2.1 Orbit Integration (In Progress)

**Milestone Goal:** Deploy WiQ model to Orbit via DuckDBRetriever adapter with intent configuration and natural language query capabilities.

**Phase Numbering:**
- Integer phases (11, 12, 13): Planned milestone work
- Decimal phases (11.1, 11.2): Urgent insertions (marked with INSERTED)

- [ ] **Phase 11: Validation and Hardening** - Validate existing orbit/ components, harden error handling
- [ ] **Phase 12: Schema and Domain Intelligence** - Enhance DDL for SQL accuracy, add workforce-specific patterns
- [ ] **Phase 13: Deployment and Documentation** - Production deployment config and integration guide

## Phase Details

### Phase 11: Validation and Hardening
**Goal**: Orbit adapter routes queries to JobForge API with validated table coverage and user-friendly errors
**Depends on**: Phase 10 (v2.0 completed)
**Requirements**: ORB-01, ORB-02, ORB-03, ORB-04, ORB-12
**Success Criteria** (what must be TRUE):
  1. User can send natural language query from Orbit and receive JobForge API response
  2. User query is classified into correct intent category (data, metadata, compliance, lineage)
  3. User can query any of the 24 gold tables via DuckDBRetriever without errors
  4. User receives actionable error message when query fails (not raw stack trace)
**Plans**: 2 plans

Plans:
- [ ] 11-01-PLAN.md — RFC 9457 error handling + CORS middleware
- [ ] 11-02-PLAN.md — Table coverage tests + intent validation tests

### Phase 12: Schema and Domain Intelligence
**Goal**: Text-to-SQL accuracy improved via enhanced DDL and workforce-specific entity recognition
**Depends on**: Phase 11
**Requirements**: ORB-05, ORB-06, ORB-07, ORB-08, ORB-09
**Success Criteria** (what must be TRUE):
  1. Generated SQL uses correct column names because DDL includes semantic descriptions
  2. Multi-table queries succeed because DDL includes relationship hints for joins
  3. Workforce intelligence queries match domain-specific intent patterns
  4. NOC codes, occupational groups, and job titles are recognized as entities in queries
  5. Query responses include source attribution showing data provenance
**Plans**: 3 plans

Plans:
- [ ] 12-01-PLAN.md — Catalog enrichment with semantic descriptions and workforce_dynamic
- [ ] 12-02-PLAN.md — Enhanced DDL generator with COMMENT statements and relationship hints
- [ ] 12-03-PLAN.md — Query enhancement with workforce patterns and source attribution

### Phase 13: Deployment and Documentation
**Goal**: Orbit + JobForge stack deployable via Docker Compose with complete integration guide
**Depends on**: Phase 12
**Requirements**: ORB-10, ORB-11, ORB-13, ORB-14
**Success Criteria** (what must be TRUE):
  1. User can start Orbit + JobForge stack with single `docker-compose up` command
  2. Environment variables configure API URLs, ports, and credentials without code changes
  3. Cross-origin requests from Orbit frontend to JobForge API succeed (CORS configured)
  4. Integration guide explains architecture with diagram and step-by-step setup
  5. Intent configuration reference enables users to extend query patterns
**Plans**: TBD

Plans:
- [ ] 13-01: TBD
- [ ] 13-02: TBD

## Progress

**Execution Order:**
Phases execute in numeric order: 11 -> 11.1 (if any) -> 12 -> 12.1 (if any) -> 13

| Phase | Milestone | Plans Complete | Status | Completed |
|-------|-----------|----------------|--------|-----------|
| 11. Validation and Hardening | v2.1 | 0/2 | Planned | - |
| 12. Schema and Domain Intelligence | v2.1 | 0/3 | Planned | - |
| 13. Deployment and Documentation | v2.1 | 0/TBD | Not started | - |

---
*Roadmap created: 2026-01-20*
*Milestone: v2.1 Orbit Integration*
