# Roadmap: JobForge 2.0

## Milestones

- v1.0 MVP - Phases 1-5 (shipped 2026-01-19)
- v2.0 Self-Imputing WiQ - Phases 6-10 (shipped 2026-01-20)
- v2.1 Orbit Integration - Phases 11-13 (shipped 2026-01-21)
- v3.0 Data Layer Expansion - Phases 14-16 (shipped 2026-02-05)
- v4.0 Governed Data Foundation - Phases 17-23 (in progress)

## Phases

<details>
<summary>v1.0 MVP (Phases 1-5) - SHIPPED 2026-01-19</summary>

See archived roadmap: `.planning/milestones/v1.0-ROADMAP.md`

</details>

<details>
<summary>v2.0 Self-Imputing WiQ (Phases 6-10) - SHIPPED 2026-01-20</summary>

See archived roadmap: `.planning/milestones/v2.0-ROADMAP.md`

</details>

<details>
<summary>v2.1 Orbit Integration (Phases 11-13) - SHIPPED 2026-01-21</summary>

See archived roadmap: `.planning/milestones/v2.1-ROADMAP.md`

</details>

<details>
<summary>v3.0 Data Layer Expansion (Phases 14-16) - SHIPPED 2026-02-05</summary>

**Milestone Goal:** Expand the WiQ data layer with TBS Occupational Groups and CAF Careers data, enabling downstream apps (JD Builder Lite, veteran transition tools) to query governed gold models instead of scraping.

**Phases:**
- Phase 14: OG Core - TBS Occupational Groups scraping, gold tables, NOC concordance
- Phase 15: CAF Core - CAF Careers scraping, gold tables, bridges to NOC/JA
- Phase 16: Extended Metadata - Qualification standards, job evaluation, training, governance

</details>

### v4.0 Governed Data Foundation (IN PROGRESS)

**Milestone Goal:** Complete JobForge's governed data foundation through governance compliance (DAMA DMBOK auditing, policy provenance), data quality measurement (GC DQMF 9-dimension scoring), business metadata capture, and 5-taxonomy data layer (O*NET integration, PAA/DRF organizational context, GC HR Data Model alignment).

**Phase Numbering:**
- Integer phases (17, 18, 19...): Planned milestone work
- Decimal phases (17.1, 17.2): Urgent insertions (marked with INSERTED)

- [ ] **Phase 17: Governance Compliance Framework** - DAMA audit, policy provenance, lineage-to-policy traceability
- [ ] **Phase 18: Data Quality Dashboard** - GC DQMF 9-dimension scoring, quality API, Streamlit dashboard
- [ ] **Phase 19: Business Metadata Capture** - Business purpose, questions, owner per table; interview workflow
- [ ] **Phase 20: O*NET Integration** - O*NET dimension, 5 attribute tables, NOC concordance, local cache
- [ ] **Phase 21: Job Architecture Enrichment** - JA semantic descriptions, metadata completeness audit
- [ ] **Phase 22: PAA/DRF Data Layer** - PAA/DRF scraper, departmental gold tables, OG-PAA bridge
- [ ] **Phase 23: GC HR Data Model Alignment** - HR ERD ingestion, column mapping, gap analysis, recommendations

## Phase Details

### Phase 17: Governance Compliance Framework
**Goal**: Governance checks trace to policy with quantitative evidence, enabling audit-ready compliance reports
**Depends on**: Phase 16 (v3.0 completed)
**Requirements**: GOV-10, GOV-11, GOV-12, GOV-13
**Success Criteria** (what must be TRUE):
  1. User can view DAMA compliance evidence with quantitative metrics per phase (not just artifact names)
  2. User can trace any data relationship in WiQ to the TBS directive clause it satisfies
  3. User can run automated DAMA DMBOK audit and see phase-level compliance scores
  4. User can query which policies govern a specific table or relationship
**Plans:** TBD (estimated 4-6 plans)

### Phase 18: Data Quality Dashboard
**Goal**: Users can assess and monitor data quality across all gold tables using GC DQMF 9-dimension framework
**Depends on**: Phase 17 (governance models provide audit context)
**Requirements**: DQ-01, DQ-02, DQ-03, DQ-04, DQ-05, DQ-06, DQ-07, DQ-08
**Success Criteria** (what must be TRUE):
  1. User can view GC DQMF 9-dimension quality scores for any gold table
  2. User can query completeness (NULL rate) for any column via API
  3. User can view timeliness (days since refresh) for any table
  4. User can view data quality dashboard with radar charts showing quality dimensions
  5. User can see quality trends over time to detect degradation
**Plans:** TBD (estimated 5-7 plans)

### Phase 19: Business Metadata Capture
**Goal**: Every core table has business context (purpose, questions, owner) captured from domain stakeholders
**Depends on**: Phase 18 (quality dashboard shows which tables lack business context)
**Requirements**: BM-01, BM-02, BM-03, BM-04
**Success Criteria** (what must be TRUE):
  1. User can view business purpose for any gold table in catalog
  2. User can view 3+ business questions per core table showing how it supports decisions
  3. User can identify the business owner/steward for any table
  4. User can run CLI workflow to capture business metadata via guided interview
**Plans:** TBD (estimated 3-4 plans)

### Phase 20: O*NET Integration
**Goal**: O*NET occupation data integrated as 5th taxonomy with full attribute coverage and NOC concordance
**Depends on**: Phase 17 (governance models for provenance tracking)
**Requirements**: ONET-01, ONET-02, ONET-03, ONET-04, ONET-05, ONET-06, ONET-07, ONET-08
**Success Criteria** (what must be TRUE):
  1. User can query ~900 O*NET occupations with SOC alignment
  2. User can query O*NET abilities, skills, and knowledge scores for any occupation
  3. User can query O*NET work activities (importance/level) and work context (conditions)
  4. User can find NOC codes linked to O*NET occupations via SOC crosswalk
  5. O*NET data loads from local cache (offline-first) with API fallback
**Plans:** TBD (estimated 5-7 plans)

### Phase 21: Job Architecture Enrichment
**Goal**: Job Architecture has complete semantic descriptions for functions and families with verified metadata coverage
**Depends on**: Phase 19 (business metadata patterns), Phase 20 (O*NET work activities for context)
**Requirements**: JA-01, JA-02, JA-03, JA-04
**Success Criteria** (what must be TRUE):
  1. User can view semantic descriptions for all job functions
  2. User can view semantic descriptions for all job families
  3. User can run metadata completeness audit showing JA coverage percentage
  4. All enrichment follows Phase 12 catalog patterns with full provenance
**Plans:** TBD (estimated 3-4 plans)

### Phase 22: PAA/DRF Data Layer
**Goal**: PAA/DRF organizational hierarchy for target departments enables job-to-program context
**Depends on**: Phase 20 (similar external data integration patterns)
**Requirements**: PAA-01, PAA-02, PAA-03, PAA-04, PAA-05, PAA-06
**Success Criteria** (what must be TRUE):
  1. User can scrape PAA/DRF data from Open Government Portal via ckanapi
  2. User can query DND PAA and DRF hierarchies (first target department)
  3. User can query DFO PAA and DRF hierarchies (second target department)
  4. User can query Elections Canada PAA and DRF hierarchies (third target department)
  5. User can look up which PAA programs an OG code maps to
  6. Schema accommodates 3-5 hierarchy levels across departments
**Plans:** TBD (estimated 5-6 plans)

### Phase 23: GC HR Data Model Alignment
**Goal**: JobForge data model mapped to GC HR Data Model with documented gaps and recommendations
**Depends on**: Phase 22 (complete data model for accurate gap analysis)
**Requirements**: HRDM-01, HRDM-02, HRDM-03, HRDM-04, HRDM-05, HRDM-06, HRDM-07, HRDM-08
**Success Criteria** (what must be TRUE):
  1. User can view HR data dictionary ingested as reference tables
  2. User can view HR Services ERD diagrams with provenance metadata
  3. User can trace any JobForge catalog column to corresponding HR ERD entity/attribute
  4. User can view extended HR data dictionary including JobForge gold tables
  5. User can view bidirectional gap analysis showing what JobForge has vs HR DM covers
  6. User can view alignment recommendations and version-dated status
**Plans:** TBD (estimated 5-7 plans)

## Progress

**Execution Order:**
Phases execute in numeric order: 17 -> 17.1 (if any) -> 18 -> 18.1 (if any) -> 19 -> 20 -> 21 -> 22 -> 23

| Phase | Milestone | Plans Complete | Status | Completed |
|-------|-----------|----------------|--------|-----------|
| 17. Governance Compliance | v4.0 | 0/TBD | Planned | - |
| 18. Data Quality Dashboard | v4.0 | 0/TBD | Planned | - |
| 19. Business Metadata | v4.0 | 0/TBD | Planned | - |
| 20. O*NET Integration | v4.0 | 0/TBD | Planned | - |
| 21. JA Enrichment | v4.0 | 0/TBD | Planned | - |
| 22. PAA/DRF Data Layer | v4.0 | 0/TBD | Planned | - |
| 23. HR Data Model Alignment | v4.0 | 0/TBD | Planned | - |

---
*Roadmap created: 2026-01-20*
*v3.0 phases added: 2026-02-04*
*v3.0 complete: 2026-02-05*
*v4.0 phases added: 2026-02-05*
