# Project Research Summary: v4.0 Governed Data Foundation

**Project:** JobForge v4.0 — Governed Data Foundation
**Domain:** Data governance, quality measurement, multi-taxonomy integration
**Researched:** 2026-02-05
**Confidence:** MEDIUM-HIGH

---

## Executive Summary

v4.0 completes JobForge's governed data foundation through three capability pillars: (1) **governance compliance** with DAMA DMBOK auditing, DADM compliance verification, and policy provenance tracking; (2) **data quality measurement** implementing GC DQMF 9-dimension scoring with dashboard visualization; and (3) **5-taxonomy data layer** completing the O*NET integration and adding PAA/DRF organizational context. The existing catalog infrastructure (28 tables, 123 lineage logs, 3 compliance frameworks) provides a strong foundation that v4.0 extends without architectural refactoring.

The recommended approach uses **minimal stack additions**: cuallee (not Great Expectations) for Polars-native quality validation, ckanapi for Open Government Portal access, and Streamlit for dashboard UI. Total new dependency footprint is approximately 45MB. All new features integrate through 5 established extension points: compliance layer, quality API endpoint, catalog enrichment, ingestion pipeline, and CLI commands. This is an additive build, not a refactor.

Key risks center on **governance process overhead** (audit becoming an approval gate), **quality metrics without actionability** (dashboard that drives no action), and **O*NET rate limiting** (incomplete data loads). Prevention requires treating audits as informational-not-blocking, limiting to 6 actionable metrics with owners/thresholds, and implementing local database caching for O*NET. The PAA/DRF integration carries moderate risk due to cross-departmental schema variance.

---

## Key Findings

### Recommended Stack

v4.0 requires only 4 new dependencies. The existing Polars/DuckDB/Pydantic/httpx stack handles most requirements.

**Core technologies (new):**
- **cuallee** (>=0.13.0): GC DQMF data quality validation — native Polars/DuckDB support, 50+ built-in checks, JOSS peer-reviewed, 15MB (vs Great Expectations at 50MB)
- **ckanapi** (>=4.9): Open Government Portal access — official CKAN client for PAA/DRF datasets, GET-only, no auth needed
- **Streamlit** (>=1.41.0): Data quality dashboard UI — pure Python, native DuckDB support, production-ready in 2026
- **plotly** (>=6.0.0): Interactive visualizations — integrates with Streamlit, hover/zoom/filter

**Existing stack (reuse, no changes):**
- httpx/tenacity: O*NET API calls (existing ONetClient sufficient)
- pydantic/structlog: DAMA audit logging (extend existing patterns)
- pdfplumber: Policy document parsing (already in pyproject.toml)
- beautifulsoup4: PAA/DRF scraping fallback (established patterns)

**Do NOT use:** Great Expectations (no Polars support), Soda Core (YAML-first conflicts with code-first), Apache Atlas/OpenMetadata (overkill for single project), Evidence BI (introduces Node.js).

### Expected Features

**Must have (table stakes) — 12 features:**
- GC DQMF 9-dimension scoring per table
- Completeness, accuracy, timeliness metrics
- Data quality API endpoint (`/api/quality/table/{table}`)
- Business purpose and business questions per table in catalog
- O*NET occupation dimension (`dim_onet_occupation` with ~900 occupations)
- O*NET attributes (abilities, skills, knowledge, work activities, work context)
- NOC-O*NET concordance bridge (516 NOC codes via SOC crosswalk)
- DAMA compliance evidence links (metrics, not just artifacts)
- Lineage-to-policy traceability

**Should have (differentiators) — top 5:**
- GC DQMF dashboard with 9-dimension radar chart per table
- Automated DAMA DMBOK audit (phase-level compliance scoring)
- Policy provenance at document/relationship level
- PAA/DRF for DND (first department target)
- GC HR Data Model mapping document with gap analysis

**Defer to v5.0:**
- Automated quality alerts/remediation (agent territory)
- Natural language quality queries (conversational agent)
- Full PAA/DRF for all 300+ departments
- O*NET interests, work styles, tasks tables

### Architecture Approach

v4.0 integrates through **5 extension points** in the existing architecture with no refactoring required. All features are additive to established patterns.

**Major components:**
1. **governance/dqmf/** — GC DQMF 9-dimension implementation (dimensions.py, metrics.py, dashboard.py)
2. **governance/policy/** — Policy provenance (parser.py for PDF extraction, provenance.py for artifact-to-clause mapping)
3. **external/paa/** — PAA/DRF scraping (scraper.py using ckanapi, models.py for Pydantic schemas)
4. **ingestion/onet.py** — O*NET occupation ingestion (follows og.py medallion pattern)
5. **api/quality.py** — Quality dashboard endpoints (follows existing FastAPI router patterns)

**Key insight:** O*NET and PAA/DRF use the same PipelineEngine for layer transitions. Quality metrics are stored in catalog JSON files (not a separate database). Dashboard reads from catalog, not separate quality DB.

### Critical Pitfalls

**7 critical pitfalls identified, mapped to phases:**

1. **Governance Audit as Approval Gate** (Phase 17) — Prevention: Audit is informational, not blocking; automate regeneration in CI/CD; target <30 second audit generation; delta audits only.

2. **Data Quality Metrics Without Actionability** (Phase 18) — Prevention: 6 metrics, not 60; owner per metric; thresholds with explicit actions; trend over 7 days, not snapshot; link every metric to source table/column.

3. **Policy Provenance at Wrong Granularity** (Phase 17) — Prevention: Document/relationship level, not paragraph level; canonical canada.ca URLs; version tracking; weekly provenance verification job.

4. **O*NET API Integration Without Caching** (Phase 20) — Prevention: Local database cache as primary source; API as fallback; persistent cache with 30-90 day TTL; pipeline works fully offline after initial cache.

5. **PAA/DRF Data Consistency Across Departments** (Phase 22) — Prevention: One department at a time (DND first); schema accommodates 3-5 hierarchy levels; department-specific adapters; accept incompleteness.

6. **GC HR Data Model Completeness Assumptions** (Phase 23) — Prevention: Gap analysis document, not code changes; version-dated alignment; provisional mappings clearly marked; recommendations for JobForge, not for fixing the model.

7. **Business Metadata Capture Workflow Friction** (Phase 19) — Prevention: Prioritize by usage (dim_noc, cops_employment first); templates not blank fields; batch interviews; async form option; 1 purpose + 3 questions minimum.

---

## Implications for Roadmap

Based on research, suggested 7-phase structure (Phases 17-23):

### Phase 17: Governance Compliance Framework
**Rationale:** Foundation phase — defines compliance check structure, audit trail models, policy provenance patterns. All subsequent phases depend on these models.
**Delivers:** DQMFComplianceLog, PolicyProvenanceLink models; DAMA audit enhancement with phase-level evidence; compliance CLI (`jobforge compliance`)
**Addresses:** DAMA compliance evidence links, lineage-to-policy traceability
**Avoids:** Pitfall 1 (audit as gate) by implementing informational audits; Pitfall 3 (wrong granularity) by starting with document-level provenance

### Phase 18: Data Quality Dashboard
**Rationale:** Depends on Phase 17 models. High visibility deliverable that demonstrates governance value early.
**Delivers:** GC DQMF 9-dimension scoring engine; `/api/quality/` endpoints; Streamlit dashboard UI with radar charts
**Uses:** cuallee for Polars-native validation; Streamlit + plotly for visualization
**Implements:** governance/dqmf/ component
**Avoids:** Pitfall 2 (metrics without actionability) by limiting to 6 core metrics with owners/thresholds

### Phase 19: Business Metadata Capture
**Rationale:** Depends on Phase 18 catalog schema extension. Enables stakeholder engagement while technical work proceeds in parallel.
**Delivers:** business_purpose, business_questions, business_owner fields in catalog; interview workflow (CLI or async form); metadata completeness tracking
**Addresses:** Business purpose per table, business questions per table
**Avoids:** Pitfall 7 (workflow friction) by prioritizing high-usage tables and providing templates

### Phase 20: O*NET Integration
**Rationale:** Can develop in parallel with Phases 18-19 after Phase 17 completes. High business value (completes 5-taxonomy coverage).
**Delivers:** dim_onet_occupation gold table; 5 O*NET attribute tables; bridge_noc_onet concordance; local database cache
**Uses:** Existing ONetClient (extended); ckanapi not needed (O*NET has its own download)
**Implements:** external/onet/scraper.py, ingestion/onet.py
**Avoids:** Pitfall 4 (rate limiting) by implementing local database cache with API fallback

### Phase 21: Job Architecture Enrichment
**Rationale:** Uses business metadata patterns from Phase 19; may leverage O*NET work activities from Phase 20.
**Delivers:** Complete JA descriptions; enriched job functions and families; metadata completeness >90%
**Addresses:** Job architecture completeness gap
**Implements:** Extends Phase 12 enrichment patterns

### Phase 22: PAA/DRF Data Layer
**Rationale:** Similar patterns to O*NET scraping from Phase 20. New data source with higher complexity due to departmental variance.
**Delivers:** dim_paa_activity, dim_drf_outcome gold tables; bridge_og_paa relationship; DND as first department
**Uses:** ckanapi for Open Government Portal; existing scraper patterns
**Avoids:** Pitfall 5 (cross-department inconsistency) by targeting one department, designing for hierarchy variance

### Phase 23: GC HR Data Model Alignment
**Rationale:** Analysis phase requiring complete data model from prior phases. Produces documentation, not code changes.
**Delivers:** GC HR Data Model mapping document; bidirectional gap analysis; alignment recommendations; version-dated alignment status
**Addresses:** Strategic positioning of JobForge in GC ecosystem
**Avoids:** Pitfall 6 (completeness assumptions) by treating as gap analysis, not gap filling

### Phase Ordering Rationale

1. **Phase 17 first** — All subsequent phases depend on governance/compliance models
2. **Phase 18 early** — High-visibility dashboard demonstrates value; uses Phase 17 models
3. **Phases 18/19 and 20 can parallelize** — Dashboard/metadata (internal) vs O*NET (external) have no dependencies
4. **Phase 21 after 19-20** — Needs business metadata patterns and may use O*NET data
5. **Phase 22 after 20** — Uses similar scraping patterns established in O*NET phase
6. **Phase 23 last** — Analysis phase requiring stable data model

### Research Flags

**Phases likely needing deeper research during planning:**
- **Phase 20 (O*NET):** Rate limit behavior undisclosed; verify local database format; confirm attribution requirements
- **Phase 22 (PAA/DRF):** Departmental variance not fully documented; verify DND data availability on Open Government Portal

**Phases with standard patterns (skip research-phase):**
- **Phase 17 (Governance):** DAMA framework well-documented; extends existing ComplianceLog patterns
- **Phase 18 (Quality):** cuallee API documented; GC DQMF 9 dimensions defined in official guidance
- **Phase 19 (Business Metadata):** Extends existing catalog JSON schema; standard field additions
- **Phase 21 (JA Enrichment):** Follows Phase 12 patterns exactly
- **Phase 23 (HR Data Model):** Documentation task; no implementation

---

## Confidence Assessment

| Area | Confidence | Notes |
|------|------------|-------|
| Stack | HIGH | cuallee, ckanapi, Streamlit verified via PyPI and official docs; existing stack reuse confirmed |
| Features | MEDIUM-HIGH | GC DQMF and O*NET authoritative; PAA/DRF availability varies; GC HR Data Model explicitly incomplete |
| Architecture | HIGH | 5 extension points verified against existing codebase; no refactoring required |
| Pitfalls | MEDIUM | Industry patterns well-documented; project-specific impact requires validation during execution |

**Overall confidence:** MEDIUM-HIGH

### Gaps to Address

1. **O*NET Rate Limits:** Exact thresholds undisclosed. Plan: design for offline-first with cache; monitor during Phase 20 initial load.

2. **PAA/DRF Departmental Coverage:** Open Government Portal has DRF data, but department-specific coverage varies. Plan: validate DND data availability in Phase 22 planning.

3. **GC HR Data Model Current State:** Model is "available but incomplete." Plan: Phase 23 is explicitly a gap analysis, not a completion effort.

4. **Stakeholder Availability for Metadata Capture:** Business metadata interviews require domain experts. Plan: prioritize 8 core tables; offer async form alternative.

5. **Streamlit + FastAPI Coexistence:** Both services need separate ports. Plan: document port configuration; consider reverse proxy for production.

---

## Sources

### Primary (HIGH confidence)
- [GC Guidance on Data Quality](https://www.canada.ca/en/government/system/digital-government/digital-government-innovations/information-management/guidance-data-quality.html) — 9 dimensions definition
- [O*NET Web Services](https://services.onetcenter.org/) — API v2.0 specification and Terms of Service
- [O*NET Resource Center](https://www.onetcenter.org/database.html) — Database download and crosswalk files
- [DAMA DMBOK Framework](https://dama.org/learning-resources/dama-data-management-body-of-knowledge-dmbok/) — 11 knowledge areas
- [Directive on Automated Decision-Making](https://www.tbs-sct.canada.ca/pol/doc-eng.aspx?id=32592) — DADM compliance requirements
- [cuallee PyPI](https://pypi.org/project/cuallee/) — Version 0.13.0, Polars/DuckDB support confirmed
- [ckanapi PyPI](https://pypi.org/project/ckanapi/) — Version 4.9, CKAN core team maintained
- [Open Government API](https://open.canada.ca/en/access-our-application-programming-interface-api) — CKAN API for open.canada.ca

### Secondary (MEDIUM confidence)
- [cuallee JOSS Paper](https://joss.theoj.org/papers/10.21105/joss.06684) — Peer-reviewed methodology
- [Monte Carlo Data Quality Metrics](https://www.montecarlodata.com/blog-data-quality-metrics/) — Actionable metrics guidance
- [DataKitchen Six Types of Dashboards](https://datakitchen.io/the-six-types-of-data-quality-dashboards/) — Dashboard design patterns
- [2023-2026 Data Strategy](https://www.canada.ca/en/treasury-board-secretariat/corporate/reports/2023-2026-data-strategy.html) — GC data governance context
- [Next Generation HR and Pay Report](https://www.canada.ca/en/shared-services/corporate/about-us/transparency/publications/2023-24/next-generation-hr-pay-final-findings-report.html) — 70 HRMS complexity documented

### Tertiary (LOW confidence — needs validation)
- [DRF Datasets on Open Government Portal](https://open.canada.ca/data/en/dataset/320e0439-187a-4db5-b120-4079ed05ff99) — Verify specific department coverage
- GC HR Data Model completeness — Limited public documentation; model explicitly incomplete

---

*Research completed: 2026-02-05*
*Ready for roadmap: YES*
