# Domain Pitfalls: v4.0 Governed Data Foundation

**Domain:** Data governance compliance, quality dashboards, taxonomy expansion
**Researched:** 2026-02-05
**Context:** Adding governance and data quality features to existing JobForge 2.0 platform

---

## Critical Pitfalls

Mistakes that cause rewrites or major issues when adding governance features to an existing system.

### Pitfall 1: Governance Audit as Approval Gate

**What goes wrong:** DAMA DMBOK audit integration becomes a bottleneck that slows development velocity to a crawl. Teams interpret "audit integration" as requiring formal approval before each phase can proceed.

**Why it happens:**
- Governance frameworks are designed for enterprise-scale compliance, not developer-friendly workflows
- DAMA DMBOK defines principles without prescribing tools or methodologies
- Organizational interpretation defaults to "more process = more governance"

**Consequences:**
- Development velocity drops by 60-80%
- Engineers avoid making changes to avoid triggering audits
- Compliance becomes theater (check-the-box) rather than substantive
- Audit logs grow stale because nobody regenerates them

**Warning signs:**
- `/gsd:verify-work` takes longer than the implementation work
- Teams skip audit regeneration "to save time"
- DAMA compliance sections in SUMMARY.md become copy-paste boilerplate

**Prevention strategy:**
1. Audit is **informational**, not **blocking** - generate compliance logs but don't require manual approval
2. Automate regeneration: `jobforge compliance regenerate` runs in CI/CD, not manually
3. Focus on **delta audits** - only audit what changed, not the entire system
4. Set explicit scope: audit covers data layer artifacts, not code style or test coverage

**Detection checkpoint:**
- After Phase 17 (Governance Compliance Framework), verify that audit generation completes in under 30 seconds
- If `/gsd:verify-work` adds more than 5 minutes to phase completion, scope is too broad

**Phase mapping:** Phase 17 (Governance Compliance Framework)

---

### Pitfall 2: Data Quality Metrics Without Actionability

**What goes wrong:** Dashboard shows 47 quality metrics across 6 dimensions (accuracy, completeness, consistency, timeliness, validity, uniqueness), but nobody knows what to do when metrics degrade. Dashboard becomes background noise.

**Why it happens:**
- GC DQMF dimensions are conceptually complete but operationally vague
- "Completeness" could mean filling every field or only critical fields
- Metrics without thresholds or owners are just numbers
- Dashboards designed for executives, not operators

**Consequences:**
- Quality issues are detected but not fixed
- Dashboard exists but drives no action
- Over 70% of enterprises report their lineage is incomplete or outdated (industry pattern)
- Teams view quality metrics as overhead rather than enablement

**Warning signs:**
- No owner assigned to any metric
- All metrics show "green" but users report data issues
- Dashboard accessed weekly but no follow-up tickets created
- Metrics lack temporal context (no trending, no alerts)

**Prevention strategy:**
1. **6 metrics, not 60** - Start with 6 actionable metrics, one per DQMF dimension
2. **Owner per metric** - Each metric has a responsible person/team
3. **Thresholds with consequences** - Green/yellow/red with explicit "yellow means X action"
4. **Link to source** - Every metric links to the table/column it measures
5. **Trend, don't snapshot** - Show 7-day trend, not just current value

**Metrics that matter (per Monte Carlo Data research):**
| Metric | What it measures | Action when degraded |
|--------|------------------|---------------------|
| Freshness | Time since last update | Investigate pipeline failures |
| Volume | Row count delta vs expected | Check source system availability |
| Schema | Column changes detected | Review migration scripts |
| Distribution | Value histograms changed | Validate business rule changes |
| Null rate | % null by column | Investigate upstream data gaps |
| Duplicate rate | PK/NK uniqueness | Check deduplication logic |

**Detection checkpoint:**
- After Phase 18, each metric should have: owner, threshold, action, and source link
- If dashboard shows "all green" on day 1, thresholds are wrong

**Phase mapping:** Phase 18 (Data Quality Dashboard)

---

### Pitfall 3: Policy Provenance at Wrong Granularity

**What goes wrong:** Attempt to trace every field to its policy source creates a documentation maintenance nightmare. Policy documents change, but provenance links don't get updated.

**Why it happens:**
- "Paragraph-level provenance indexing" sounds impressive but requires constant maintenance
- TBS directives get amended (DADM was last amended 2023-10-01)
- Classification policies reference other documents that reference other documents
- Over 80% of organizations don't even publish basic provenance metadata (industry pattern)

**Consequences:**
- Initial mapping takes weeks; becomes outdated within months
- Broken links to moved/renamed policy documents
- "Where did this come from?" answers with dead URLs
- Audit confidence drops because provenance can't be verified

**Warning signs:**
- Provenance links return 404s during verification
- Same policy clause referenced by 50+ fields (copy-paste without understanding)
- No process for updating provenance when policies change
- Provenance added to catalog but never queried

**Prevention strategy:**
1. **Document-level, not paragraph-level** - Link to the policy document, not specific clause
2. **Canonical URL patterns** - Use canada.ca permanent URLs, not session-based links
3. **Policy version tracking** - Record policy version date alongside link
4. **Provenance verification job** - Weekly automated check that linked documents still exist
5. **Start with relationships, not fields** - WiQ has 27 relationships; map those 27 to policy first

**Provenance hierarchy (from high to low value):**
| Level | Example | Maintenance burden |
|-------|---------|-------------------|
| Table-level | "dim_og sourced from TBS Qualification Standards" | Low |
| Relationship-level | "bridge_noc_og concordance per Classification Policy" | Low |
| Column-level | "og_code follows TBS occupational group taxonomy" | Medium |
| Value-level | "AS classification level per PA collective agreement" | High (avoid) |

**Detection checkpoint:**
- Provenance verification pass rate should be >95% at all times
- If >10% of provenance links break within 3 months, granularity is wrong

**Phase mapping:** Phase 17 (Governance Compliance Framework)

---

### Pitfall 4: O*NET API Integration Without Caching Strategy

**What goes wrong:** O*NET API rate limits hit during batch processing, causing incomplete data loads or 429 errors cascading through the pipeline.

**Why it happens:**
- O*NET Web Services throttles "more than a certain threshold" (exact limits undisclosed)
- JobForge processes 516 NOC codes, each potentially mapping to multiple SOC codes
- Existing O*NET client has retry logic but no persistent caching
- "Best-effort" service with no SLA for high-volume users

**Consequences:**
- Partial O*NET data in gold tables (some occupations have attributes, others don't)
- Pipeline failures during re-runs when cache is cold
- Unpredictable processing times (5 minutes vs 2 hours depending on rate limiting)
- Attribution requirements violated if O*NET data displayed without proper credit

**Warning signs:**
- `ONetRateLimitError` in logs during pipeline runs
- O*NET attribute coverage varies between runs
- Pipeline duration highly variable (>50% variance)
- Customer service asks about high request volumes

**Prevention strategy:**
1. **Local database cache** - Download O*NET database (available from onetcenter.org) as local fallback
2. **Request batching** - Group SOC codes, fetch in batches with delays
3. **Persistent cache** - Store API responses in `data/onet/` with TTL (30-90 days)
4. **Stale-while-revalidate** - Use cached data immediately, update in background
5. **Attribution compliance** - Display required link per Terms of Service

**O*NET integration architecture:**
```
Pipeline Request
       |
       v
  [Local Cache?] -- Yes --> Return cached data
       |
      No
       v
  [Database File?] -- Yes --> Query local DB
       |
      No
       v
  [API Request] --> Store in cache --> Return data
```

**Key Terms of Service requirements:**
- Must display "O*NET Web Services" attribution with link
- Can only use on registered sites/applications
- High-volume users should use downloadable database

**Detection checkpoint:**
- O*NET API calls per pipeline run should be <100 (cached)
- After initial cache population, pipeline should work fully offline

**Phase mapping:** Phase 20 (O*NET Integration)

---

### Pitfall 5: PAA/DRF Data Consistency Across Departments

**What goes wrong:** PAA data structure varies significantly between departments. What works for DND doesn't work for Fisheries and Oceans or Elections Canada.

**Why it happens:**
- PAA was replaced by DRF but not all departments have migrated
- Each department interprets PAA/DRF differently
- GC does not operate as a single employer (200+ distinct organizations)
- 70 different HR Management Systems across government, each non-standardized

**Consequences:**
- Schema designed for DND PAA breaks on Fisheries PAA
- Inconsistent granularity (some departments have 5 levels, others have 3)
- Bridge tables can't be built because keys don't align
- "Works for one department" ≠ "Works for government"

**Warning signs:**
- First department works; second department requires schema changes
- Bridge tables have NULL foreign keys for certain departments
- "Organizational Context" field means different things per department
- DRF outcomes don't map to PAA programs

**Prevention strategy:**
1. **One department at a time** - Build, validate, then generalize
2. **Schema flexibility** - Design for varying granularity (nullable hierarchy levels)
3. **Department-specific adapters** - Don't force one schema; transform at ingestion
4. **Explicit mapping tables** - Document what each department calls each concept
5. **Accept incompleteness** - Some departments won't have certain data; that's okay

**Schema pattern for departmental variance:**
```json
{
  "dept_code": "DND",
  "paa_level_1": "Core Responsibility",
  "paa_level_2": "Program",
  "paa_level_3": "Sub-program",
  "paa_level_4": null,  // DND doesn't use L4
  "drf_core_responsibility": "...",
  "drf_result": "...",
  "drf_indicator": "..."
}
```

**Detection checkpoint:**
- After first department (DND), schema should accommodate 3-5 hierarchy levels
- Second department should require <20% schema changes

**Phase mapping:** Phase 22 (PAA/DRF Data Layer)

---

### Pitfall 6: GC HR Data Model Completeness Assumptions

**What goes wrong:** Planning assumes GC HR Data Model is complete and authoritative, but it's incomplete. Phase scope creep as team tries to "complete" the model.

**Why it happens:**
- Model status is explicitly "available but incomplete"
- 70 different HRMS across government means no single source of truth
- Office of OCHRO is "building out" the model (in progress, not complete)
- Seven new mandatory measures introduced recently (requirements still settling)

**Consequences:**
- Gap analysis reveals more gaps than mappings
- Phase 23 scope balloons as team tries to fill gaps
- JobForge forced to make design decisions that may conflict with future model updates
- Alignment recommendations immediately obsolete when model updates

**Warning signs:**
- Gap analysis document > mapping document
- "Proposed mappings" outnumber "confirmed mappings"
- Phase 23 delivery date slips repeatedly
- Stakeholder requests to "just map to what exists"

**Prevention strategy:**
1. **Gap analysis, not gap filling** - Document gaps; don't try to fix the model
2. **Versioned alignment** - "Aligned with GC HR Data Model v1.2 as of 2026-02-05"
3. **Provisional mappings** - Mark uncertain mappings as provisional, subject to model updates
4. **Bidirectional gap report** - Both "JobForge has, model lacks" AND "model has, JobForge lacks"
5. **Recommendation scope** - Recommendations for JobForge, not recommendations for fixing the model

**Alignment output format:**
| JobForge Entity | GC HR DM Entity | Alignment Status | Notes |
|-----------------|-----------------|------------------|-------|
| dim_noc | OccupationClassification | Confirmed | Direct mapping via NOC code |
| dim_og | TBSOccupationalGroup | Confirmed | Uses OG code |
| dim_caf_occupation | MilitaryOccupation | Provisional | GC HR DM entity may not exist yet |
| job_architecture | N/A | Gap | JA is JobForge-specific |

**Detection checkpoint:**
- Phase 23 should produce a document, not a code change
- If alignment requires >10% schema changes, model isn't ready

**Phase mapping:** Phase 23 (GC HR Data Model Alignment)

---

### Pitfall 7: Business Metadata Capture Workflow Friction

**What goes wrong:** Interview workflow for capturing business purpose and business questions creates stakeholder fatigue. Initial enthusiasm fades after first 10 tables.

**Why it happens:**
- Stakeholders have day jobs; metadata capture is overhead
- 28 tables (and growing) is a lot of interviews
- "What business questions can this table answer?" requires domain expertise
- Lack of measurable progress erodes buy-in over time

**Consequences:**
- First 10 tables have rich metadata; remaining 18 have placeholder text
- Metadata capture backlog grows faster than it's cleared
- Stakeholders view governance as "extra work without visible benefit"
- Business metadata becomes another field to ignore

**Warning signs:**
- Interview completion rate drops after first week
- "Same as X" appears frequently in business purpose fields
- Stakeholders delegate to people without domain expertise
- business_questions array is empty for most tables

**Prevention strategy:**
1. **Prioritize by usage** - Start with most-queried tables (dim_noc, cops_employment)
2. **Templates, not blank fields** - Provide example purposes and questions
3. **Batch interviews** - Group related tables (all COPS tables in one session)
4. **Visible value** - Show metadata in demo UI immediately after capture
5. **Asynchronous option** - Allow async form submission, not just live interviews
6. **Minimum viable metadata** - 1 purpose sentence + 3 questions is enough to start

**Interview prioritization matrix:**
| Priority | Tables | Rationale |
|----------|--------|-----------|
| P1 | dim_noc, cops_employment, cops_employment_growth | Core tables, highest query frequency |
| P2 | dim_og, bridge_noc_og, dim_og_subgroup | New in v3.0, stakeholder interest high |
| P3 | oasis_* tables | Attribute tables, similar purposes |
| P4 | dim_caf_*, bridge_caf_* | Specialized audience |

**Detection checkpoint:**
- 8 of 28 tables should have complete metadata within first sprint
- If completion rate <50% after 2 sprints, workflow has too much friction

**Phase mapping:** Phase 19 (Business Metadata Capture)

---

## Technical Debt Patterns

Mistakes that cause delays or technical debt when retrofitting governance.

### Pattern 1: Compliance Log Staleness

**What goes wrong:** Compliance logs (DADM, DAMA, Classification) generated once, never regenerated.

**Prevention:**
- Add `jobforge compliance check --diff` to CI/CD
- Alert when compliance logs older than 7 days
- Include compliance log age in demo UI status

**Phase:** 17

### Pattern 2: Quality Metric Silos

**What goes wrong:** Quality metrics computed separately from catalog metadata, creating two sources of truth.

**Prevention:**
- Quality metrics stored in same catalog JSON as table metadata
- Single `data/catalog/tables/{table}.json` contains both
- Dashboard reads from catalog, not separate quality database

**Phase:** 18

### Pattern 3: O*NET Data Drift

**What goes wrong:** Local O*NET cache diverges from API as O*NET updates their database (semi-annual releases).

**Prevention:**
- Track O*NET database version in cache metadata
- Log warning when cached version >6 months old
- Provide `jobforge onet refresh --force` for manual updates

**Phase:** 20

### Pattern 4: Orphaned Provenance

**What goes wrong:** Provenance links to tables/columns that no longer exist after schema changes.

**Prevention:**
- Provenance validation in `jobforge catalog validate`
- Provenance links use table/column names, not UUIDs
- Schema migration includes provenance migration

**Phase:** 17

---

## Integration Gotchas

Specific issues when integrating v4.0 features with existing JobForge 2.0.

### Gotcha 1: Existing O*NET Client Expectations

**Current state:** `src/jobforge/external/onet/client.py` has `ONetClient` with retry logic for 429s.

**Problem:** v4.0 O*NET integration assumes different architecture (local database + API fallback).

**Resolution:**
- Extend, don't replace: `ONetClient` becomes API-only client
- New `ONetDataSource` wraps client + local DB + cache
- Existing crosswalk code continues to work

### Gotcha 2: Compliance Log Format Compatibility

**Current state:** `data/catalog/compliance/dama.json` uses ComplianceLog model with TraceabilityEntry.

**Problem:** v4.0 DAMA audit may want phase-level compliance, not just artifact-level.

**Resolution:**
- Add optional `phase_id` field to TraceabilityEntry
- Existing logs remain valid (field is optional)
- New audit workflow adds phase context

### Gotcha 3: Catalog Enrichment Collision

**Current state:** `src/jobforge/catalog/enrich.py` adds workforce_dynamic, descriptions to catalog.

**Problem:** v4.0 business metadata capture adds more fields to same JSON files.

**Resolution:**
- Define clear field ownership (enrich.py owns technical metadata)
- Business metadata in separate `business_metadata` object within same file
- Merge strategy: business metadata never overwritten by technical enrichment

### Gotcha 4: WiQ Schema Registration Growth

**Current state:** 28 tables, 27 relationships in `wiq_schema.json`.

**Problem:** v4.0 adds O*NET tables, PAA/DRF tables - potential for 40+ tables.

**Resolution:**
- Schema generator handles arbitrary table count
- Consider schema namespacing: `core.dim_noc`, `onet.dim_soc`, `paa.fact_outcomes`
- Performance test DDL generation at 50 tables

---

## "Looks Done But Isn't" Checklist

Tests that verify features are actually complete, not just present.

### Phase 17: Governance Compliance Framework

- [ ] DAMA audit generates in <30 seconds
- [ ] Audit can run without manual approval
- [ ] Policy provenance links resolve (HTTP 200)
- [ ] Delta audit works (only changed artifacts)
- [ ] Compliance check integrates with CI/CD

### Phase 18: Data Quality Dashboard

- [ ] Each metric has an owner
- [ ] Each metric has a threshold
- [ ] Yellow status triggers defined action
- [ ] Metrics trend over 7 days (not just snapshot)
- [ ] Dashboard loads in <3 seconds

### Phase 19: Business Metadata Capture

- [ ] Interview can be completed async (form, not just live)
- [ ] Templates provided for common table types
- [ ] Captured metadata visible in demo UI
- [ ] Completion tracked (X of Y tables documented)
- [ ] Business questions searchable in query interface

### Phase 20: O*NET Integration

- [ ] Pipeline works fully offline (cached data)
- [ ] O*NET database version tracked
- [ ] Attribution link displayed per Terms of Service
- [ ] Rate limit errors don't fail entire pipeline
- [ ] SOC code coverage matches NOC code count

### Phase 21: Job Architecture Enrichment

- [ ] All job functions have descriptions
- [ ] All job families have descriptions
- [ ] Metadata completeness >90%
- [ ] Enrichment follows Phase 12 pattern
- [ ] No orphaned JA records

### Phase 22: PAA/DRF Data Layer

- [ ] Schema handles 3-5 hierarchy levels
- [ ] DND data fully integrated
- [ ] Second department requires <20% schema change
- [ ] Bridge tables have valid FKs
- [ ] Provenance to Open Government Portal

### Phase 23: GC HR Data Model Alignment

- [ ] Gap analysis document complete
- [ ] Bidirectional gaps documented
- [ ] Provisional mappings clearly marked
- [ ] No code changes required for alignment
- [ ] Version date recorded

---

## Pitfall-to-Phase Mapping

| Pitfall | Phase(s) | Severity | Prevention Complexity |
|---------|----------|----------|----------------------|
| Governance Audit as Approval Gate | 17 | Critical | Medium |
| Data Quality Metrics Without Actionability | 18 | Critical | Medium |
| Policy Provenance at Wrong Granularity | 17 | Critical | High |
| O*NET API Integration Without Caching | 20 | Critical | Medium |
| PAA/DRF Data Consistency Across Departments | 22 | Critical | High |
| GC HR Data Model Completeness Assumptions | 23 | Critical | Low |
| Business Metadata Capture Workflow Friction | 19 | Critical | Medium |
| Compliance Log Staleness | 17, All | Moderate | Low |
| Quality Metric Silos | 18 | Moderate | Low |
| O*NET Data Drift | 20 | Moderate | Low |
| Orphaned Provenance | 17, All | Moderate | Medium |

---

## Sources

### Official Documentation (HIGH confidence)

- [DAMA DMBOK Framework Guide](https://atlan.com/dama-dmbok-framework/) - Framework overview and implementation guidance
- [DAMA DMBOK 2.0 Revisions](https://www.damadmbok.org/dmbok2-revisions) - DMBOK 3.0 evergreening initiative (2025)
- [O*NET Web Services](https://services.onetcenter.org/) - API documentation and Terms of Service
- [O*NET Web Services Reference Manual](https://services.onetcenter.org/reference/) - API v2.0 reference
- [Directive on Automated Decision-Making](https://www.tbs-sct.canada.ca/pol/doc-eng.aspx?id=32592) - DADM compliance requirements
- [Algorithmic Impact Assessment tool](https://www.canada.ca/en/government/system/digital-government/digital-government-innovations/responsible-use-ai/algorithmic-impact-assessment.html) - AIA requirements and timeline
- [2023-2026 Data Strategy for the Federal Public Service](https://www.canada.ca/en/treasury-board-secretariat/corporate/reports/2023-2026-data-strategy.html) - GC data governance priorities
- [GC HR and Pay Data Standards](https://open.canada.ca/data/en/dataset/67c81048-e230-47f2-ad9a-38bc68f3b51e) - HR data standardization efforts
- [Next Generation HR and Pay Final Findings Report](https://www.canada.ca/en/shared-services/corporate/about-us/transparency/publications/2023-24/next-generation-hr-pay-final-findings-report.html) - 70 HRMS complexity documented

### Industry Research (MEDIUM confidence)

- [Data Quality Dashboard Guide](https://datakitchen.io/the-six-types-of-data-quality-dashboards/) - Six dashboard types, design patterns
- [Data Quality Metrics That Matter](https://www.montecarlodata.com/blog-data-quality-metrics/) - Actionable metrics guidance
- [Data Quality Issues 2025](https://atlan.com/data-quality-issues/) - Common quality issues and solutions
- [Data Governance Challenges](https://www.alation.com/blog/data-governance-challenges/) - Retrofit challenges and solutions
- [Data Provenance and Lineage](https://www.nightfall.ai/ai-security-101/data-provenance-and-lineage) - Implementation challenges
- [Metadata Management Best Practices](https://www.alation.com/blog/metadata-management-framework/) - Stakeholder engagement patterns
- [IBM Data Quality Issues](https://www.ibm.com/think/insights/data-quality-issues) - Enterprise data quality challenges
- [Data Governance Audit Checklist 2025](https://lumenalta.com/insights/data-governance-audit-checklist-updated-2025) - Audit automation guidance

### Project Context (HIGH confidence)

- Existing O*NET client: `src/jobforge/external/onet/client.py`
- Existing compliance logs: `src/jobforge/governance/compliance/`
- Existing catalog structure: `data/catalog/tables/*.json`
- v4.0 proposal: `.planning/proposals/v4.0-governance-agents-vision.md`

---

**Confidence Assessment:**

| Area | Confidence | Reasoning |
|------|------------|-----------|
| DAMA/Governance Pitfalls | MEDIUM | Framework guidance is general; project-specific impact requires validation |
| Data Quality Dashboard | HIGH | Industry patterns well-documented; Monte Carlo and DataKitchen research comprehensive |
| O*NET Integration | HIGH | Existing client code + official documentation reviewed |
| PAA/DRF Challenges | MEDIUM | GC-specific; limited public documentation on departmental variance |
| GC HR Data Model | MEDIUM | Model explicitly incomplete; alignment complexity depends on model state |
| Business Metadata | MEDIUM | Industry patterns apply; stakeholder-specific friction hard to predict |

---

*Researched: 2026-02-05*
*Valid for: v4.0 milestone planning*
