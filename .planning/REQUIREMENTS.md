# Requirements: JobForge v4.0 Governed Data Foundation

**Defined:** 2026-02-05
**Core Value:** Auditable provenance from source to output — every artifact traces back to authoritative sources.

## v4.0 Requirements

Requirements for v4.0 milestone. Each maps to roadmap phases (17-23).

### Governance Compliance

- [ ] **GOV-10**: DAMA compliance evidence links with quantitative metrics (not just artifacts)
- [ ] **GOV-11**: Lineage-to-policy traceability — link data relationships to TBS directive clauses
- [ ] **GOV-12**: Automated DAMA DMBOK audit with phase-level compliance scoring
- [ ] **GOV-13**: Policy provenance tracking at document/relationship level

### Data Quality

- [ ] **DQ-01**: GC DQMF 9-dimension scoring per gold table
- [ ] **DQ-02**: Completeness metric — NULL rate per column for all tables
- [ ] **DQ-03**: Timeliness metric — days since last refresh per table
- [ ] **DQ-04**: Data quality API endpoint (`/api/quality/table/{table}`)
- [ ] **DQ-05**: GC DQMF dashboard with 9-dimension radar chart per table
- [ ] **DQ-06**: Quality trend storage — historical DQ scores for degradation detection
- [ ] **DQ-07**: Coherence metric — FK integrity scores per bridge table
- [ ] **DQ-08**: Accuracy validation rules — pattern validation for NOC codes and standard columns

### Business Metadata

- [ ] **BM-01**: Business purpose field in catalog for all gold tables
- [ ] **BM-02**: Business questions field in catalog (minimum 3 per core table)
- [ ] **BM-03**: Business owner field in catalog linking tables to stewards
- [ ] **BM-04**: Business metadata interview workflow — CLI-guided stakeholder capture

### O*NET Integration

- [ ] **ONET-01**: O*NET occupation dimension (`dim_onet_occupation`) — ~900 SOC-aligned occupations
- [ ] **ONET-02**: O*NET abilities attribute table with scores per occupation
- [ ] **ONET-03**: O*NET skills attribute table with scores per occupation
- [ ] **ONET-04**: O*NET knowledge attribute table with scores per occupation
- [ ] **ONET-05**: O*NET work activities attribute table with importance/level scores
- [ ] **ONET-06**: O*NET work context attribute table with working conditions
- [ ] **ONET-07**: NOC-O*NET concordance bridge via existing SOC crosswalk (516 NOC codes)
- [ ] **ONET-08**: Local O*NET database cache with offline-first pattern

### PAA/DRF Organizational Context

- [ ] **PAA-01**: PAA/DRF scraper for Open Government Portal datasets
- [ ] **PAA-02**: DND PAA/DRF gold tables (`dim_paa_dnd`, `dim_drf_dnd`)
- [ ] **PAA-03**: DFO PAA/DRF gold tables (`dim_paa_dfo`, `dim_drf_dfo`)
- [ ] **PAA-04**: Elections Canada PAA/DRF gold tables (`dim_paa_ec`, `dim_drf_ec`)
- [ ] **PAA-05**: Bridge table linking OG to PAA programs (`bridge_og_paa`)
- [ ] **PAA-06**: Flexible schema accommodating 3-5 hierarchy levels across departments

### GC HR Data Model Alignment

- [ ] **HRDM-01**: Ingest GC HR data dictionary spreadsheet as reference tables (`data/reference/hr_erd/`)
- [ ] **HRDM-02**: Store HR Services ERD PDF diagrams with provenance metadata (visual blueprint)
- [ ] **HRDM-03**: Column-level mapping — JobForge catalog columns → HR ERD entities/attributes
- [ ] **HRDM-04**: Extend HR data dictionary WITH JobForge gold tables (add open data tables to dictionary)
- [ ] **HRDM-05**: Catalog enrichment with `hr_erd_entity` and `hr_erd_attribute` fields per column
- [ ] **HRDM-06**: Bidirectional gap analysis document — what JobForge has vs what HR DM covers
- [ ] **HRDM-07**: Alignment recommendations — how to close gaps
- [ ] **HRDM-08**: Version-dated alignment status for tracking over time

### Job Architecture Enrichment

- [ ] **JA-01**: Semantic descriptions for all job functions
- [ ] **JA-02**: Semantic descriptions for all job families
- [ ] **JA-03**: Metadata completeness audit — identify gaps in JA coverage
- [ ] **JA-04**: Catalog enrichment following Phase 12 patterns

## Future Requirements (v5.0+ Scope)

**Conversational Intelligence (v5.0):**
- **AGENT-01**: Natural language quality queries ("What's the quality of COPS data?")
- **AGENT-02**: Automated quality remediation workflows
- **AGENT-03**: ML-based anomaly detection for quality degradation
- **AGENT-04**: 6 specialized agents (Business, Architecture, Engineering, Governance, Performance, Exec Influencer)
- **AGENT-05**: Megatrend Monitor with control chart monitoring
- **AGENT-06**: Benefits Realization tracking

**Extended Data:**
- **EXT-01**: O*NET interests table — RIASEC vocational profiles
- **EXT-02**: O*NET work styles table — personal characteristics
- **EXT-03**: O*NET tasks table — occupation-specific task statements
- **EXT-04**: Full PAA/DRF for all 300+ departments

## Out of Scope

| Feature | Reason |
|---------|--------|
| Real-time data quality monitoring | Adds operational complexity; JobForge is analytical, not transactional |
| ML-based anomaly detection | v5.0 agent territory; rule-based is sufficient for v4.0 |
| Custom quality dimensions | GC DQMF has 9 standard dimensions; custom adds confusion |
| Quality remediation workflows | v5.0 agent territory; requires human-in-loop |
| Third-party DQ tool integration | Adds dependencies; JobForge should be self-contained |
| Individual-level DADM compliance | JobForge is decision-SUPPORT, not decision-MAKING |
| Automated AIA completion | AIA requires human judgment on impact levels |
| Replicating full HR ERD schema in JobForge | JobForge extends HR data dictionary, not replaces it; artifact-backed provenance sufficient |
| O*NET full database import | 900+ occupations, import only NOC-mapped ones |

## Traceability

Which phases cover which requirements. Updated during roadmap creation.

| Requirement | Phase | Status |
|-------------|-------|--------|
| GOV-10 | Phase 17 | Pending |
| GOV-11 | Phase 17 | Pending |
| GOV-12 | Phase 17 | Pending |
| GOV-13 | Phase 17 | Pending |
| DQ-01 | Phase 18 | Pending |
| DQ-02 | Phase 18 | Pending |
| DQ-03 | Phase 18 | Pending |
| DQ-04 | Phase 18 | Pending |
| DQ-05 | Phase 18 | Pending |
| DQ-06 | Phase 18 | Pending |
| DQ-07 | Phase 18 | Pending |
| DQ-08 | Phase 18 | Pending |
| BM-01 | Phase 19 | Pending |
| BM-02 | Phase 19 | Pending |
| BM-03 | Phase 19 | Pending |
| BM-04 | Phase 19 | Pending |
| ONET-01 | Phase 20 | Pending |
| ONET-02 | Phase 20 | Pending |
| ONET-03 | Phase 20 | Pending |
| ONET-04 | Phase 20 | Pending |
| ONET-05 | Phase 20 | Pending |
| ONET-06 | Phase 20 | Pending |
| ONET-07 | Phase 20 | Pending |
| ONET-08 | Phase 20 | Pending |
| JA-01 | Phase 21 | Pending |
| JA-02 | Phase 21 | Pending |
| JA-03 | Phase 21 | Pending |
| JA-04 | Phase 21 | Pending |
| PAA-01 | Phase 22 | Pending |
| PAA-02 | Phase 22 | Pending |
| PAA-03 | Phase 22 | Pending |
| PAA-04 | Phase 22 | Pending |
| PAA-05 | Phase 22 | Pending |
| PAA-06 | Phase 22 | Pending |
| HRDM-01 | Phase 23 | Pending |
| HRDM-02 | Phase 23 | Pending |
| HRDM-03 | Phase 23 | Pending |
| HRDM-04 | Phase 23 | Pending |
| HRDM-05 | Phase 23 | Pending |
| HRDM-06 | Phase 23 | Pending |
| HRDM-07 | Phase 23 | Pending |
| HRDM-08 | Phase 23 | Pending |

**Coverage:**
- v4.0 requirements: 40 total
- Mapped to phases: 40
- Unmapped: 0 ✓

---
*Requirements defined: 2026-02-05*
*Last updated: 2026-02-05 after milestone initialization*
