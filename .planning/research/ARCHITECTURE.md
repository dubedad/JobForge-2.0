# Architecture Patterns

**Domain:** Workforce Intelligence Platform (Data Pipeline + Semantic Model + RAG)
**Researched:** 2026-01-18
**Confidence:** HIGH (patterns verified via authoritative sources)

## Executive Summary

JobForge combines three mature architecture patterns that are well-documented in industry practice:

1. **Medallion Architecture** for staged ETL (bronze/silver/gold)
2. **Hub-and-Spoke Dimensional Model** with bridge tables for WiQ semantic model
3. **Hybrid GraphRAG** combining knowledge graph traversal with vector retrieval

These patterns are synergistic: the medallion pipeline feeds the semantic model, which feeds both the Power BI deployment and the knowledge graph, which powers the RAG interface. The architecture is fundamentally a **data governance platform** with multiple consumption surfaces.

---

## System Architecture Overview

```
                                    +-----------------------+
                                    |   Consumption Layer   |
                                    |                       |
                    +---------------+  Power BI Semantic    |
                    |               |  Model (Direct Lake)  |
                    |               +-----------+-----------+
                    |                           |
                    v                           |
+-------------------+-------------------+       |
|        Semantic Model (WiQ)           |       |
|                                       |       |
|  +-------------+   +---------------+  |       |
|  | DIM NOC     |   | DIM Job Arch  |  |       |
|  | (Hub)       |   | (Hub)         |  |       |
|  +------+------+   +-------+-------+  |       |
|         |                  |          |       |
|  +------v------+   +-------v-------+  |       |
|  | Attribute   |   | Bridge Tables |  |       |
|  | Tables      |   | (M:M links)   |  |       |
|  | (Element,   |   |               |  |       |
|  |  Oasis)     |   |               |  |       |
|  +-------------+   +---------------+  |       |
|         |                             |       |
|  +------v--------------------------+  |       |
|  | Fact Tables (COPS forecasting)  |  |       |
|  +---------------------------------+  |       |
+-------------------+-------------------+       |
                    |                           |
                    |    +----------------------+
                    |    |
                    v    v
+-------------------+----+------------------+
|           Knowledge Graph                 |
|  (Occupational vocabulary indexed)        |
|                                           |
|  Entities: Occupations, Skills, Tasks,    |
|            Job Titles, Attributes         |
|  Relationships: requires_skill, maps_to,  |
|                 has_attribute, forecasts  |
+-------------------+-----------------------+
                    |
                    v
+-------------------+-----------------------+
|         RAG Interface Layer               |
|                                           |
|  +-------------+     +----------------+   |
|  | Vector DB   |     | Graph Retriever|   |
|  | (semantic)  |     | (structured)   |   |
|  +------+------+     +-------+--------+   |
|         |                    |            |
|         +--------+-----------+            |
|                  |                        |
|         +--------v--------+               |
|         | Hybrid Retriever|               |
|         +--------+--------+               |
|                  |                        |
|         +--------v--------+               |
|         | LLM Generator   |               |
|         +-----------------+               |
+-------------------------------------------+
                    |
                    v
+-------------------------------------------+
|         Artifact Export Layer             |
|                                           |
|  Data Dictionary --> Purview / Denodo     |
|  Lineage Docs    --> Purview / Denodo     |
|  DADM Compliance --> Audit reports        |
+-------------------------------------------+
                    ^
                    |
                    |
+-------------------+-------------------+
|        Medallion Pipeline             |
|                                       |
|  STAGED --> BRONZE --> SILVER --> GOLD|
|  (raw)     (typed)   (clean)   (model)|
|                                       |
|  Sources: NOC, O*NET/SOC, COPS        |
+---------------------------------------+
```

---

## Component Boundaries

| Component | Responsibility | Inputs | Outputs | Dependencies |
|-----------|---------------|--------|---------|--------------|
| **Staged Layer** | Raw ingestion, preserve source fidelity | Source files (CSV, XML, API) | Parquet files with metadata | None |
| **Bronze Layer** | Type enforcement, schema standardization | Staged parquet | Typed parquet with source tracking | Staged |
| **Silver Layer** | Deduplication, harmonization, validation | Bronze parquet | Clean, validated parquet | Bronze |
| **Gold Layer** | Business-ready dimensional model | Silver parquet | WiQ model tables (parquet) | Silver |
| **WiQ Model** | Semantic relationships, business logic | Gold parquet | Star schema with bridges | Gold |
| **Knowledge Graph** | Vocabulary indexing, entity relationships | WiQ model, attribute tables | Graph entities/edges | WiQ |
| **Vector Store** | Semantic embeddings for retrieval | WiQ descriptions, attribute text | Vector index | WiQ, KG |
| **RAG Interface** | Conversational query processing | User queries | Natural language responses | KG, Vector, LLM |
| **Power BI Layer** | Visualization, DAX measures, RLS | WiQ model (Direct Lake) | Reports, dashboards | WiQ (Gold) |
| **Artifact Export** | Governance documentation generation | WiQ metadata, lineage | Purview/Denodo format files | WiQ |

---

## Layer 1: Medallion Pipeline Architecture

### Pattern Description

The medallion architecture (bronze/silver/gold) provides progressive data refinement with checkpoints for replay and debugging. This is the dominant pattern for data lakehouse architectures in 2025.

**Source:** [Databricks Medallion Architecture](https://www.databricks.com/glossary/medallion-architecture), [Microsoft Learn](https://learn.microsoft.com/en-us/azure/databricks/lakehouse/medallion)

### JobForge Implementation

```
Sources                     Pipeline Stages                    Output
--------                    ---------------                    ------

NOC XML/CSV  ----+
                 |          +----------+
O*NET API    ----+--------> | STAGED   |  Raw files preserved
                 |          | Layer    |  with ingestion metadata
COPS CSV     ----+          +----+-----+
                                 |
                                 v
                            +----------+
                            | BRONZE   |  Schema applied
                            | Layer    |  Types enforced
                            +----+-----+  Source ID added
                                 |
                                 v
                            +----------+
                            | SILVER   |  Deduplicated
                            | Layer    |  Harmonized
                            +----+-----+  Validated
                                 |
                                 v
                            +----------+
                            | GOLD     |  Dimensional model
                            | Layer    |  Business keys
                            +----------+  Fact/Dim structure
```

### Stage Specifications

| Stage | Format | Purpose | Key Transformations |
|-------|--------|---------|---------------------|
| **Staged** | Parquet | Raw preservation | Add ingestion timestamp, source file ID, batch ID |
| **Bronze** | Parquet | Type standardization | Enforce schema, standardize date formats, add source_system column |
| **Silver** | Parquet | Clean & harmonize | Deduplicate on business keys, apply NOC-SOC crosswalk, validate referential integrity |
| **Gold** | Parquet | Business model | Build dimensional tables, compute derived fields, establish foreign keys |

### Best Practices Applied

1. **Schema-on-read for Bronze**: Accept new columns automatically; don't fail on schema changes
2. **Quarantine mechanism**: Isolate malformed records in separate error tables
3. **Metadata columns**: Every table carries `_ingested_at`, `_source_file`, `_batch_id`
4. **Idempotent processing**: Rerunning a stage produces identical output
5. **Incremental loading**: Silver and Gold use CDC patterns to process only changed records

### Data Flow (Concrete)

```
NOC 2021 v1.3 XML
    |
    v
staged/noc/2026-01-18/noc_2021_v1.3.parquet
    |  (add: _ingested_at, _source_file, _batch_id)
    v
bronze/noc/noc_occupations.parquet
    |  (enforce: noc_code VARCHAR(4), title VARCHAR(500), ...)
    v
silver/noc/dim_noc.parquet
    |  (dedupe on noc_code, add: is_current, valid_from, valid_to)
    v
gold/wiq/dim_noc.parquet
    |  (add: noc_key SURROGATE, business keys, relationships)
    v
WiQ semantic model (Power BI)
```

---

## Layer 2: Hub-and-Spoke Dimensional Model (WiQ)

### Pattern Description

The WiQ semantic model uses a **hub-and-spoke** dimensional architecture with two hub dimensions (DIM NOC, DIM Job Architecture) connected to attribute tables and fact tables via bridge tables.

**Source:** [Kimball Group - Bridge Tables](https://www.kimballgroup.com/2012/02/design-tip-142-building-bridges/), [Microsoft Fabric Dimensional Modeling](https://learn.microsoft.com/en-us/fabric/data-warehouse/dimensional-modeling-dimension-tables)

### Model Structure

```
                        +-------------------+
                        |    DIM NOC        |
                        |    (Hub 1)        |
                        |-------------------|
                        | noc_key (PK)      |
                        | noc_code (BK)     |
                        | noc_title         |
                        | noc_definition    |
                        | is_current        |
                        +--------+----------+
                                 |
          +----------------------+----------------------+
          |                      |                      |
          v                      v                      v
+------------------+  +------------------+  +------------------+
| NOC_ELEMENT      |  | NOC_OASIS        |  | FACT_NOC_COPS    |
| (Attribute)      |  | (Attribute)      |  | (Fact)           |
|------------------|  |------------------|  |------------------|
| noc_key (FK)     |  | noc_key (FK)     |  | noc_key (FK)     |
| element_type     |  | oasis_code       |  | forecast_year    |
| element_value    |  | oasis_name       |  | employment_count |
| element_desc     |  | oasis_level      |  | growth_rate      |
+------------------+  +------------------+  +------------------+

                        +-------------------+
                        | DIM JOB ARCH      |
                        | (Hub 2)           |
                        |-------------------|
                        | job_arch_key (PK) |
                        | job_title (BK)    |
                        | job_family        |
                        | job_level         |
                        +--------+----------+
                                 |
          +----------------------+----------------------+
          |                      |                      |
          v                      v                      v
+------------------+  +------------------+  +------------------+
| BRIDGE_NOC_JOB   |  | DIM_OCC_GROUP    |  | BRIDGE_JOB_POS   |
| (Bridge)         |  | (Dim)            |  | (Bridge)         |
|------------------|  |------------------|  |------------------|
| noc_key (FK)     |  | occ_group_key    |  | job_arch_key(FK) |
| job_arch_key(FK) |  | group_name       |  | position_id (FK) |
| match_confidence |  | job_arch_key(FK) |  | match_score      |
| match_method     |  | parent_group_key |  | match_date       |
+------------------+  +------------------+  +------------------+
```

### Bridge Table Pattern

Bridge tables resolve many-to-many relationships that are common in occupational data:

- **One NOC code** can map to **many Job Architecture titles** (e.g., NOC 21232 "Software Developers" maps to "Senior Developer", "Full-Stack Engineer", etc.)
- **One Job Title** can map to **many NOC codes** (rare but possible with hybrid roles)
- **One Job Title** can appear in **many Positions** across the organization

**Bridge Table Best Practices (from Kimball):**

1. Include **weighting factor** for double-counting prevention in aggregations
2. Include **match metadata** (confidence score, method, date) for governance
3. Maintain **SCD Type 2** for time-variant relationships (job-to-NOC mapping changes)
4. Keep bridge tables **narrow** (just keys + metadata)

### Cardinality Rules

| Relationship | Cardinality | Implementation |
|--------------|-------------|----------------|
| DIM_NOC : NOC_ELEMENT | 1:N | FK on element table |
| DIM_NOC : NOC_OASIS | 1:N | FK on oasis table |
| DIM_NOC : FACT_NOC_COPS | 1:N | FK on fact table |
| DIM_NOC : DIM_JOB_ARCH | M:N | BRIDGE_NOC_JOB |
| DIM_JOB_ARCH : DIM_OCC_GROUP | 1:N | FK on occ_group |
| DIM_JOB_ARCH : ORG_POSITIONS | M:N | BRIDGE_JOB_POS |

---

## Layer 3: Knowledge Graph Architecture

### Pattern Description

The knowledge graph indexes vocabulary across occupational data sources, enabling:
- Entity resolution (linking "Software Developer" to NOC 21232)
- Relationship traversal (what skills does this occupation require?)
- Semantic search (find occupations similar to X)

**Source:** [Neo4j GraphRAG Tutorial](https://neo4j.com/blog/developer/rag-tutorial/), [Microsoft GraphRAG](https://microsoft.github.io/graphrag/)

### Entity Model

```
+-------------+         +-------------+         +-------------+
| OCCUPATION  |-------->| SKILL       |<--------| TASK        |
| (NOC-based) | requires| (O*NET)     | supports|             |
+------+------+         +------+------+         +-------------+
       |                       |
       | maps_to               | related_to
       v                       v
+-------------+         +-------------+
| JOB_TITLE   |         | ATTRIBUTE   |
| (Org-based) |         | (Element,   |
+-------------+         |  Oasis)     |
                        +-------------+
```

### Node Types

| Node Type | Source | Attributes | Purpose |
|-----------|--------|------------|---------|
| Occupation | NOC, O*NET | code, title, definition, level | Canonical occupation representation |
| Skill | O*NET | skill_id, name, category, importance | Skills taxonomy |
| Task | O*NET | task_id, description, occupation_id | Work activities |
| Attribute | NOC Elements, Oasis | type, value, description | Occupational qualifiers |
| JobTitle | Job Architecture | title, family, level | Organizational job nomenclature |

### Edge Types

| Edge Type | From | To | Attributes |
|-----------|------|-----|------------|
| REQUIRES_SKILL | Occupation | Skill | importance, level |
| PERFORMS_TASK | Occupation | Task | frequency |
| HAS_ATTRIBUTE | Occupation | Attribute | value |
| MAPS_TO | JobTitle | Occupation | confidence, method |
| FORECASTS | Occupation | COPSForecast | year, scenario |
| RELATED_TO | Skill | Skill | similarity_score |

### Storage Options

| Option | Pros | Cons | Recommendation |
|--------|------|------|----------------|
| **Neo4j** | Native graph, Cypher queries, mature GraphRAG tooling | Separate service, licensing | Best for production |
| **NetworkX + SQLite** | Pure Python, no external deps, embeddings in SQLite | Limited scale, in-memory | Good for MVP |
| **Property Graph in Postgres** | Single DB, SQL + graph queries via extensions | Less native graph features | Good if already using Postgres |

**Recommendation:** Start with NetworkX for MVP development, migrate to Neo4j for production scale.

---

## Layer 4: Hybrid RAG Architecture

### Pattern Description

The RAG interface combines two retrieval channels:
1. **Vector search** for semantic similarity (find occupations "like" a description)
2. **Graph traversal** for structured relationships (what skills does NOC 21232 require?)

This hybrid approach outperforms either method alone, particularly for multi-hop reasoning queries common in workforce intelligence.

**Source:** [Memgraph HybridRAG](https://memgraph.com/blog/why-hybridrag), [Neo4j RAG Tutorial](https://neo4j.com/blog/developer/rag-tutorial/)

### Component Architecture

```
User Query: "What skills are at risk of shortage for software roles?"
    |
    v
+-------------------+
| Query Analyzer    |  Determine query type and routing
+--------+----------+
         |
    +----+----+
    |         |
    v         v
+-------+  +----------+
|Vector |  |Graph     |
|Search |  |Traversal |
+---+---+  +----+-----+
    |           |
    v           v
+-------+  +----------+
|Similar|  |Structured|
|Docs   |  |Results   |
+---+---+  +----+-----+
    |           |
    +-----+-----+
          |
          v
+-------------------+
| Result Merger     |  Combine and rank results
+--------+----------+
         |
         v
+-------------------+
| Context Builder   |  Format context for LLM
+--------+----------+
         |
         v
+-------------------+
| LLM Generator     |  Generate natural language response
+--------+----------+
         |
         v
Response: "Based on COPS forecasting data, the following skills
associated with software occupations (NOC 21232, 21234) show
projected shortages by 2028: ..."
```

### Query Routing

| Query Type | Example | Primary Retrieval | Secondary |
|------------|---------|-------------------|-----------|
| **Semantic** | "Jobs like data scientist" | Vector search | Graph (related occupations) |
| **Structured** | "Skills for NOC 21232" | Graph traversal | Vector (similar skills) |
| **Aggregation** | "Fastest growing occupations" | Graph (facts) | None |
| **Multi-hop** | "Skills at risk for tech roles" | Graph + Graph | Vector (fallback) |
| **Lineage** | "Where does this data come from?" | Graph (metadata) | None |

### Vector Store Requirements

| Requirement | Specification |
|-------------|---------------|
| Embedding model | text-embedding-3-small or similar |
| Chunk strategy | Entity descriptions, not documents |
| Index type | HNSW for production scale |
| Metadata filters | source_type, noc_code, date |

---

## Layer 5: Power BI Deployment Architecture

### Pattern Description

The WiQ semantic model deploys to Power BI using Direct Lake mode for optimal performance with parquet files, combined with Import mode for smaller reference tables.

**Source:** [Microsoft Fabric Direct Lake](https://learn.microsoft.com/en-us/fabric/fundamentals/direct-lake-develop), [Power BI Semantic Models](https://learn.microsoft.com/en-us/power-bi/connect-data/service-datasets-understand)

### Deployment Model

```
Gold Layer (Parquet)          Power BI Semantic Model
--------------------          ----------------------

dim_noc.parquet       ---->   DIM_NOC (Direct Lake)
dim_job_arch.parquet  ---->   DIM_JOB_ARCH (Direct Lake)
fact_cops.parquet     ---->   FACT_COPS (Direct Lake)
bridge_noc_job.parquet ---->  BRIDGE_NOC_JOB (Direct Lake)

Reference tables      ---->   Imported (small, static)
DAX measures          ---->   Calculated in model
RLS rules             ---->   Per-department access
```

### Model Artifacts

| Artifact | Purpose | Format |
|----------|---------|--------|
| Semantic model | Tables, relationships, measures | PBIX or TMDL |
| DAX measures | Business calculations | Embedded in model |
| RLS rules | Row-level security | Embedded in model |
| Display folders | Organization | Embedded in model |
| Descriptions | Business glossary | Table/column properties |

### Best Practices Applied

1. **Star schema maintained**: Even with bridge tables, fact tables reference dimensions
2. **Narrow dimensions**: Only include columns needed for filtering/slicing
3. **Calculation groups**: Reduce measure proliferation (time intelligence, etc.)
4. **No snowflaking**: Flatten hierarchies into dimensions
5. **Business key preservation**: Maintain natural keys alongside surrogates

---

## Layer 6: Artifact Export Architecture

### Pattern Description

Export governance artifacts in platform-native formats for Purview (Azure data catalog) and Denodo (data virtualization).

**Source:** [Microsoft Purview Data Lineage](https://learn.microsoft.com/en-us/purview/data-gov-classic-lineage-user-guide)

### Export Flow

```
WiQ Metadata                    Export Targets
------------                    --------------

Table definitions   -----+
Column descriptions      |----> Data Dictionary
Business glossary   -----+      (Excel, JSON, Purview format)

Source mappings     -----+
Transformation log       |----> Lineage Documentation
Pipeline metadata   -----+      (Purview API, SVG diagrams)

DADM mapping        -----+
Compliance scores        |----> Compliance Reports
Audit trail         -----+      (PDF, JSON)
```

### Export Formats

| Target | Format | Key Fields |
|--------|--------|------------|
| **Purview** | JSON (Atlas API) | qualifiedName, typeName, attributes, lineage edges |
| **Denodo** | VQL metadata | view definitions, source mappings |
| **Data Dictionary** | Excel/JSON | table, column, type, description, source, glossary_term |
| **Lineage** | JSON/SVG | source_table, target_table, transformation, timestamp |

---

## Build Order and Dependencies

Based on the architecture, components should be built in this order:

### Phase 1: Pipeline Foundation

```
[1.1] Staged Layer
       |
       v
[1.2] Bronze Layer
       |
       v
[1.3] Silver Layer
       |
       v
[1.4] Gold Layer (dimensional tables only, no relationships yet)
```

**Rationale:** Pipeline must exist before any downstream components can be tested.

### Phase 2: Semantic Model Core

```
[2.1] DIM_NOC (hub dimension)
       |
       v
[2.2] NOC Attribute tables (Element, Oasis) --> connects to DIM_NOC
       |
       v
[2.3] FACT_COPS --> connects to DIM_NOC
       |
       v
[2.4] DIM_JOB_ARCH (hub dimension)
       |
       v
[2.5] BRIDGE_NOC_JOB --> connects hubs
```

**Rationale:** Build outward from hub dimensions. Each step validates referential integrity.

### Phase 3: Power BI Deployment

```
[3.1] Power BI semantic model (Direct Lake connection)
       |
       v
[3.2] DAX measures
       |
       v
[3.3] RLS rules
       |
       v
[3.4] Business descriptions (glossary population)
```

**Rationale:** Model structure before logic before access control before documentation.

### Phase 4: Knowledge Graph

```
[4.1] Entity extraction from WiQ
       |
       v
[4.2] Relationship mapping
       |
       v
[4.3] Graph indexing
       |
       v
[4.4] Graph querying API
```

**Rationale:** Can be built in parallel with Phase 3 once Gold layer exists.

### Phase 5: RAG Interface

```
[5.1] Vector embeddings for entities
       |
       v
[5.2] Vector store indexing
       |
       v
[5.3] Hybrid retriever (vector + graph)
       |
       v
[5.4] LLM integration
       |
       v
[5.5] Conversational interface
```

**Rationale:** Depends on both Power BI deployment (for testing queries) and Knowledge Graph.

### Phase 6: Artifact Export

```
[6.1] Data dictionary generation
       |
       v
[6.2] Lineage documentation
       |
       v
[6.3] Purview export adapter
       |
       v
[6.4] Denodo export adapter
```

**Rationale:** Can be built in parallel with RAG once model metadata is stable.

### Dependency Graph

```
Phase 1 (Pipeline)
    |
    v
Phase 2 (Semantic Model)
    |
    +-------+-------+
    |       |       |
    v       v       v
Phase 3  Phase 4  Phase 6
(Power   (Know-   (Artifact
 BI)     ledge    Export)
         Graph)
    |       |
    +---+---+
        |
        v
    Phase 5
    (RAG)
```

---

## Anti-Patterns to Avoid

### Anti-Pattern 1: Skipping Bronze Layer

**What:** Writing directly from staged to silver to "save time"
**Why bad:** Lose schema standardization checkpoint; schema changes cause cascading failures
**Instead:** Always have bronze enforce types and add source tracking

### Anti-Pattern 2: Snowflaking the Dimensional Model

**What:** Creating normalized hierarchies (NOC -> Major Group -> Minor Group -> Occupation)
**Why bad:** Kills Power BI query performance; complicates DAX
**Instead:** Flatten into single DIM_NOC with denormalized hierarchy columns

### Anti-Pattern 3: Separate Knowledge Graph from Semantic Model

**What:** Building KG from source data instead of gold layer
**Why bad:** Creates two sources of truth; lineage becomes unmaintainable
**Instead:** KG indexes WiQ model entities, not source data

### Anti-Pattern 4: Over-Embedding in RAG

**What:** Embedding full documents or large text blocks
**Why bad:** Retrieval gets noisy; context windows fill with irrelevant text
**Instead:** Embed entity descriptions; use graph for relationships

### Anti-Pattern 5: Monolithic Workspace

**What:** All pipeline stages, models, and reports in single workspace
**Why bad:** Lineage becomes untraceable; access control impossible
**Instead:** Separate workspaces per medallion layer

---

## Scalability Considerations

| Concern | 100 Users | 10K Users | 100K Users |
|---------|-----------|-----------|------------|
| **Query latency** | Direct Lake sufficient | Add aggregations | Pre-computed aggregates |
| **RAG throughput** | Single LLM endpoint | Load balanced endpoints | Cached common queries |
| **Graph size** | NetworkX in-memory | Neo4j single node | Neo4j cluster |
| **Pipeline refresh** | Full refresh OK | Incremental only | Streaming ingestion |
| **Artifact export** | On-demand | Scheduled | Event-driven |

---

## Technology Recommendations

| Component | Recommended | Alternative | Rationale |
|-----------|-------------|-------------|-----------|
| **Pipeline orchestration** | Python scripts | Prefect, Airflow | Simplicity for MVP; upgrade for production |
| **Parquet processing** | Polars | Pandas, DuckDB | Performance + memory efficiency |
| **Graph storage** | NetworkX (MVP) / Neo4j (prod) | ArangoDB | Maturity of GraphRAG ecosystem |
| **Vector store** | ChromaDB (MVP) / Pinecone (prod) | Weaviate | Simplicity for MVP |
| **LLM** | Claude API | OpenAI, local models | Quality for reasoning queries |
| **Power BI deployment** | python-pptx + REST API | Tabular Editor | Python-native for consistency |

---

## Sources

**Medallion Architecture:**
- [Databricks - What is Medallion Architecture](https://www.databricks.com/glossary/medallion-architecture)
- [Microsoft Learn - Medallion Lakehouse Architecture](https://learn.microsoft.com/en-us/azure/databricks/lakehouse/medallion)
- [Weld Blog - Medallion Layers](https://weld.app/blog/medallion-layers)

**Dimensional Modeling:**
- [Kimball Group - Design Tip 142: Building Bridges](https://www.kimballgroup.com/2012/02/design-tip-142-building-bridges/)
- [Kimball - Multivalued Dimensions and Bridge Tables](https://www.kimballgroup.com/data-warehouse-business-intelligence-resources/kimball-techniques/dimensional-modeling-techniques/multivalued-dimension-bridge-table/)
- [Microsoft Fabric - Modeling Dimension Tables](https://learn.microsoft.com/en-us/fabric/data-warehouse/dimensional-modeling-dimension-tables)

**Knowledge Graph + RAG:**
- [Neo4j - RAG Tutorial](https://neo4j.com/blog/developer/rag-tutorial/)
- [Microsoft GraphRAG](https://microsoft.github.io/graphrag/)
- [Memgraph - Why HybridRAG](https://memgraph.com/blog/why-hybridrag)
- [Databricks - Knowledge Graph RAG Systems](https://www.databricks.com/blog/building-improving-and-deploying-knowledge-graph-rag-systems-databricks)

**Power BI:**
- [Microsoft Learn - Power BI Semantic Models](https://learn.microsoft.com/en-us/power-bi/connect-data/service-datasets-understand)
- [Microsoft Fabric - Direct Lake](https://learn.microsoft.com/en-us/fabric/fundamentals/direct-lake-develop)

**Occupational Data:**
- [O*NET Resource Center - Crosswalks](https://www.onetcenter.org/crosswalks.html)
- [Occupation Ontology (OccO)](https://github.com/Occupation-Ontology/OccO)

**Data Governance:**
- [Microsoft Purview - Data Lineage](https://learn.microsoft.com/en-us/purview/data-gov-classic-lineage-user-guide)
- [Microsoft Purview - Best Practices](https://learn.microsoft.com/en-us/purview/concept-best-practices-lineage-azure-data-factory)
