# Requirements: JobForge 2.0

**Defined:** 2026-01-19
**Core Value:** Auditable provenance from source to output — every artifact traces back to authoritative sources, including DADM directive chapter and verse.

## v2.0 Requirements

Requirements for self-imputing model and live demo. Each maps to roadmap phases.

### Imputation & Data Quality

- [x] **IMP-01**: Validate and port imputation system from prototype
- [x] **IMP-02**: Hierarchical attribute inheritance (L5->L6->L7 filtered context)
- [x] **IMP-03**: O*NET API integration for SOC-aligned attribute candidates
- [x] **IMP-04**: LLM-powered attribute imputation for empty cells
- [x] **IMP-05**: Description generation (job titles, families, functions)
- [x] **IMP-06**: Multiple description sources with provenance (authoritative vs LLM-generated)

### New Data Sources

- [x] **SRC-01**: Scrape TBS Occupational Groups page with full provenance
- [x] **SRC-02**: Follow embedded links for occupational group metadata
- [x] **SRC-03**: Extend DIM Occupations schema with scraped fields

### Demo & MCP

- [ ] **MCP-01**: Port MCP configuration from prototype to JobForge 2.0
- [ ] **MCP-02**: `/stagegold` live demo via MCP (Power BI + UI split screen)
- [ ] **MCP-03**: Basic UI for demo narration (what JobForge is doing)

### Governance & Compliance

- [ ] **GOV-02**: DADM traceability log — demonstrates observable compliance with Directive requirements
- [ ] **GOV-03**: DAMA traceability log — demonstrates observable compliance with DAMA DMBOK
- [ ] **GOV-04**: Job classification log — demonstrates observable compliance with Classification Policy, Process and Practice
- [ ] **GOV-05**: Conversational interface for data queries
- [ ] **GOV-06**: Conversational interface for metadata queries

## v3+ Requirements

Deferred to future release. Tracked but not in current roadmap.

### Extended Integration

- **INT-01**: Extended O*NET/SOC crosswalk beyond imputation use case
- **INT-02**: Confidence scoring refinements for NOC-SOC mappings

### Power BI Enhancements

- **PBI-02**: Auto-populate table/column descriptions from business glossary
- **PBI-03**: DAX measures for standard reporting (headcount, FTE, vacancy rates)
- **PBI-04**: Status visuals for data management team
- **PBI-05**: Planning visuals for HR team

### Export Formats

- **GOV-07**: Export to MS Purview format
- **GOV-08**: Export to Denodo format

### Job Classification

- **CLASS-01**: Job classification automation (second phase of job desc builder)

## Out of Scope

Explicitly excluded. Documented to prevent scope creep.

| Feature | Reason |
|---------|--------|
| Manager artifact building (JD builder) | v3+ after model refinement complete |
| Performance agreements | v3+ after model refinement complete |
| Departmental position data integration | Privacy constrained |
| Employee-level data | Privacy constrained |
| Real-time sync with org HR systems | Manual export/import for now |
| Real-time job posting ingestion | Job Bank already does this |
| Full HRIS functionality | Existing government systems handle this |
| Automated hiring decisions | DADM compliance risk |

## Traceability

Which phases cover which requirements. Updated during roadmap creation.

| Requirement | Phase | Status |
|-------------|-------|--------|
| IMP-01 | Phase 6 | Complete |
| IMP-02 | Phase 6 | Complete |
| IMP-03 | Phase 7 | Complete |
| IMP-04 | Phase 7 | Complete |
| IMP-05 | Phase 8 | Complete |
| IMP-06 | Phase 8 | Complete |
| SRC-01 | Phase 7 | Complete |
| SRC-02 | Phase 7 | Complete |
| SRC-03 | Phase 7 | Complete |
| MCP-01 | Phase 9 | Pending |
| MCP-02 | Phase 9 | Pending |
| MCP-03 | Phase 9 | Pending |
| GOV-02 | Phase 10 | Pending |
| GOV-03 | Phase 10 | Pending |
| GOV-04 | Phase 10 | Pending |
| GOV-05 | Phase 10 | Pending |
| GOV-06 | Phase 10 | Pending |

**Coverage:**
- v2.0 requirements: 17 total
- Mapped to phases: 17
- Unmapped: 0

---
*Requirements defined: 2026-01-19*
*Last updated: 2026-01-20 after Phase 8 completion*
