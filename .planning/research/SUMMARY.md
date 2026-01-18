# Project Research Summary

**Project:** JobForge 2.0 - Workforce Intelligence Platform
**Domain:** Workforce Intelligence / Occupational Data Governance for Government of Canada
**Researched:** 2026-01-18
**Confidence:** HIGH

## Executive Summary

JobForge 2.0 is a workforce intelligence platform combining three mature architecture patterns: medallion data pipeline (bronze/silver/gold), hub-and-spoke dimensional modeling for Power BI semantic models, and hybrid GraphRAG for conversational queries. The platform's core mission is occupational data governance with NOC (National Occupational Classification) as the authoritative Canadian source, supplemented by O*NET for richer skill/task descriptors, deployed via Power BI semantic models with conversational RAG capabilities.

The recommended approach builds from foundation up: establish the medallion pipeline first (Polars + DuckDB + Parquet), then the WiQ dimensional model with DIM_NOC as the hub, followed by Power BI deployment via semantic-link-labs, and finally the knowledge graph and RAG layer (LlamaIndex + Qdrant). This order respects dependencies - each layer feeds the next - and aligns with the research consensus that data governance foundations must be solid before building consumption interfaces.

Key risks center on three areas: (1) layer responsibility leakage in the medallion architecture causing "semantic sprawl" where metrics diverge, (2) DADM (Directive on Automated Decision-Making) compliance treated as afterthought rather than designed into schemas from day one, and (3) RAG deployment without evaluation frameworks leading to confident-but-wrong answers. Mitigation requires explicit layer contracts documented before building, provenance tracking in every schema, and golden Q&A test datasets before any RAG features ship.

## Key Findings

### Recommended Stack

The stack is optimized for Microsoft Fabric ecosystem, modern Python data processing, and production-ready RAG. All core libraries are verified via PyPI and official documentation.

**Core technologies:**
- **Polars 1.37.1**: DataFrame operations, ETL transformations - 3-10x faster than Pandas, native Parquet support, lazy evaluation
- **DuckDB 1.4.3**: SQL analytics on Parquet, medallion layer queries - in-process OLAP, projection/filter pushdown, zero-copy Arrow integration
- **semantic-link-labs 0.12.9**: Power BI semantic model deployment - Microsoft's official library for programmatic deployment, Direct Lake support
- **RDFLib 7.5.0**: Knowledge graph operations - built-in SKOS namespace support for NOC/O*NET vocabulary indexing
- **LlamaIndex 0.14.12**: RAG orchestration - superior retrieval accuracy, designed for document-heavy applications
- **Qdrant 1.16.2**: Production vector database - Rust-based, HNSW with metadata filtering, ready for GC production workloads
- **OpenLineage 1.42.1**: Data governance lineage - open standard adopted by Airflow/dbt/Spark

**Critical constraint:** Python 3.11 required (semantic-link-labs does not support Python 3.12+).

### Expected Features

**Must have (table stakes):**
- NOC ingestion and parsing (516 unit groups, hierarchical structure)
- O*NET/SOC integration for skill/task descriptors
- NOC-SOC crosswalk mapping with confidence scores
- Power BI semantic model deployment (Direct Lake to Gold layer)
- Measure definitions with DAX (headcount, FTE, vacancy rates)
- Row-Level Security for department-level access control
- Data dictionary generation from model metadata
- Business glossary for workforce domain terms
- Data lineage tracking (source-to-report traceability)

**Should have (competitive):**
- Natural language query interface ("Show me IT occupations requiring Python")
- Occupation similarity scoring via embeddings
- Auto-generated glossary terms from metadata
- Lineage visualization (interactive data flow diagrams)

**Defer (v2+):**
- Skills ontology (taxonomy sufficient for MVP)
- Job description generation (manager persona is later phase)
- Skills gap analysis (requires organizational data not in initial scope)
- Emerging skills detection (NLP on job postings)
- Real-time job posting ingestion (Job Bank already does this)

### Architecture Approach

The architecture is a six-layer system where each layer feeds the next: medallion pipeline produces staged/bronze/silver/gold Parquet files; gold feeds the WiQ semantic model with hub-and-spoke dimensional design; WiQ feeds both Power BI (via Direct Lake) and the knowledge graph; the knowledge graph powers hybrid RAG retrieval; and artifact export generates governance documentation for Purview/Denodo.

**Major components:**
1. **Medallion Pipeline** (Staged/Bronze/Silver/Gold) - Progressive data refinement with checkpoints
2. **WiQ Semantic Model** - Hub-and-spoke dimensional model with DIM_NOC and DIM_JOB_ARCH as hubs, bridge tables for M:N relationships
3. **Knowledge Graph** - Vocabulary indexing for entity resolution and relationship traversal
4. **RAG Interface** - Hybrid retriever combining vector search (semantic) and graph traversal (structured)
5. **Power BI Layer** - Semantic model with DAX measures, RLS, Direct Lake connection
6. **Artifact Export** - Data dictionary and lineage documentation to Purview/Denodo formats

### Critical Pitfalls

1. **Layer responsibility leakage** - Business logic appearing in Bronze/Silver instead of Gold causes conflicting metric definitions. **Avoid:** Document layer contracts explicitly; enforce naming conventions (bronze_*, silver_*, gold_*); code review flags business logic outside Gold.

2. **DADM compliance as afterthought** - Bolting on compliance tracking after building creates incomplete audit trails. **Avoid:** Design provenance tracking into schemas from day 1 (source_system, ingestion_timestamp, transform_version); map each data element to DADM requirements early.

3. **NOC-to-ONET mapping without imputation strategy** - Treating O*NET as directly joinable with NOC ignores taxonomy differences (SOC vs NOC). **Avoid:** Treat NOC as authoritative; build explicit crosswalk table with confidence scores; quarantine NOC codes without reliable O*NET mapping.

4. **Power BI semantic model without star schema** - Importing Gold tables directly without dimensional transformation creates performance issues and incorrect calculations. **Avoid:** Gold layer should already model toward star schema; single direction relationships with DAX USERELATIONSHIP.

5. **Knowledge Graph RAG without evaluation framework** - "72% of enterprise RAG implementations fail within their first year" due to no accuracy baselines. **Avoid:** Build evaluation dataset before building RAG (golden Q&A pairs); measure retrieval precision; require source citation in every answer; set accuracy threshold (85%+) before release.

## Implications for Roadmap

Based on research, suggested phase structure:

### Phase 1: Data Foundation / Pipeline Infrastructure

**Rationale:** Pipeline must exist before any downstream components can be tested. Architecture research confirms medallion pipeline is foundational; all other layers depend on Gold output.

**Delivers:**
- Staged/Bronze/Silver/Gold layer infrastructure
- NOC 2021 v1.3 ingestion pipeline
- Schema validation framework with quarantine tables
- Provenance tracking in every table (_ingested_at, _source_file, _batch_id)

**Addresses:** NOC ingestion, metadata storage, version management (from FEATURES.md)

**Avoids:** Layer responsibility leakage, deferred data quality rules, DADM afterthought (from PITFALLS.md)

**Stack:** Polars, DuckDB, PyArrow, Pydantic for validation

### Phase 2: WiQ Semantic Model Core

**Rationale:** Semantic model structure must be designed before Power BI deployment. Hub-and-spoke pattern requires careful relationship design; bridge tables need cardinality rules.

**Delivers:**
- DIM_NOC hub dimension with hierarchy (4-digit to 1-digit)
- NOC attribute tables (Element, Oasis)
- FACT_NOC_COPS for forecasting data
- Star schema validated for Power BI consumption
- Business key preservation alongside surrogates

**Addresses:** Relationships & star schema, measure definitions infrastructure (from FEATURES.md)

**Uses:** Gold layer output, dimensional modeling patterns (from ARCHITECTURE.md)

**Avoids:** Snowflaking, Power BI semantic model without star schema (from PITFALLS.md)

### Phase 3: Power BI Deployment

**Rationale:** Primary consumption point for Government of Canada analysts. Must be deployed before RAG since RAG queries should be validated against semantic model answers.

**Delivers:**
- Power BI semantic model (Direct Lake connection)
- DAX measures (headcount, FTE, vacancy rates, turnover)
- Row-Level Security by department
- Business descriptions (glossary population in model)
- Model documentation export

**Addresses:** Power BI semantic model deployment, RLS, model documentation export (from FEATURES.md)

**Uses:** semantic-link-labs, TMDL for version control (from STACK.md)

**Avoids:** Embedded data in reports, RLS implemented too late (from PITFALLS.md)

### Phase 4: O*NET Integration and Crosswalk

**Rationale:** O*NET enriches NOC with skill/task data but requires explicit crosswalk with confidence scores. Keeping this separate from Phase 1 prevents NOC-ONET mapping pitfalls.

**Delivers:**
- O*NET-SOC 2019 ingestion pipeline
- NOC-SOC crosswalk table with confidence scores and match methodology
- O*NET attribute integration (skills, tasks, work context)
- Quarantine for NOC codes without reliable mapping

**Addresses:** O*NET/SOC integration, NOC-SOC crosswalk (from FEATURES.md)

**Avoids:** NOC-to-ONET mapping without imputation strategy (from PITFALLS.md)

### Phase 5: Data Governance Artifacts

**Rationale:** Governance documentation can be generated once semantic model is stable. Metadata lives in code; documentation is generated, not hand-edited.

**Delivers:**
- Data dictionary generation (automated from schema)
- Business glossary (structured format, CI/CD validated)
- Lineage documentation (cross-system coverage)
- Purview export adapter
- Denodo export adapter

**Addresses:** Data dictionary, business glossary, metadata catalog, export to standard formats (from FEATURES.md)

**Uses:** OpenLineage, SQLLineage, azure-purview-datamap (from STACK.md)

**Avoids:** Metadata catalog as static wiki, lineage without cross-system coverage (from PITFALLS.md)

### Phase 6: Knowledge Graph and RAG

**Rationale:** RAG is high-complexity differentiator that depends on stable semantic model. Architecture research shows hybrid GraphRAG (vector + graph) outperforms either alone. Must build evaluation framework first.

**Delivers:**
- Knowledge graph indexing from WiQ entities
- Vector embeddings for entity descriptions
- Hybrid retriever (vector search + graph traversal)
- LLM integration with source citations
- Evaluation framework with golden Q&A dataset (85% accuracy threshold)

**Addresses:** Natural language query, contextual follow-up, query explanation (from FEATURES.md)

**Uses:** LlamaIndex, Qdrant, RDFLib (from STACK.md)

**Avoids:** RAG without evaluation framework (from PITFALLS.md)

### Phase Ordering Rationale

- **Foundation before consumption:** Pipeline (1) feeds semantic model (2), which feeds Power BI (3) and RAG (6). This order is non-negotiable based on architecture dependencies.
- **NOC before O*NET:** O*NET integration (4) is deliberately separate to avoid crosswalk pitfalls. NOC is authoritative; O*NET supplements.
- **Power BI before RAG:** Analysts need working Power BI before conversational interface. RAG answers can be validated against semantic model.
- **Governance parallel track:** Artifact export (5) can be developed in parallel with O*NET integration once semantic model is stable.
- **RAG is final:** Highest complexity, highest risk of failure. Build only after foundation is solid and evaluation framework exists.

### Research Flags

Phases likely needing deeper research during planning:
- **Phase 4 (O*NET Integration):** Crosswalk methodology requires detailed research on SOC-NOC alignment; confidence scoring approach needs validation
- **Phase 6 (Knowledge Graph / RAG):** Evaluation framework design, hybrid retrieval tuning, multi-hop reasoning testing - sparse documentation on GC-specific implementations

Phases with standard patterns (skip research-phase):
- **Phase 1 (Pipeline Foundation):** Medallion architecture is well-documented; Polars/DuckDB patterns established
- **Phase 3 (Power BI Deployment):** semantic-link-labs has official documentation; Direct Lake patterns documented by Microsoft
- **Phase 5 (Governance Artifacts):** OpenLineage is industry standard; Purview SDK has official documentation

## Confidence Assessment

| Area | Confidence | Notes |
|------|------------|-------|
| Stack | HIGH | All versions verified via PyPI; official Microsoft documentation for semantic-link-labs |
| Features | MEDIUM-HIGH | Feature landscape synthesized from multiple workforce intelligence platforms; DADM requirements from official directive |
| Architecture | HIGH | Medallion, hub-and-spoke, GraphRAG patterns verified via authoritative sources (Databricks, Kimball, Neo4j) |
| Pitfalls | HIGH | Multiple sources cross-referenced; GC-specific warnings from official DADM documentation |

**Overall confidence:** HIGH

### Gaps to Address

- **O*NET imputation methodology:** Explicit crosswalk approach needs validation during Phase 4 planning. Research shows many-to-many mapping complexity but doesn't prescribe specific confidence scoring.
- **RAG evaluation benchmarks:** What constitutes "acceptable" accuracy for GC workforce intelligence queries? Research cites 85% as common threshold but domain-specific validation needed.
- **Denodo AI SDK maturity:** Newer (2025) SDK with limited community validation. REST API fallback available if SDK proves unstable.
- **DADM transition requirements:** New requirements effective June 24, 2025 with compliance deadline June 24, 2026. Monitor TBS announcements during development.

## Sources

### Primary (HIGH confidence)
- [PyPI - semantic-link-labs 0.12.9](https://pypi.org/project/semantic-link-labs/)
- [PyPI - Polars 1.37.1](https://pypi.org/project/polars/)
- [PyPI - DuckDB 1.4.3](https://pypi.org/project/duckdb/)
- [PyPI - LlamaIndex 0.14.12](https://pypi.org/project/llama-index/)
- [Microsoft Learn - Semantic Link](https://learn.microsoft.com/en-us/fabric/data-science/semantic-link-power-bi)
- [Microsoft Learn - Medallion Architecture](https://learn.microsoft.com/en-us/azure/databricks/lakehouse/medallion)
- [Databricks - Medallion Architecture](https://www.databricks.com/glossary/medallion-architecture)
- [Kimball Group - Bridge Tables](https://www.kimballgroup.com/2012/02/design-tip-142-building-bridges/)
- [Canada DADM Directive](https://www.tbs-sct.canada.ca/pol/doc-eng.aspx?id=32592)

### Secondary (MEDIUM confidence)
- [Neo4j - RAG Tutorial](https://neo4j.com/blog/developer/rag-tutorial/)
- [Microsoft GraphRAG](https://microsoft.github.io/graphrag/)
- [O*NET Resource Center - Crosswalks](https://www.onetcenter.org/crosswalks.html)
- [LangChain vs LlamaIndex 2025 Comparison](https://latenode.com/blog/platform-comparisons-alternatives/automation-platform-comparisons/langchain-vs-llamaindex-2025-complete-rag-framework-comparison)
- [ChromaDB vs Qdrant Comparison](https://aloa.co/ai/comparisons/vector-database-comparison/chroma-vs-qdrant)

### Tertiary (LOW confidence)
- [Denodo AI SDK](https://community.denodo.com/docs/html/document/denodoconnects/latest/en/Denodo%20AI%20SDK%20-%20User%20Manual) - newer SDK, limited community validation
- [ESCO-O*NET Crosswalk Technical Report](https://esco.ec.europa.eu/en/about-esco/data-science-and-esco/crosswalk-between-esco-and-onet) - European context, needs adaptation for NOC

---
*Research completed: 2026-01-18*
*Ready for roadmap: yes*
