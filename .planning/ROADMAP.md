# Roadmap: JobForge 2.0

## Milestones

- v1.0 MVP - Phases 1-5 (shipped 2026-01-19)
- v2.0 Self-Imputing WiQ - Phases 6-10 (shipped 2026-01-20)
- v2.1 Orbit Integration - Phases 11-13 (shipped 2026-01-21)
- v3.0 Data Layer Expansion - Phases 14-16 (in progress)

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

### v3.0 Data Layer Expansion (IN PROGRESS)

**Milestone Goal:** Expand the WiQ data layer with TBS Occupational Groups and CAF Careers data, enabling downstream apps (JD Builder Lite, veteran transition tools) to query governed gold models instead of scraping.

**Phase Numbering:**
- Integer phases (14, 15, 16): Planned milestone work
- Decimal phases (14.1, 14.2): Urgent insertions (marked with INSERTED)

- [ ] **Phase 14: OG Core** - TBS Occupational Groups scraping, gold tables, NOC concordance
- [ ] **Phase 15: CAF Core** - CAF Careers scraping, gold tables, bridges to NOC/JA
- [ ] **Phase 16: Extended Metadata** - Qualification standards, job evaluation, training, governance

## Phase Details

### Phase 14: OG Core
**Goal**: TBS Occupational Groups data scraped and loaded into gold tables with NOC concordance
**Depends on**: Phase 13 (v2.1 completed)
**Requirements**: OG-01, OG-02, OG-06, OG-07, OG-10
**Success Criteria** (what must be TRUE):
  1. User can query all 65 TBS occupational groups with definitions
  2. User can query ~200 subgroups linked to parent groups
  3. User can look up which occupational group(s) a NOC code maps to
  4. All tables have full provenance (source URL, scrape timestamp)
  5. JD Builder Lite can consume `bridge_noc_og` for deterministic classification
**Plans**: TBD (created during /gsd:plan-phase 14)

### Phase 15: CAF Core
**Goal**: CAF Careers data scraped and loaded into gold tables with bridges to NOC and Job Architecture
**Depends on**: Phase 14
**Requirements**: CAF-01, CAF-02, CAF-03, CAF-04, CAF-05, CAF-07, CAF-08, CAF-09
**Success Criteria** (what must be TRUE):
  1. User can query all 107 CAF occupations with full metadata
  2. User can query 12 CAF job families
  3. User can look up civilian equivalents for any CAF occupation
  4. User can find NOC codes associated with CAF occupations
  5. User can find Job Architecture matches with confidence scores
  6. All tables have full provenance (source URL, scrape timestamp, match algorithm)
**Plans**: TBD (created during /gsd:plan-phase 15)

### Phase 16: Extended Metadata
**Goal**: Enrich OG and CAF data with qualification standards, job evaluation, training requirements, and governance
**Depends on**: Phase 15
**Requirements**: OG-03, OG-04, OG-05, OG-08, OG-09, CAF-06, GOV-09, GOV-10
**Success Criteria** (what must be TRUE):
  1. User can query qualification standards per occupational group/subgroup
  2. User can query job evaluation standards
  3. User can query rates of pay (represented/unrepresented)
  4. User can query CAF training requirements per occupation
  5. All new tables have DMBOK practice provenance
  6. Data catalogue updated with all new table metadata
**Plans**: TBD (created during /gsd:plan-phase 16)

**Note:** Phase 16 may be deferred to v3.1 if v3.0 timeline requires it.

## Progress

**Execution Order:**
Phases execute in numeric order: 14 -> 14.1 (if any) -> 15 -> 15.1 (if any) -> 16

| Phase | Milestone | Plans Complete | Status | Completed |
|-------|-----------|----------------|--------|-----------|
| 14. OG Core | v3.0 | 0/? | Pending | — |
| 15. CAF Core | v3.0 | 0/? | Pending | — |
| 16. Extended Metadata | v3.0 | 0/? | Pending | — |

---
*Roadmap created: 2026-01-20*
*v3.0 phases added: 2026-02-04*
