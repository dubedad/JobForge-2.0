# Requirements: JobForge 2.0

**Defined:** 2026-01-18
**Core Value:** Auditable provenance from source to output — every artifact traces back to authoritative sources with DADM compliance scoring.

## v1 Requirements

Requirements for initial release. Each maps to roadmap phases.

### Data Pipeline

- [ ] **PIPE-01**: Implement medallion pipeline (staged -> bronze -> silver -> gold with parquet files)
- [ ] **PIPE-02**: Ingest DIM NOC table
- [ ] **PIPE-03**: Ingest NOC attribute tables (Element, Oasis)
- [ ] **PIPE-04**: Ingest NOC COPS forecasting data
- [ ] **PIPE-05**: Ingest Job Architecture table
- [ ] **PIPE-06**: Ingest DIM Occupations (Occupational Groups) table

### Semantic Model

- [ ] **WIQ-01**: Create WiQ schema with relationships and proper cardinality

### Power BI Deployment

- [ ] **PBI-01**: `/stagegold` command deploys entire WiQ model to Power BI in one operation

### Data Governance

- [ ] **GOV-01**: Generate Data Catalogue for WiQ

### Conversational Interface

- [ ] **CONV-01**: WiQ can answer lineage queries (explain its own data pipeline)

## v2 Requirements

Deferred to future release. Tracked but not in current roadmap.

### Data Integration

- **INT-01**: O*NET/SOC integration with crosswalk mapping
- **INT-02**: Confidence scoring for NOC-SOC mappings

### Power BI Enhancement

- **PBI-02**: Auto-populate table/column descriptions from business glossary
- **PBI-03**: DAX measures for standard reporting (headcount, FTE, vacancy rates)
- **PBI-04**: Status visuals for data management team
- **PBI-05**: Planning visuals for HR team

### Data Governance Expansion

- **GOV-02**: Business glossary with standard workforce terms
- **GOV-03**: Lineage documentation export
- **GOV-04**: Export to MS Purview format
- **GOV-05**: Export to Denodo format

### Conversational Enhancement

- **CONV-02**: Natural language queries on jobs and forecasts
- **CONV-03**: Query explanation with source citations
- **CONV-04**: DADM compliance queries

### Manager Artifacts

- **MGR-01**: Job Description builder
- **MGR-02**: Performance agreement generation
- **MGR-03**: Learning plan generation
- **MGR-04**: Authority/differentiation quadrant controls

## Out of Scope

Explicitly excluded. Documented to prevent scope creep.

| Feature | Reason |
|---------|--------|
| Real-time job posting ingestion | Job Bank already does this; integrate later if needed |
| Full HRIS functionality | Existing government systems (PeopleSoft, Phoenix successor) |
| Employee-level data storage | Privacy constraints; focus on occupational data |
| Automated hiring decisions | DADM compliance risk; support decisions, never make them |
| Resume parsing | Solved problem with existing vendors; scope creep |
| Training delivery/LMS | Separate domain; government has existing systems |

## Traceability

Which phases cover which requirements. Updated during roadmap creation.

| Requirement | Phase | Status |
|-------------|-------|--------|
| PIPE-01 | Phase 1: Pipeline Infrastructure | Pending |
| PIPE-02 | Phase 2: Data Ingestion | Pending |
| PIPE-03 | Phase 2: Data Ingestion | Pending |
| PIPE-04 | Phase 2: Data Ingestion | Pending |
| PIPE-05 | Phase 2: Data Ingestion | Pending |
| PIPE-06 | Phase 2: Data Ingestion | Pending |
| WIQ-01 | Phase 3: WiQ Semantic Model | Pending |
| PBI-01 | Phase 4: Power BI Deployment | Pending |
| GOV-01 | Phase 5: Data Governance and Lineage | Pending |
| CONV-01 | Phase 5: Data Governance and Lineage | Pending |

**Coverage:**
- v1 requirements: 10 total
- Mapped to phases: 10
- Unmapped: 0

---
*Requirements defined: 2026-01-18*
*Last updated: 2026-01-18 after roadmap creation*
