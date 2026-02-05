# Feature Landscape: v4.0 Governed Data Foundation

**Domain:** Data governance, quality measurement, multi-taxonomy integration
**Researched:** 2026-02-05
**Confidence:** MEDIUM-HIGH (GC frameworks well-documented; O*NET authoritative; business metadata patterns established)

---

## Executive Summary

v4.0 completes JobForge's governed data foundation through three major capability areas:

1. **Governance Compliance** - DAMA DMBOK auditing, DADM compliance verification, policy provenance tracking
2. **Data Quality Measurement** - GC DQMF 9-dimension scoring, dashboard visualization, per-table/column metrics
3. **5-Taxonomy Data Layer** - O*NET integration (completing NOC, OG, CAF, JA, O*NET coverage), PAA/DRF for organizational context

The existing catalog infrastructure (24 tables, 123 lineage logs, 3 compliance frameworks) provides strong foundation. v4.0 extends this with quantitative quality metrics, structured business metadata, and the fifth occupational taxonomy.

---

## Table Stakes (Must Have)

Features users expect from a governed data platform. Missing = credibility gap with GC stakeholders.

| Feature | Why Expected | Complexity | Existing Coverage | Dependencies |
|---------|--------------|------------|-------------------|--------------|
| **GC DQMF 9-dimension scoring** | GC standard for data quality; required for TBS compliance discussions | Medium | 0% - not measured | catalog tables exist |
| **Completeness metric per table** | Most basic DQ dimension; "how much is null?" | Low | 0% - row counts only | parquet files |
| **Accuracy validation rules** | Can data be verified against known values? | Medium | 0% - no rules defined | reference data |
| **Timeliness tracking** | When was data last refreshed? | Low | Partial - `updated_at` in catalog | catalog metadata |
| **Data quality API endpoint** | Programmatic access to DQ metrics | Low | 0% - no DQ endpoints | FastAPI existing |
| **Business purpose per table** | "What is this table FOR?" in catalog | Low | Partial - generic descriptions | catalog schema |
| **Business questions per table** | "What can I ask this table?" | Low | 0% - not captured | catalog schema |
| **O*NET occupation dimension** | 5th taxonomy; US DOL authoritative source | High | Existing NOC-SOC crosswalk | O*NET database download |
| **O*NET attribute tables** | Skills, abilities, work activities, work context | Medium | 0% - not ingested | O*NET integration |
| **NOC-O*NET concordance bridge** | Link NOC to O*NET via SOC crosswalk | Medium | Existing SOC crosswalk has 1,467 mappings | bridge_noc_og pattern |
| **DAMA compliance evidence links** | Current dama.json has artifacts, not metrics | Low | 80% - structure exists | dama.json entries |
| **Lineage-to-policy traceability** | Which policy authorizes this data relationship? | Medium | 0% - lineage exists, policy refs don't | governance module |

---

## Differentiators (Competitive Advantage in GC Context)

Features that set JobForge apart from generic data catalogs or governance tools.

| Feature | Value Proposition | Complexity | Build in v4.0? | Notes |
|---------|-------------------|------------|----------------|-------|
| **GC DQMF dashboard in demo UI** | Visual DQ at a glance; executive-friendly | Medium | YES | Extends existing demo UI |
| **9-dimension radar chart per table** | Intuitive quality visualization | Low | YES | Chart.js in existing demo |
| **Automated DAMA DMBOK audit** | "How DAMA-compliant is this phase?" | Medium | YES | Use managing-data-governance skill |
| **Policy provenance paragraph-level** | Link data element to exact TBS clause | High | YES | mapping-policy-provenance skill |
| **Business metadata interview workflow** | Guided capture of table purpose/questions | Medium | YES | Stakeholder engagement value |
| **O*NET work activities for NOC codes** | "What tasks does this occupation do?" | Medium | YES | Via crosswalk imputation |
| **O*NET abilities/skills profiles** | Rich competency data beyond OaSIS | Medium | YES | Expands attribute coverage |
| **Quality trend over time** | "Is DQ improving or degrading?" | Medium | MAYBE | Requires historical storage |
| **PAA/DRF organizational context** | Job factors for classification decisions | High | YES | DND, DFO, Elections target |
| **GC HR Data Model mapping document** | Positions JobForge in GC ecosystem | Medium | YES | Strategic value |
| **Automated quality alerts** | Notify on quality degradation | Medium | NO | v5.0 agent territory |
| **Natural language quality queries** | "What's the quality of COPS data?" | Medium | NO | v5.0 agent territory |

**Recommended differentiators for v4.0:**
1. GC DQMF dashboard (executive visibility)
2. Policy provenance tracking (audit-ready)
3. Business metadata capture workflow (stakeholder engagement)
4. O*NET integration (completes 5-taxonomy coverage)

---

## Anti-Features (Out of Scope)

Features to deliberately NOT build. Some distract; others belong in v5.0 agents phase.

| Anti-Feature | Why Avoid | What to Do Instead |
|--------------|-----------|-------------------|
| **Real-time data quality monitoring** | Adds operational complexity; JobForge is analytical, not transactional | Batch quality scoring on pipeline runs |
| **ML-based anomaly detection** | Overly complex for current state; rule-based is sufficient | Define explicit validation rules |
| **Custom quality dimensions** | GC DQMF has 9 standard dimensions; custom adds confusion | Use GC standard dimensions only |
| **Quality remediation workflows** | v5.0 agent territory; requires human-in-loop | Surface issues, don't auto-fix |
| **Third-party DQ tool integration** | Adds dependencies; JobForge should be self-contained | Build native quality scoring |
| **Individual-level DADM compliance** | JobForge is decision-SUPPORT, not decision-MAKING | Document decision-support exemption clearly |
| **Automated AIA completion** | AIA requires human judgment on impact levels | Provide AIA documentation template only |
| **Full GC HR Data Model implementation** | Model incomplete per proposal; incremental alignment | Mapping document + gap analysis only |
| **PAA for all departments** | 300+ departments; scope explosion | Target 3 departments (DND, DFO, Elections) |
| **O*NET full database import** | 900+ occupations, most not relevant to Canadian context | Import attributes for NOC-mapped occupations only |

**Rationale:** v4.0 is about completing the governed data foundation. Autonomous quality management belongs in v5.0's agent layer.

---

## Feature Dependencies

```
EXISTING JobForge v3.0 Features
        |
        v
+-------------------+
| Gold Parquet      |  <-- DQ metrics calculated from parquet files
| (28 tables)       |
+-------------------+
        |
        v
+-------------------+
| Catalog Metadata  |  <-- business_purpose, business_questions extend catalog
| (data/catalog/)   |
+-------------------+
        |
        +----------------------+
        |                      |
        v                      v
+-------------------+  +-------------------+
| DAMA/DADM Logs    |  | Lineage Graph     |
| (compliance/)     |  | (lineage/)        |
+-------------------+  +-------------------+
        |                      |
        +----------+-----------+
                   |
                   v
        +-------------------+
        | Policy Provenance |  <-- NEW: links lineage to TBS directives
        | (NEW)             |
        +-------------------+
                   |
                   v
        +-------------------+
        | GC DQMF Metrics   |  <-- NEW: 9-dimension scoring
        | (NEW API)         |
        +-------------------+
                   |
                   v
        +-------------------+
        | Quality Dashboard |  <-- NEW: extends demo UI
        | (demo/quality.html)|
        +-------------------+


O*NET INTEGRATION PATH
+-------------------+
| Existing          |
| NOC-SOC Crosswalk |  <-- 1,467 mappings already exist
| (data/reference)  |
+-------------------+
        |
        v
+-------------------+
| O*NET Database    |  <-- DOWNLOAD: from onetcenter.org
| (External)        |
+-------------------+
        |
        v
+-------------------+
| dim_onet_occupation|  <-- NEW: O*NET occupation dimension
| (gold)            |
+-------------------+
        |
        v
+-------------------+
| O*NET Attributes  |  <-- NEW: abilities, skills, work_activities, work_context
| (gold)            |
+-------------------+
        |
        v
+-------------------+
| bridge_noc_onet   |  <-- NEW: NOC-to-O*NET via SOC crosswalk
| (gold)            |
+-------------------+


PAA/DRF INTEGRATION PATH
+-------------------+
| Open Government   |  <-- SOURCE: open.canada.ca datasets
| Portal (DRF)      |
+-------------------+
        |
        v
+-------------------+
| dim_paa_program   |  <-- NEW: Program Alignment Architecture
| (gold)            |
+-------------------+
        |
        v
+-------------------+
| dim_drf_result    |  <-- NEW: Departmental Results Framework
| (gold)            |
+-------------------+
        |
        v
+-------------------+
| bridge_og_paa     |  <-- NEW: OG to PAA program mapping
| (gold)            |
+-------------------+
```

**Critical Path:**
1. Catalog schema must extend BEFORE business metadata capture
2. Quality metrics must calculate BEFORE dashboard displays
3. O*NET download must complete BEFORE attribute ingestion
4. Policy provenance requires lineage EXISTS (already done)

---

## GC DQMF: The 9 Quality Dimensions

Based on [Government of Canada Guidance on Data Quality](https://www.canada.ca/en/government/system/digital-government/digital-government-innovations/information-management/guidance-data-quality.html) and [GC Data Quality Framework wiki](https://wiki.gccollab.ca/index.php?title=GC_Data_Quality_Framework).

| Dimension | Definition | Measurement Approach | Complexity |
|-----------|------------|---------------------|------------|
| **Access** | How easy it is to discover, retrieve, process and use data | API availability, documentation completeness | Low |
| **Accuracy** | Degree to which data describes real-world phenomena | Validation rules, reference data comparison | Medium |
| **Coherence** | How easily a user can compare and link data from sources | FK integrity, standard codes adherence | Low |
| **Completeness** | Degree to which data values are sufficiently populated | NULL rate per column, required field coverage | Low |
| **Consistency** | Degree to which data is internally non-contradictory | Cross-table validation, duplicate detection | Medium |
| **Interpretability** | How much data can be understood in context | Description completeness, glossary linkage | Low |
| **Relevance** | How well data supports a specific goal/objective | Business purpose documentation, usage tracking | Low |
| **Reliability** | How well differences in data can be explained | Source attribution, transformation logging | Low |
| **Timeliness** | Time between reference period end and data availability | Refresh date tracking, lag calculation | Low |

**Implementation Priority:**
1. **Completeness** - Easiest to calculate (NULL counts)
2. **Timeliness** - Already have `updated_at` in catalog
3. **Coherence** - FK validation exists in ingestion
4. **Interpretability** - Extends catalog descriptions
5. **Accuracy** - Requires defining validation rules (more effort)

---

## O*NET Data Categories

Based on [O*NET Resource Center](https://www.onetcenter.org/database.html).

| Category | Tables | Purpose | JobForge Relevance |
|----------|--------|---------|-------------------|
| **Abilities** | Abilities.xlsx | Cognitive, psychomotor, physical, sensory | Extends OaSIS abilities coverage |
| **Skills** | Skills.xlsx | Basic (reading, math) + cross-functional (social, technical) | Extends OaSIS skills coverage |
| **Knowledge** | Knowledge.xlsx | Subject matter expertise areas | Extends OaSIS knowledge coverage |
| **Work Activities** | Work_Activities.xlsx | Generalized work activities taxonomy | NEW - not in current model |
| **Work Context** | Work_Context.xlsx | Working conditions, interaction requirements | Extends OaSIS work context |
| **Interests** | Interests.xlsx | RIASEC vocational interest profiles | NEW - career matching value |
| **Work Styles** | Work_Styles.xlsx | Personal characteristics for job success | NEW - person-job fit |
| **Tasks** | Tasks.xlsx | Occupation-specific task statements | NEW - job description generation |

**v4.0 Scope:** Abilities, Skills, Knowledge, Work Activities, Work Context (matches existing OaSIS pattern).
**Defer:** Interests, Work Styles, Tasks (v5.0 career matching agents).

---

## MVP Definition: v4.0 Launch

### Must Ship (Governance Foundation Complete)

| Feature | Deliverable | Success Criteria |
|---------|-------------|------------------|
| GC DQMF scoring | `/api/quality/table/{table_name}` endpoint | Returns 9-dimension scores |
| Completeness metric | NULL rate per column | Calculated for all 28+ tables |
| Timeliness metric | Days since last refresh | Calculated from catalog metadata |
| Quality dashboard | Demo UI `/quality` page | Displays table scores, trends |
| Business purpose capture | Extended catalog schema | All tables have purpose documented |
| Business questions capture | Extended catalog schema | At least 3 questions per core table |
| O*NET occupation dimension | `dim_onet_occupation` gold table | ~900 occupations loaded |
| O*NET attributes | 5 attribute tables in gold | Abilities, Skills, Knowledge, Work Activities, Work Context |
| NOC-O*NET bridge | `bridge_noc_onet` gold table | 516 NOC codes mapped via SOC |
| Policy provenance | Catalog field for policy references | Core tables link to TBS directives |
| DAMA audit enhancement | Metrics-based compliance scoring | Quantitative DAMA compliance % |
| GC HR Data Model mapping | Mapping document in `.planning/` | Gap analysis completed |

### Should Ship (Enhanced Governance)

| Feature | Deliverable | Notes |
|---------|-------------|-------|
| PAA/DRF for DND | `dim_paa_dnd`, `dim_drf_dnd` tables | First department target |
| Coherence metric | FK integrity scores | Leverage existing validation |
| Accuracy validation rules | Rule definitions in catalog | At least for NOC codes |
| Quality trend storage | Historical DQ scores | Enables degradation detection |
| Business metadata interview CLI | `jobforge metadata interview` | Guided stakeholder workflow |

### Defer to v5.0 (Agent-Powered Features)

| Feature | Reason |
|---------|--------|
| Natural language quality queries | Requires conversational agent |
| Automated quality remediation | Requires autonomous agent |
| Quality anomaly detection | ML-based, agent territory |
| DAMA audit automation in verify-work | Needs `/gsd:verify-work` integration |
| Full PAA/DRF for all departments | Scope management |

---

## Feature Prioritization Matrix

| Feature | Business Value | Technical Effort | Risk | Priority |
|---------|---------------|------------------|------|----------|
| GC DQMF scoring | HIGH | Medium | Low | P1 |
| O*NET integration | HIGH | High | Medium | P1 |
| Business metadata capture | HIGH | Low | Low | P1 |
| Quality dashboard | MEDIUM | Low | Low | P1 |
| Policy provenance | HIGH | Medium | Medium | P2 |
| PAA/DRF DND | MEDIUM | High | Medium | P2 |
| GC HR Data Model mapping | MEDIUM | Medium | Low | P2 |
| Quality trends | LOW | Medium | Low | P3 |
| Business metadata interview CLI | MEDIUM | Medium | Low | P3 |

**P1 = Phase 17-19** | **P2 = Phase 20-22** | **P3 = Phase 23 or defer**

---

## Complexity Assessment

| Feature Area | Complexity | Effort (days) | Risk | Notes |
|--------------|------------|---------------|------|-------|
| **Catalog schema extension** | Low | 1 | Low | Add `business_purpose`, `business_questions` fields |
| **GC DQMF scoring engine** | Medium | 3 | Low | 9-dimension calculation per table |
| **Quality API endpoints** | Low | 1 | Low | FastAPI patterns established |
| **Quality dashboard** | Medium | 2 | Low | Extends demo UI with charts |
| **O*NET database download** | Low | 0.5 | Low | Public download, no API needed |
| **O*NET ingestion pipeline** | Medium | 3 | Medium | Follow existing medallion pattern |
| **O*NET attribute tables** | Medium | 2 | Low | 5 tables, similar to OaSIS pattern |
| **NOC-O*NET bridge** | Medium | 2 | Low | Leverage existing SOC crosswalk |
| **Policy provenance tracking** | High | 4 | Medium | Paragraph-level citation mapping |
| **PAA/DRF scraping** | High | 3 | Medium | Open Government Portal API |
| **PAA/DRF ingestion** | Medium | 2 | Low | Standard medallion pipeline |
| **GC HR Data Model mapping** | Medium | 3 | Low | Documentation task |
| **Business metadata interview** | Medium | 2 | Low | CLI workflow |
| **DAMA audit enhancement** | Low | 1 | Low | Extend existing dama.json |

**Total estimated effort:** 29-32 developer-days for v4.0

---

## Sources

### GC Data Quality Framework
- [Guidance on Data Quality - Canada.ca](https://www.canada.ca/en/government/system/digital-government/digital-government-innovations/information-management/guidance-data-quality.html) - **Official 9-dimension framework**
- [GC Data Quality Framework - GCcollab Wiki](https://wiki.gccollab.ca/index.php?title=GC_Data_Quality_Framework) - Community documentation
- [Statistics Canada Quality Assurance Framework](https://www150.statcan.gc.ca/n1/en/catalogue/12-586-X) - Statistical quality standards

### DADM Compliance
- [Directive on Automated Decision-Making - TBS](https://www.tbs-sct.canada.ca/pol/doc-eng.aspx?id=32592) - **Official directive**
- [Algorithmic Impact Assessment tool - Canada.ca](https://www.canada.ca/en/government/system/digital-government/digital-government-innovations/responsible-use-ai/algorithmic-impact-assessment.html) - AIA tool and requirements
- [Guide on the Scope of the Directive](https://www.canada.ca/en/government/system/digital-government/digital-government-innovations/responsible-use-ai/guide-scope-directive-automated-decision-making.html) - Scope clarification

### DAMA DMBOK
- [DAMA DMBOK Framework Guide - Atlan](https://atlan.com/dama-dmbok-framework/) - Framework overview
- [DAMA International - DMBOK](https://dama.org/learning-resources/dama-data-management-body-of-knowledge-dmbok/) - Official DAMA source
- [Data Governance Framework 2026 - Atlan](https://atlan.com/data-governance-framework/) - Modern governance practices

### O*NET Integration
- [O*NET Database - Resource Center](https://www.onetcenter.org/database.html) - **Official database download**
- [O*NET-SOC Taxonomy](https://www.onetcenter.org/taxonomy.html) - Taxonomy structure
- [O*NET Crosswalk Files](https://www.onetcenter.org/crosswalks.html) - SOC-O*NET mappings

### PAA/DRF
- [Departmental Results Framework - Open Government Portal](https://open.canada.ca/data/en/dataset/320e0439-187a-4db5-b120-4079ed05ff99) - DRF dataset
- [National Defence PAA - Open Government Portal](https://open.canada.ca/data/en/dataset/1812c4ba-b74a-48c3-8be0-9fccbd0689cb) - DND PAA data
- [Departmental Results Reports - Canada.ca](https://www.canada.ca/en/treasury-board-secretariat/services/departmental-performance-reports.html) - DRR context

### Business Metadata
- [Data Catalog vs Metadata Management 2026 - OvalEdge](https://www.ovaledge.com/blog/data-catalog-vs-metadata-management) - Catalog patterns
- [Business Glossary for Data Governance - Select Star](https://www.selectstar.com/resources/business-glossary-data-governance) - Glossary best practices
- [Data Governance Best Practices 2026 - Alation](https://www.alation.com/blog/data-governance-best-practices/) - Governance framework

### Data Quality Dashboards
- [Six Types of Data Quality Dashboards - DataKitchen](https://datakitchen.io/the-six-types-of-data-quality-dashboards/) - Dashboard patterns
- [How to Make a Data Quality Dashboard - DQOps](https://dqops.com/how-to-make-a-data-quality-dashboard/) - Implementation guide
- [Data Quality Scorecard Guide - Datafold](https://www.datafold.com/blog/crafting-a-data-quality-scorecard) - Scorecard design

### Confidence Notes
- **HIGH:** GC DQMF dimensions (official Canada.ca source)
- **HIGH:** DADM/AIA requirements (TBS official directive)
- **HIGH:** O*NET database structure (official onetcenter.org)
- **MEDIUM:** Dashboard visualization patterns (industry best practices, multiple sources agree)
- **MEDIUM:** PAA/DRF data availability (Open Government Portal exists, structure varies by department)
- **LOW:** GC HR Data Model completeness (proposal notes model is incomplete)

---

*Last updated: 2026-02-05*
*Research mode: Features dimension for subsequent milestone*
