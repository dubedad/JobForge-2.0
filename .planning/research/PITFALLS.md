# Domain Pitfalls

**Domain:** Workforce intelligence platform with medallion architecture, Power BI semantic model, DADM compliance, and knowledge graph RAG
**Researched:** 2026-01-18
**Confidence:** HIGH (multiple authoritative sources cross-referenced)

---

## Critical Pitfalls

Mistakes that cause rewrites, compliance failures, or major architectural issues.

### Pitfall 1: Leaking Responsibilities Across Medallion Layers

**What goes wrong:** Teams ingest raw data directly into Gold, have Silver pipelines depend on unrefined Bronze data, or build business KPIs in Silver instead of Gold. This creates "semantic sprawl" where different teams define metrics differently with no single authoritative version.

**Why it happens:** Pressure to deliver quickly leads to shortcuts. Teams misunderstand layer purposes or interpret them differently without shared definitions.

**Consequences:**
- Multiple conflicting metric definitions (e.g., "active employee count" means different things)
- Breaking changes cascade unpredictably through layers
- Reprocessing requires rebuilding downstream tables
- Audit trail becomes unreliable

**Warning signs:**
- Business logic appearing in Silver transformations
- DAX measures duplicating logic already in Gold aggregations
- Different teams producing different numbers for "the same" metric
- Bronze tables being queried directly for reporting

**Prevention:**
- Document layer purposes explicitly in PROJECT.md before building
- Bronze = raw/immutable, Silver = validated/conformed, Gold = business-ready aggregates
- Enforce with naming conventions: `bronze_*`, `silver_*`, `gold_*`
- Code review should flag any business logic in Bronze/Silver transforms

**Phase mapping:** Address in Phase 1 (Foundation) with explicit layer contracts

**Sources:** [Weld Blog](https://weld.app/blog/medallion-layers), [InfoQ](https://www.infoq.com/articles/rethinking-medallion-architecture/), [DataKitchen](https://datakitchen.io/the-race-for-data-quality-in-a-medallion-architecture/)

---

### Pitfall 2: Deferring Data Quality Rules Until Gold

**What goes wrong:** Teams treat Bronze and Silver as pass-through layers, implementing all validation only at Gold. Invalid data propagates through the pipeline, creating expensive reprocessing when issues are finally caught.

**Why it happens:** Bronze is documented as "raw data" so teams interpret this as "no validation." Quality work feels like it belongs at the end.

**Consequences:**
- Invalid records propagate and multiply through transforms
- Late-stage failures require reprocessing entire pipeline
- Audit questions about data quality become hard to answer
- "Garbage in, garbage out" compounds at each layer

**Warning signs:**
- No schema validation at Bronze ingestion
- Silver layer has no null checks or quarantine tables
- Quality issues discovered only in Power BI visuals
- No count matching between layers

**Prevention:**
- Bronze: Minimal validation (schema conformance, required fields present)
- Silver: Core validation (null handling, type casting, referential integrity, quarantine invalid records)
- Gold: Business rule validation (range checks, metric consistency)
- Implement count matching between layers as automated checks
- Quarantine tables at Silver for invalid records (don't drop silently)

**Phase mapping:** Implement validation framework in Phase 1; refine rules incrementally

**Sources:** [Azure Databricks](https://learn.microsoft.com/en-us/azure/databricks/lakehouse/medallion), [DataKitchen](https://datakitchen.io/the-race-for-data-quality-in-a-medallion-architecture/)

---

### Pitfall 3: DADM Compliance as Afterthought

**What goes wrong:** Teams build the technical pipeline first, then attempt to bolt on DADM compliance tracking afterward. This results in incomplete audit trails, missing documentation, and inability to answer "where did this come from?"

**Why it happens:** Compliance feels like bureaucracy. Technical teams prioritize functionality over governance. DADM requirements are complex and easy to defer.

**Consequences:**
- Failed compliance audits
- Inability to demonstrate algorithmic fairness
- Missing Algorithmic Impact Assessment (AIA) documentation
- Rewrite required to add provenance tracking

**Warning signs:**
- No provenance fields in schema design
- Transforms don't preserve source attribution
- No documentation of decision logic
- DADM mentioned only in project docs, not in code

**Prevention:**
- Design provenance tracking into schema from day 1 (source_system, ingestion_timestamp, transform_version)
- Every transform must preserve or enhance lineage, never lose it
- Create DADM compliance scorecard template before building
- Map each data element to DADM requirements early
- Human-in-the-loop review points documented for automated decisions

**Phase mapping:** DADM schema design in Phase 1; compliance scoring in Phase 2

**Sources:** [Canada DADM Directive](https://www.tbs-sct.canada.ca/pol/doc-eng.aspx?id=32592), [Statistics Canada](https://www.statcan.gc.ca/en/data-science/network/automated-systems)

---

### Pitfall 4: NOC-to-ONET Mapping Without Imputation Strategy

**What goes wrong:** Teams treat O*NET data as directly usable with NOC codes, ignoring that they use different taxonomies (SOC vs NOC) and O*NET requires imputation/crosswalk logic.

**Why it happens:** Both are "occupation data" so they seem interchangeable. The crosswalk complexity is underestimated.

**Consequences:**
- Many-to-many mapping nightmares
- Missing data for NOC codes without clean SOC equivalents
- Inconsistent attribute coverage across occupations
- Audit questions about data derivation become unanswerable

**Warning signs:**
- Direct joins between NOC and O*NET tables
- Null explosion when querying O*NET attributes for NOC codes
- Different occupations showing identical O*NET profiles
- No documentation of crosswalk methodology

**Prevention:**
- Treat NOC as authoritative (source of truth for Canadian context)
- Treat O*NET as supplementary (informing, not authoritative)
- Build explicit crosswalk table with confidence scores
- Document imputation methodology before building
- Quarantine NOC codes without reliable O*NET mapping
- Consider O*NET imputation as separate milestone (already in out-of-scope)

**Phase mapping:** NOC pipeline in Phase 1; O*NET integration as separate later phase

**Sources:** [BLS Monthly Labor Review](https://www.bls.gov/opub/mlr/2021/article/mapping-employment-projections-and-onet-data.htm), [NCBI NOC Coding](https://pmc.ncbi.nlm.nih.gov/articles/PMC7439137/)

---

### Pitfall 5: Power BI Semantic Model Without Star Schema

**What goes wrong:** Teams replicate the medallion architecture structure directly into Power BI instead of transforming Gold into a proper star schema. This creates performance issues, incorrect calculations, and confused users.

**Why it happens:** Gold tables feel "ready" so teams import them directly. Star schema design is perceived as extra work.

**Consequences:**
- Snowflake complexity slows queries
- Incorrect totals from ambiguous relationships
- DAX measures become complex to compensate
- Report slowness drives users away

**Warning signs:**
- Multiple hops between dimension and fact tables
- Bi-directional relationships used to "fix" calculation issues
- Same dimension data in multiple tables
- DAX using CALCULATE with complex filter context

**Prevention:**
- Gold layer should already model toward star schema (fact tables, dimension tables)
- One calendar dimension, one NOC dimension, one Job Architecture dimension
- Fact tables grain clearly defined and documented
- Bi-directional relationships used sparingly (prefer single direction with DAX USERELATIONSHIP)
- Test with DAX Studio for performance before release

**Phase mapping:** Design star schema in Gold phase; validate before Power BI deployment

**Sources:** [Microsoft Learn](https://learn.microsoft.com/en-us/power-bi/connect-data/service-datasets-understand), [425 Consulting](https://www.425consulting.com/blog/blog-business-intelligence/top-5-power-bi-semantic-model-mistakes-to-avoid), [SQLBI](https://www.sqlbi.com/blog/marco/2024/04/06/direct-lake-vs-import-mode-in-power-bi/)

---

### Pitfall 6: Knowledge Graph RAG Without Evaluation Framework

**What goes wrong:** Teams build knowledge graph + RAG for conversational queries without systematic evaluation, leading to unreliable answers that erode trust. "72% of enterprise RAG implementations fail within their first year."

**Why it happens:** RAG demos are impressive. Teams ship before establishing accuracy baselines. Evaluation is hard and deferred.

**Consequences:**
- Answers that sound confident but are wrong
- Multi-hop reasoning failures (connecting NOC -> Skills -> Jobs requires chain reasoning)
- Stakeholders lose trust and build their own spreadsheets
- Compliance risk from unexplainable answers

**Warning signs:**
- No test dataset with expected answers
- "It works" based on a few manual checks
- Complex questions return plausible but wrong answers
- Users stop trusting the conversational interface

**Prevention:**
- Build evaluation dataset before building RAG (golden Q&A pairs)
- Test multi-hop reasoning explicitly: "Which skills are at risk of shortage and what job titles use them?"
- Measure retrieval precision (are the right chunks retrieved?)
- Require source citation in every answer
- Set accuracy threshold (e.g., 85% correct on test set) before release

**Phase mapping:** Evaluation framework in early RAG phase; do not ship without passing

**Sources:** [FreeCodeCamp](https://www.freecodecamp.org/news/how-to-solve-5-common-rag-failures-with-knowledge-graphs/), [CIO](https://www.cio.com/article/3808569/knowledge-graphs-the-missing-link-in-enterprise-ai.html), [Databricks](https://www.databricks.com/blog/building-improving-and-deploying-knowledge-graph-rag-systems-databricks)

---

## Moderate Pitfalls

Mistakes that cause delays, technical debt, or user frustration.

### Pitfall 7: Metadata Catalog as Static Wiki

**What goes wrong:** Business glossary and data dictionary are created as static documents (Word, Confluence) instead of automated catalog capabilities. They drift from reality immediately.

**Why it happens:** Documentation feels faster than tooling. Teams plan to "automate later."

**Consequences:**
- Business terms drift without accountability
- Data dictionary doesn't match actual schema
- Purview/Denodo exports require manual reconciliation
- Audit preparation becomes manual scramble

**Prevention:**
- Metadata lives in code (schema definitions, not documents)
- Business glossary terms stored in structured format (JSON/YAML) alongside table definitions
- Automated generation of data dictionary from schema
- CI/CD validates that glossary terms exist for all exposed columns
- Purview/Denodo export generated, never hand-edited

**Phase mapping:** Metadata schema design in Phase 1; export automation in Phase 2

**Sources:** [Alation](https://www.alation.com/blog/metadata-management-best-practices/), [Decube](https://www.decube.io/post/data-catalog-metadata-management-guide)

---

### Pitfall 8: Separate Semantic Model and Reports Not Enforced

**What goes wrong:** Reports embed their own data models instead of connecting to a shared semantic model. Each report becomes its own silo with its own version of "truth."

**Why it happens:** Faster to build quick .pbix with embedded data. Shared semantic model requires coordination.

**Consequences:**
- Multiple versions of metrics
- Refresh failures cascade unpredictably
- Cannot answer "where is this metric used?"
- Storage and refresh costs multiply

**Prevention:**
- Deploy semantic model as standalone artifact
- Reports connect to semantic model via Live Connection
- Block publishing reports with embedded data to shared workspaces
- Single refresh pipeline for semantic model; reports refresh automatically

**Phase mapping:** Enforce from first Power BI deployment

**Sources:** [Microsoft Learn](https://learn.microsoft.com/en-us/fabric/cicd/deployment-pipelines/understand-the-deployment-process), [Medium](https://medium.com/microsoft-power-bi/a-comprehensive-guide-to-modern-deployment-and-distribution-of-power-bi-solutions-34f6f69919f3)

---

### Pitfall 9: Lineage Tracking Without Cross-System Coverage

**What goes wrong:** Lineage is tracked within individual systems (dbt, Power BI) but not across the full pipeline. "Where did this number come from?" cannot be answered end-to-end.

**Why it happens:** Each tool has its own lineage capability. Stitching them together requires explicit design.

**Consequences:**
- Audit trail has gaps
- Root cause analysis stops at system boundaries
- Impact analysis misses upstream/downstream effects
- DADM compliance incomplete

**Prevention:**
- Design cross-system lineage from the start using common identifiers
- Every table/column has `source_system` and `transform_id` metadata
- Lineage documentation generates from metadata, not manual tracking
- Test lineage queries explicitly: "trace this Gold metric to its Bronze sources"

**Phase mapping:** Lineage schema in Phase 1; cross-system documentation in Phase 2

**Sources:** [Prophecy](https://www.prophecy.io/blog/data-lineage), [Acceldata](https://www.acceldata.io/blog/data-provenance)

---

### Pitfall 10: RLS (Row-Level Security) Implemented Too Late

**What goes wrong:** Row-level security is treated as a final polish step. When implemented, it requires significant DAX rework and reveals architectural issues.

**Why it happens:** "Let's get it working first, then add security." RLS feels like a Power BI-specific concern.

**Consequences:**
- Complex RLS rules that tank performance
- Rewiring relationships to support security filtering
- Users see wrong data during development (normalization risk)
- Hardcoded security logic scattered in measures

**Prevention:**
- Design RLS roles during semantic model design
- Test RLS with "View as" feature early and often
- Keep RLS rules simple (role-based, not row-based logic in DAX)
- Security requirements documented before build

**Phase mapping:** RLS design in Phase 1; implementation in first Power BI phase

**Sources:** [425 Consulting](https://www.425consulting.com/blog/blog-business-intelligence/top-5-power-bi-semantic-model-mistakes-to-avoid)

---

### Pitfall 11: DAMA DMBOK Full Implementation Upfront

**What goes wrong:** Teams attempt to implement all DAMA DMBOK knowledge areas simultaneously. Governance becomes overwhelming, adoption stalls, and teams revert to ungoverned practices.

**Why it happens:** DAMA DMBOK is comprehensive. Completeness feels like correctness. Framework adoption is conflated with framework mastery.

**Consequences:**
- Governance exists on paper but not in practice
- Teams route around governance as burden
- 80% of data governance initiatives fail (Gartner prediction)
- Continuous improvement never starts

**Prevention:**
- Start with 3-5 knowledge areas aligned to project goals
- For JobForge: Data Governance, Data Quality, Metadata Management, Data Modeling
- Add knowledge areas as maturity grows
- Treat DAMA as vocabulary and principles, not checklist

**Phase mapping:** Core knowledge areas in Phase 1; expand over milestones

**Sources:** [Atlan](https://atlan.com/dama-dmbok-framework/), [Alation](https://www.alation.com/blog/data-governance-challenges/)

---

## Minor Pitfalls

Mistakes that cause annoyance but are recoverable.

### Pitfall 12: High-Cardinality Columns in Semantic Model

**What goes wrong:** GUIDs, timestamps, or long text fields imported into Power BI, bloating model size and slowing queries.

**Prevention:**
- Use surrogate integer keys, not GUIDs
- Text descriptions in dimension tables only (not facts)
- Timestamps as DateKey integers, not datetime columns
- Profile column cardinality before import

**Phase mapping:** Schema review in Gold design phase

---

### Pitfall 13: Views Instead of Tables for Direct Lake

**What goes wrong:** If using Fabric Direct Lake, views cause fallback to DirectQuery, losing performance benefits.

**Prevention:**
- Materialize views as tables for Direct Lake sources
- Test query performance, not just correctness

**Phase mapping:** Only relevant if/when Fabric adopted (future)

---

### Pitfall 14: Expecting Real-Time from Gold Layer

**What goes wrong:** Business users expect Gold to reflect changes immediately. Gold is designed for batch-refresh aggregates.

**Prevention:**
- Set expectations: Gold refreshes on schedule (daily, hourly)
- If real-time needed, design separate hot path (not Gold)
- Document refresh schedule prominently

**Phase mapping:** Communicate in user documentation

---

### Pitfall 15: DAX Calculations Done in Power Query

**What goes wrong:** Business logic implemented in Power Query (M) instead of DAX. This limits flexibility and hurts performance for complex calculations.

**Prevention:**
- Power Query for data shaping (joins, filters, type conversions)
- DAX for business logic (calculations, KPIs, measures)
- Review any Power Query custom columns for business logic leakage

**Phase mapping:** Code review standard from first semantic model

---

## Phase-Specific Warnings

| Phase Topic | Likely Pitfall | Mitigation |
|-------------|---------------|------------|
| Medallion pipeline setup | Layer responsibility leakage | Document layer contracts before building |
| Bronze ingestion | No schema validation | Implement minimal validation (schema, required fields) |
| Silver transforms | Skipping quarantine tables | Invalid records go to quarantine, not dropped |
| Gold aggregates | Business logic not in Gold | All KPI definitions live in Gold or DAX |
| NOC dimension | Treating as simple lookup | Model NOC hierarchy properly (4-digit to 1-digit) |
| O*NET integration | Direct join without crosswalk | Explicit crosswalk table with confidence scores |
| Power BI deployment | Embedded data in reports | Enforce Live Connection to shared semantic model |
| Metadata/glossary | Static documentation | Metadata in code, documentation generated |
| DADM compliance | Compliance as afterthought | Provenance schema from day 1 |
| Knowledge graph RAG | No evaluation framework | Golden Q&A dataset before shipping |
| Lineage tracking | Per-system only | Cross-system identifiers in schema |
| RLS security | Late implementation | Design roles during semantic model design |

---

## Government of Canada Specific Warnings

### DADM Transition Period

The DADM directive has been updated with new requirements effective June 24, 2025. Systems developed before this date have until June 24, 2026 to comply. JobForge should target current requirements, not archived versions.

**Prevention:** Use current directive (not archived 2021/2023 versions), monitor TBS announcements.

### AIA Timing and Publication

The directive doesn't specify timing for Algorithmic Impact Assessment release. This creates ambiguity.

**Prevention:** Establish internal AIA publication policy; document decision rationale.

### Privacy and Organizational Data

Departmental position data and employee data are explicitly out of scope due to privacy constraints. This is correct, but be cautious about:
- Semantic matching that could inadvertently reveal organizational structure
- Aggregate queries that could identify individuals
- Job architecture that ties too closely to specific positions

**Prevention:** Privacy impact assessment before any org data integration; aggregation thresholds.

---

## Sources Summary

**Medallion Architecture:**
- [Azure Databricks Medallion](https://learn.microsoft.com/en-us/azure/databricks/lakehouse/medallion)
- [InfoQ Rethinking Medallion](https://www.infoq.com/articles/rethinking-medallion-architecture/)
- [DataKitchen Data Quality](https://datakitchen.io/the-race-for-data-quality-in-a-medallion-architecture/)

**Power BI Semantic Models:**
- [Microsoft Learn Semantic Models](https://learn.microsoft.com/en-us/power-bi/connect-data/service-datasets-understand)
- [425 Consulting Top 5 Mistakes](https://www.425consulting.com/blog/blog-business-intelligence/top-5-power-bi-semantic-model-mistakes-to-avoid)
- [Microsoft Deployment Pipelines](https://learn.microsoft.com/en-us/fabric/cicd/deployment-pipelines/understand-the-deployment-process)

**DADM Compliance:**
- [Canada DADM Directive](https://www.tbs-sct.canada.ca/pol/doc-eng.aspx?id=32592)
- [Statistics Canada Responsible AI](https://www.statcan.gc.ca/en/data-science/network/automated-systems)
- [DADM 3rd Review](https://wiki.gccollab.ca/images/f/f4/DADM_3rd_Review_-_Phase_2_Consultation_Deck_(EN).pdf)

**Knowledge Graph / RAG:**
- [FreeCodeCamp RAG Failures](https://www.freecodecamp.org/news/how-to-solve-5-common-rag-failures-with-knowledge-graphs/)
- [Databricks GraphRAG](https://www.databricks.com/blog/building-improving-and-deploying-knowledge-graph-rag-systems-databricks)

**Data Governance:**
- [Atlan DAMA DMBOK](https://atlan.com/dama-dmbok-framework/)
- [Alation Data Governance Challenges](https://www.alation.com/blog/data-governance-challenges/)

**Occupation Taxonomies:**
- [BLS O*NET Mapping](https://www.bls.gov/opub/mlr/2021/article/mapping-employment-projections-and-onet-data.htm)
- [NCBI NOC Coding](https://pmc.ncbi.nlm.nih.gov/articles/PMC7439137/)
