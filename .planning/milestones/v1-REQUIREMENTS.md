# Requirements Archive: v1.0 MVP

**Archived:** 2026-01-19
**Status:** SHIPPED

This is the archived requirements specification for v1.0.
For current requirements, see `.planning/PROJECT.md` (Validated/Active sections).

---

## v1 Requirements

**Core Value:** Auditable provenance from source to output — every artifact traces back to authoritative sources with DADM compliance scoring.

### Data Pipeline

- [x] **PIPE-01**: Implement medallion pipeline (staged -> bronze -> silver -> gold with parquet files)
- [x] **PIPE-02**: Ingest DIM NOC table
- [x] **PIPE-03**: Ingest NOC attribute tables (Element, Oasis)
- [x] **PIPE-04**: Ingest NOC COPS forecasting data
- [x] **PIPE-05**: Ingest Job Architecture table
- [x] **PIPE-06**: Ingest DIM Occupations (Occupational Groups) table

### Semantic Model

- [x] **WIQ-01**: Create WiQ schema with relationships and proper cardinality

### Power BI Deployment

- [x] **PBI-01**: `/stagegold` command deploys entire WiQ model to Power BI in one operation

### Data Governance

- [x] **GOV-01**: Generate Data Catalogue for WiQ

### Conversational Interface

- [x] **CONV-01**: WiQ can answer lineage queries (explain its own data pipeline)

---

## Traceability

| Requirement | Phase | Status | Outcome |
|-------------|-------|--------|---------|
| PIPE-01 | Phase 1: Pipeline Infrastructure | Complete | 4-layer medallion with provenance |
| PIPE-02 | Phase 2: Data Ingestion | Complete | 516 NOC unit groups |
| PIPE-03 | Phase 2: Data Ingestion | Complete | 24 attribute tables (Element + OaSIS) |
| PIPE-04 | Phase 2: Data Ingestion | Complete | 8 COPS forecast tables |
| PIPE-05 | Phase 2: Data Ingestion | Complete | 1,987 job titles |
| PIPE-06 | Phase 2: Data Ingestion | Complete | Occupational groups dimension |
| WIQ-01 | Phase 3: WiQ Semantic Model | Complete | 22 relationships validated |
| PBI-01 | Phase 4: Power BI Deployment | Complete | /stagegold CLI command |
| GOV-01 | Phase 5: Data Governance and Lineage | Complete | 24 table catalogues |
| CONV-01 | Phase 5: Data Governance and Lineage | Complete | /lineage CLI command |

**Coverage:**
- v1 requirements: 10 total
- Mapped to phases: 10
- Shipped: 10

---

## Milestone Summary

**Shipped:** 10 of 10 v1 requirements
**Adjusted:** None
**Dropped:** None

All requirements were delivered as specified. No scope changes during milestone.

---
*Archived: 2026-01-19 as part of v1.0 milestone completion*
