# Architecture Patterns

**Domain:** Workforce Intelligence Platform (Data Pipeline + Semantic Model + RAG)
**Researched:** 2026-01-18 (Updated: 2026-01-20 for Orbit Integration, 2026-02-05 for v4.0 Governance)
**Confidence:** HIGH (patterns verified via authoritative sources)

## Executive Summary

JobForge combines three mature architecture patterns that are well-documented in industry practice:

1. **Medallion Architecture** for staged ETL (bronze/silver/gold)
2. **Hub-and-Spoke Dimensional Model** with bridge tables for WiQ semantic model
3. **Hybrid GraphRAG** combining knowledge graph traversal with vector retrieval

These patterns are synergistic: the medallion pipeline feeds the semantic model, which feeds both the Power BI deployment and the knowledge graph, which powers the RAG interface. The architecture is fundamentally a **data governance platform** with multiple consumption surfaces.

---

## v4.0 Governance Integration Architecture (NEW)

### Overview

v4.0 governance features integrate through **5 architectural extension points** in the existing JobForge architecture:

1. **Compliance Layer** - New `governance/dqmf/` subdirectory extending existing RTM pattern
2. **Quality API Endpoint** - New `/api/quality/metrics` extending existing FastAPI routes
3. **Catalog Enrichment** - Business metadata fields in existing `data/catalog/tables/*.json`
4. **Ingestion Pipeline** - O*NET and PAA/DRF follow established medallion patterns
5. **CLI Commands** - New Typer subcommands following `jobforge caf` pattern

**Key insight:** No architectural refactoring required. All v4.0 features are **additive** to existing patterns.

### v4.0 System Integration Diagram

```
+-----------------------------------------------------------------------------------+
|                              JobForge v4.0 Architecture                           |
+-----------------------------------------------------------------------------------+
|                                                                                   |
|  +------------------------+     +------------------------+     +---------------+ |
|  |  External Data Sources |     |  v4.0 NEW Sources      |     | Policy Docs   | |
|  +------------------------+     +------------------------+     +---------------+ |
|  | StatCan NOC, COPS      |     | O*NET Web Services     |     | DADM PDF      | |
|  | OaSIS Proficiencies    |     | TBS InfoBase (PAA/DRF) |     | DAMA DMBOK    | |
|  | TBS OG, CAF forces.ca  |     | Dept Plans PDF         |     | Classification| |
|  +----------+-------------+     +----------+-------------+     +-------+-------+ |
|             |                              |                           |         |
|             v                              v                           v         |
|  +----------+-------------+     +----------+-------------+     +-------+-------+ |
|  | src/jobforge/external/ |     | src/jobforge/external/ |     | governance/   | |
|  | tbs/, caf/, onet/      |     | onet/, paa/  [NEW]     |     | policy/       | |
|  +----------+-------------+     +----------+-------------+     | parser.py     | |
|             |                              |                   +-------+-------+ |
|             |                              |                           |         |
|             +---------------+--------------+                           |         |
|                             |                                          |         |
|                             v                                          |         |
|           +------------------------------------------------------+     |         |
|           |              Medallion Pipeline                       |     |         |
|           |  staged -> bronze -> silver -> gold (*.parquet)       |     |         |
|           |  src/jobforge/pipeline/                               |     |         |
|           |  src/jobforge/ingestion/ (noc, og, caf, onet [NEW])   |     |         |
|           +----------------------------+-------------------------+     |         |
|                                        |                               |         |
|                                        v                               |         |
|           +------------------------------------------------------+     |         |
|           |              data/gold/*.parquet                      |     |         |
|           |  dim_noc, dim_og, dim_caf_*, bridge_*, cops_*, ...    |     |         |
|           |  + dim_onet_* [NEW]                                   |     |         |
|           |  + bridge_noc_onet [NEW]                              |     |         |
|           |  + paa_*, drf_* [NEW]                                 |     |         |
|           +----------------------------+-------------------------+     |         |
|                                        |                               |         |
|                                        v                               |         |
|  +---------------------------------------------------------------------+---------+
|  |                        Data Governance Layer                                  |
|  +-------------------------------------------------------------------------------+
|  |                                                                               |
|  |  +---------------------------+  +---------------------------+                 |
|  |  | data/catalog/             |  | src/jobforge/governance/  |                 |
|  |  +---------------------------+  +---------------------------+                 |
|  |  | tables/*.json             |  | compliance/               |                 |
|  |  |   + business_purpose [NEW]|  |   dama.py (existing)      |                 |
|  |  |   + business_questions    |  |   dadm.py (existing)      |                 |
|  |  |   + business_owner        |  |   dqmf.py [NEW]           |                 |
|  |  | lineage/*.json            |  | dqmf/                     |                 |
|  |  | schemas/wiq_schema.json   |  |   dimensions.py [NEW]     |                 |
|  |  | compliance/  [NEW]        |  |   metrics.py [NEW]        |                 |
|  |  |   dama_audit_*.json       |  | policy/                   |                 |
|  |  |   dqmf_scores_*.json      |  |   parser.py [NEW]         |                 |
|  |  +---------------------------+  |   provenance.py [NEW]     |                 |
|  |                                 +---------------------------+                 |
|  +-------------------------------------------------------------------------------+
|                                        |                                         |
|                                        v                                         |
|           +------------------------------------------------------+               |
|           |              FastAPI Service Layer                    |               |
|           |  src/jobforge/api/                                    |               |
|           +------------------------------------------------------+               |
|           | /api/query/data     - Text-to-SQL (existing)          |               |
|           | /api/query/metadata - Lineage queries (existing)      |               |
|           | /api/compliance/{f} - RTM logs (existing)             |               |
|           | /api/quality/metrics [NEW] - DQMF dashboard           |               |
|           | /api/quality/scores/{table} [NEW] - Table scores      |               |
|           +------------------------------------------------------+               |
|                                                                                   |
+-----------------------------------------------------------------------------------+
```

### v4.0 Component Responsibilities

#### Existing Components (Integration Points)

| Component | Responsibility | v4.0 Integration Point |
|-----------|----------------|------------------------|
| `src/jobforge/pipeline/` | Medallion architecture, layer transitions | O*NET/PAA ingestion uses same patterns |
| `src/jobforge/ingestion/` | Table-specific ETL (noc.py, og.py, caf.py) | Add onet.py, paa.py following same pattern |
| `src/jobforge/external/` | Web scrapers, API clients (tbs/, caf/, onet/) | Extend onet/, add paa/ with same structure |
| `src/jobforge/governance/` | Lineage graph, catalogue, compliance logs | Add dqmf/, policy/ subdirectories |
| `src/jobforge/catalog/` | Catalog enrichment (enrich.py) | Add business metadata enrichment |
| `src/jobforge/api/routes.py` | FastAPI endpoints | Add /quality endpoint group |
| `data/catalog/tables/*.json` | Table metadata JSON files | Extend schema with business fields |
| `data/catalog/compliance/` | (NEW) Compliance artifacts storage | DAMA audits, DQMF scores |

#### New Components (v4.0)

| Component | Responsibility | Integration With |
|-----------|----------------|------------------|
| `governance/dqmf/dimensions.py` | GC DQMF 9-dimension definitions | Pydantic models consumed by metrics.py |
| `governance/dqmf/metrics.py` | Calculate quality scores per dimension | Polars/DuckDB queries on gold tables |
| `governance/dqmf/dashboard.py` | FastAPI endpoints for quality dashboard | Integrates with routes.py |
| `governance/policy/parser.py` | Extract paragraphs from policy PDFs | Uses pdfplumber (existing dep) |
| `governance/policy/provenance.py` | Map artifacts to policy clauses | Extends TraceabilityEntry model |
| `ingestion/onet.py` | O*NET occupation ingestion pipeline | Same pattern as ingestion/og.py |
| `external/paa/scraper.py` | TBS InfoBase PAA/DRF scraper | Same pattern as external/tbs/ |
| `cli/quality.py` | CLI for quality commands | Typer subapp like caf.py |

### v4.0 Recommended Project Structure Additions

```
src/jobforge/
|-- governance/
|   |-- __init__.py                 # Existing
|   |-- models.py                   # Existing (LineageNode, LineageEdge)
|   |-- graph.py                    # Existing (LineageGraph)
|   |-- query.py                    # Existing (LineageQueryEngine)
|   |-- catalogue.py                # Existing (CatalogueGenerator)
|   |-- compliance/
|   |   |-- __init__.py             # Existing
|   |   |-- models.py               # Existing (TraceabilityEntry, ComplianceLog)
|   |   |-- dama.py                 # Existing (DAMAComplianceLog)
|   |   |-- dadm.py                 # Existing (DADMComplianceLog)
|   |   |-- classification.py       # Existing
|   |   +-- dqmf.py                 # NEW: DQMFComplianceLog
|   |-- dqmf/                       # NEW: GC DQMF implementation
|   |   |-- __init__.py
|   |   |-- dimensions.py           # 9 dimension enum + check definitions
|   |   |-- metrics.py              # Quality score calculations
|   |   |-- dashboard.py            # /api/quality endpoint handlers
|   |   +-- models.py               # QualityScore, DimensionResult Pydantic
|   +-- policy/                     # NEW: Policy provenance
|       |-- __init__.py
|       |-- parser.py               # PDF paragraph extraction
|       |-- provenance.py           # Artifact-to-clause mapping
|       +-- models.py               # PolicyParagraph, ProvenanceLink Pydantic
|
|-- external/
|   |-- onet/
|   |   |-- __init__.py             # Existing
|   |   |-- crosswalk.py            # Existing (NOCSOCCrosswalk)
|   |   |-- client.py               # Existing (ONetClient)
|   |   |-- adapter.py              # Existing (ONetAdapter)
|   |   +-- scraper.py              # NEW: Full O*NET taxonomy fetch
|   +-- paa/                        # NEW: PAA/DRF scraping
|       |-- __init__.py
|       |-- scraper.py              # TBS InfoBase scraper
|       |-- models.py               # PAAActivity, DRFOutcome Pydantic
|       +-- parser.py               # PDF parsing for Dept Plans
|
|-- ingestion/
|   |-- noc.py                      # Existing
|   |-- og.py                       # Existing
|   |-- caf.py                      # Existing
|   |-- onet.py                     # NEW: O*NET occupation ingestion
|   +-- paa.py                      # NEW: PAA/DRF ingestion
|
|-- api/
|   |-- __init__.py                 # Existing
|   |-- routes.py                   # Existing (add quality router)
|   |-- data_query.py               # Existing
|   |-- metadata_query.py           # Existing
|   |-- errors.py                   # Existing
|   +-- quality.py                  # NEW: Quality dashboard endpoints
|
+-- cli/
    |-- __init__.py                 # Existing
    |-- commands.py                 # Existing
    +-- quality.py                  # NEW: Quality CLI subcommands

data/
|-- catalog/
|   |-- tables/*.json               # Existing (+ business_purpose, business_questions fields)
|   |-- lineage/*.json              # Existing
|   |-- schemas/wiq_schema.json     # Existing (+ O*NET tables, PAA tables)
|   +-- compliance/                 # NEW: Compliance audit storage
|       |-- dama_audit_YYYYMMDD.json
|       |-- dqmf_scores_YYYYMMDD.json
|       +-- policy_provenance.json
|
+-- gold/
    |-- dim_noc.parquet             # Existing
    |-- dim_onet_occupation.parquet # NEW: O*NET occupations
    |-- bridge_noc_onet.parquet     # NEW: NOC-O*NET concordance
    |-- fact_onet_abilities.parquet # NEW: O*NET abilities
    |-- fact_onet_skills.parquet    # NEW: O*NET skills
    |-- fact_onet_knowledge.parquet # NEW: O*NET knowledge
    |-- dim_paa_activity.parquet    # NEW: PAA activities
    +-- dim_drf_outcome.parquet     # NEW: DRF outcomes
```

### v4.0 Data Flow for New Features

#### 1. DAMA Audit Workflow

Integration with `/gsd:verify-work`:

```
+-------------------+     +------------------------+     +---------------------+
| /gsd:verify-work  | --> | DAMAComplianceLog      | --> | data/catalog/       |
| (existing GSD     |     | .generate() with       |     | compliance/         |
| verification)     |     | phase_artifacts param  |     | dama_audit_*.json   |
+-------------------+     +------------------------+     +---------------------+
                                    |
                                    v
                          +------------------------+
                          | Phase SUMMARY.md       |
                          | includes DAMA section: |
                          | - Knowledge areas hit  |
                          | - Compliance status    |
                          +------------------------+
```

**Implementation hook:**
```python
# In /gsd:verify-work phase after technical verification
def audit_dama_compliance(phase_artifacts: list[str], config: PipelineConfig) -> ComplianceLog:
    """Audit phase against DAMA DMBOK knowledge areas."""
    generator = DAMAComplianceLog(config, phase_artifacts=phase_artifacts)
    return generator.generate()
```

#### 2. Data Quality Metrics API

```
+-------------------+     +------------------------+     +---------------------+
| /api/quality/     | --> | DQMFMetricsService     | --> | QualityScore        |
| metrics?table=X   |     | .calculate_scores()    |     | JSON response       |
+-------------------+     +------------------------+     +---------------------+
        ^                           |
        |                           v
        |                 +------------------------+
        |                 | DuckDB queries on      |
        |                 | gold/*.parquet         |
        |                 | - NULL counts          |
        |                 | - Distinct counts      |
        |                 | - Range validations    |
        |                 +------------------------+
        |                           |
        |                           v
        |                 +------------------------+
        |                 | data/catalog/          |
        |                 | compliance/            |
        |                 | dqmf_scores_*.json     |
        |                 +------------------------+
```

**Endpoint structure:**
```python
@api_app.get("/api/quality/metrics")
async def get_quality_metrics(
    table: str | None = None,
    dimension: DqmfDimension | None = None,
) -> QualityMetricsResponse:
    """Get quality scores, optionally filtered by table or dimension."""

@api_app.get("/api/quality/scores/{table_name}")
async def get_table_quality(table_name: str) -> TableQualityResponse:
    """Get all dimension scores for a specific table."""

@api_app.get("/api/quality/dashboard")
async def get_quality_dashboard() -> DashboardResponse:
    """Get aggregated quality dashboard data."""
```

#### 3. Policy Provenance Mapping

```
+-------------------+     +------------------------+     +---------------------+
| Policy PDF        | --> | policy/parser.py       | --> | PolicyParagraph[]   |
| (DADM, DMBOK)     |     | extract_paragraphs()   |     | with section IDs    |
+-------------------+     +------------------------+     +---------------------+
                                    |
                                    v
                          +------------------------+
                          | policy/provenance.py   |
                          | link_artifact_to_      |
                          | policy_clause()        |
                          +------------------------+
                                    |
                                    v
                          +------------------------+
                          | data/catalog/          |
                          | compliance/            |
                          | policy_provenance.json |
                          +------------------------+
```

**Provenance model extension:**
```python
class PolicyProvenanceLink(BaseModel):
    """Link from WiQ artifact to policy clause."""
    artifact_type: Literal["table", "column", "relationship", "transform"]
    artifact_id: str  # e.g., "gold.dim_noc.noc_code"
    policy_document: str  # e.g., "DADM-2024"
    policy_section: str  # e.g., "6.2.1"
    policy_paragraph: int
    policy_text_excerpt: str  # First 200 chars
    content_hash: str  # For change detection
    created_at: datetime
    created_by: str  # "system" or user
```

#### 4. O*NET Ingestion Pipeline

```
+-------------------+     +------------------------+     +---------------------+
| O*NET Web Services| --> | external/onet/         | --> | data/onet/          |
| API               |     | scraper.py             |     | occupations.json    |
|                   |     | (uses existing client) |     | abilities.json      |
+-------------------+     +------------------------+     | skills.json         |
                                    |                    | knowledge.json      |
                                    |                    +---------------------+
                                    v
                          +------------------------+
                          | ingestion/onet.py      |
                          | ingest_dim_onet_*()    |
                          +------------------------+
                                    |
                                    v
                          +------------------------+
                          | data/gold/             |
                          | dim_onet_occupation    |
                          | bridge_noc_onet        |
                          | fact_onet_*            |
                          +------------------------+
```

**Integration with existing O*NET module:**

The existing `external/onet/` module already has:
- `crosswalk.py` - NOC-SOC mapping (1,467 mappings)
- `client.py` - Async HTTP client with retry logic
- `adapter.py` - Convert O*NET responses to WiQ schema

v4.0 adds:
- `scraper.py` - Batch fetch all O*NET occupations for gold table creation
- New ingestion pipeline in `ingestion/onet.py`

#### 5. Business Metadata Capture

```
+-------------------+     +------------------------+     +---------------------+
| CLI interview     | --> | catalog/               | --> | data/catalog/       |
| workflow          |     | business_metadata.py   |     | tables/*.json       |
| (jobforge meta    |     | capture_business_      |     | + business_purpose  |
|  interview)       |     | context()              |     | + business_questions|
+-------------------+     +------------------------+     +---------------------+
```

**Catalog JSON schema extension:**
```json
{
  "table_name": "cops_employment",
  "description": "Employment counts by NOC occupation...",
  "business_purpose": "Track projected employment levels by occupation to support workforce planning decisions",
  "business_questions": [
    "Which occupations are projected to grow fastest over the next 10 years?",
    "What is the employment outlook for software engineers (NOC 21232)?",
    "How does projected employment compare between TEER 0 and TEER 1 occupations?"
  ],
  "business_owner": "Workforce Planning Division",
  "business_steward": "Labour Market Analysis Team",
  "columns": [ ... ]
}
```

### v4.0 Integration Points (Detailed)

#### Integration Point 1: Pipeline Engine

**Location:** `src/jobforge/pipeline/engine.py`

**Pattern:** O*NET and PAA/DRF ingestion use the same `PipelineEngine` for layer transitions.

```python
# Existing pattern (from og.py)
def ingest_dim_og(config: PipelineConfig) -> pl.DataFrame:
    """Ingest dim_og through medallion pipeline."""
    engine = PipelineEngine(config)

    # Load from external JSON
    df = _load_occupational_groups_json(config)

    # Stage the data
    engine.stage_dataframe(df, "dim_og")

    # Transition through layers
    engine.transition_to_bronze("dim_og", transforms=["validate_schema"])
    engine.transition_to_silver("dim_og", transforms=["deduplicate", "normalize"])
    engine.transition_to_gold("dim_og", transforms=["add_provenance"])

    return engine.get_gold_table("dim_og")

# NEW: Same pattern for O*NET
def ingest_dim_onet_occupation(config: PipelineConfig) -> pl.DataFrame:
    """Ingest O*NET occupations through medallion pipeline."""
    engine = PipelineEngine(config)

    # Load from O*NET JSON (scraped by external/onet/scraper.py)
    df = _load_onet_occupations_json(config)

    # Same transitions
    engine.stage_dataframe(df, "dim_onet_occupation")
    engine.transition_to_bronze("dim_onet_occupation", transforms=["validate_schema"])
    engine.transition_to_silver("dim_onet_occupation", transforms=["deduplicate"])
    engine.transition_to_gold("dim_onet_occupation", transforms=["add_provenance"])

    return engine.get_gold_table("dim_onet_occupation")
```

#### Integration Point 2: FastAPI Router

**Location:** `src/jobforge/api/routes.py`

**Pattern:** Quality endpoints follow same pattern as compliance endpoints.

```python
# Existing pattern
@api_app.get("/api/compliance/{framework}")
async def get_compliance(framework: str) -> dict:
    """Get compliance log for a framework."""
    ...

# NEW: Quality endpoints follow same pattern
from jobforge.governance.dqmf.dashboard import quality_router

# In create_api_app():
api_app.include_router(quality_router, prefix="/api/quality", tags=["quality"])
```

#### Integration Point 3: Catalog Enrichment

**Location:** `src/jobforge/catalog/enrich.py`

**Pattern:** Extend existing enrichment function for business metadata.

```python
# Existing pattern
def enrich_catalog(catalog_path: Path | None = None) -> dict[str, int]:
    """Enrich catalog JSON files with semantic descriptions."""
    ...

# NEW: Add business metadata enrichment
def enrich_business_metadata(
    table_name: str,
    business_purpose: str,
    business_questions: list[str],
    business_owner: str | None = None,
    catalog_path: Path | None = None,
) -> bool:
    """Add business metadata to a table's catalog entry."""
    ...
```

#### Integration Point 4: CLI Commands

**Location:** `src/jobforge/cli/commands.py`

**Pattern:** New subcommands follow `jobforge caf` pattern.

```python
# Existing pattern (from caf commands)
caf_app = typer.Typer(help="CAF data management commands")
app.add_typer(caf_app, name="caf")

@caf_app.command("refresh")
def caf_refresh(...):
    """Rebuild CAF gold tables."""
    ...

# NEW: Quality commands
quality_app = typer.Typer(help="Data quality commands")
app.add_typer(quality_app, name="quality")

@quality_app.command("score")
def quality_score(table: str | None = None, dimension: str | None = None):
    """Calculate and display quality scores."""
    ...

@quality_app.command("audit")
def quality_audit(output_format: str = "table"):
    """Run DAMA DMBOK compliance audit."""
    ...
```

#### Integration Point 5: Compliance Models

**Location:** `src/jobforge/governance/compliance/models.py`

**Pattern:** Extend TraceabilityEntry for policy provenance.

```python
# Existing model
class TraceabilityEntry(BaseModel):
    requirement_id: str
    requirement_text: str
    section: str
    status: ComplianceStatus
    evidence_type: str
    evidence_references: list[str]
    notes: str
    last_verified: datetime

# NEW: Extended for policy provenance
class PolicyTraceabilityEntry(TraceabilityEntry):
    """TraceabilityEntry with policy document provenance."""
    policy_document: str
    policy_version: str
    policy_paragraph_id: str
    policy_text_hash: str
    policy_url: str | None = None
```

### v4.0 Build Order

Based on dependencies and integration complexity:

| Phase | Focus | Dependencies | Rationale |
|-------|-------|--------------|-----------|
| **17** | Governance Compliance Framework | None | Foundation: defines compliance check structure, audit trail, policy provenance models |
| **18** | Data Quality Dashboard | Phase 17 (models) | Uses compliance models; adds DQMF metrics |
| **19** | Business Metadata Capture | Phase 18 (catalog extension) | Extends catalog; needs stable schema |
| **20** | O*NET Integration | Phase 17 (provenance) | Data ingestion; can run parallel with 18-19 |
| **21** | Job Architecture Enrichment | Phases 19-20 | Uses business metadata patterns; may use O*NET |
| **22** | PAA/DRF Data Layer | Phase 20 (scraping patterns) | Similar patterns to O*NET; new data source |
| **23** | GC HR Data Model Alignment | All above | Analysis phase; requires complete data model |

**Parallelization opportunities:**
- Phase 18 (DQMF) and Phase 20 (O*NET) can develop in parallel after Phase 17
- Phase 21 (JA Enrichment) and Phase 22 (PAA/DRF) can develop in parallel

### v4.0 Anti-Patterns to Avoid

#### 1. Separate Governance Service

**Wrong:**
```
src/
+-- jobforge/          # Data pipeline
+-- governance_svc/    # Separate service
```

**Right:**
```
src/
+-- jobforge/
    +-- governance/    # Integrated module
```

**Why:** JobForge is a single-service architecture. Separate services add deployment complexity without benefit.

#### 2. Database-First Quality Metrics

**Wrong:**
```python
# Create separate quality metrics database
conn = duckdb.connect("data/quality/metrics.duckdb")
conn.execute("CREATE TABLE quality_scores ...")
```

**Right:**
```python
# Store in catalog JSON files (existing pattern)
quality_scores = calculate_scores(table)
save_to_catalog_compliance(quality_scores, "dqmf_scores_{date}.json")
```

**Why:** JobForge uses JSON catalog files for metadata. Adding a separate database fragments the architecture.

#### 3. Heavy Validation Framework

**Wrong:**
```python
# Add Great Expectations with full data context
from great_expectations import DataContext
context = DataContext("gx/")
```

**Right:**
```python
# Use Pandera with Pydantic-style schemas
import pandera.polars as pa
class DimNocSchema(pa.DataFrameModel):
    noc_code: str = pa.Field(str_matches=r"^\d{5}$")
```

**Why:** Great Expectations requires config files and "data context" that conflicts with JobForge's code-first approach.

#### 4. Realtime Quality Monitoring

**Wrong:**
```python
# Calculate quality on every query
@api_app.get("/api/query/data")
async def query_data(request: QueryRequest):
    # Recalculate quality scores
    scores = calculate_quality_scores(tables_used)
    return DataQueryResult(..., quality=scores)
```

**Right:**
```python
# Batch calculate quality scores on schedule/demand
@api_app.get("/api/quality/metrics")
async def get_quality_metrics():
    # Return pre-calculated scores from catalog
    return load_cached_quality_scores()
```

**Why:** Quality calculation is expensive. Batch processing aligns with pipeline architecture.

---

## Orbit Integration Architecture (v2.1 Milestone)

### Overview

Orbit provides a conversational gateway layer that sits between users and the JobForge API. The integration adds a new deployment path without disrupting the existing Power BI deployment.

```
                                 EXISTING ARCHITECTURE
                                 ====================
                                    +-------------------+
                                    |   Power BI        |
                                    |   Semantic Model  |
                                    +--------+----------+
                                             ^
                                             |
                    +------------------------+------------------------+
                    |                   WiQ Gold Layer                |
                    |  24 Parquet tables in data/gold/                |
                    +------------------------+------------------------+
                                             ^
                                             |
                    +------------------------+------------------------+
                    |              Medallion Pipeline                 |
                    |  staged -> bronze -> silver -> gold             |
                    +------------------------------------------------+

                                   NEW: ORBIT INTEGRATION
                                   ======================
                                             |
                                             v
+-------------------------------------------------------------------------------------+
|                              ORBIT GATEWAY (localhost:3000)                          |
|  +-----------------------------------------------------------------------------+    |
|  |                         Intent Classification                                |    |
|  |   "How many developers?" -> DATA_QUERY                                       |    |
|  |   "Where does dim_noc come from?" -> METADATA_QUERY                         |    |
|  |   "Is WiQ DADM compliant?" -> COMPLIANCE_QUERY                              |    |
|  +------------------------------------+----------------------------------------+    |
|                                       |                                             |
|        +------------------------------+------------------------------+              |
|        |                              |                              |              |
|        v                              v                              v              |
|  +------------+                +------------+                +------------+         |
|  | DuckDB     |                | HTTP       |                | HTTP       |         |
|  | Retriever  |                | Adapter    |                | Adapter    |         |
|  | (new)      |                | (meta)     |                | (comply)   |         |
|  +-----+------+                +-----+------+                +-----+------+         |
+--------|-------------------------------|-------------------------------|------------+
         |                               |                               |
         v                               v                               v
+----------------+            +------------------+            +------------------+
| DuckDB         |            | JobForge API     |            | JobForge API     |
| In-Memory      |            | /api/query/      |            | /api/compliance/ |
| (gold/*.parquet)|           | metadata         |            | {framework}      |
+----------------+            +------------------+            +------------------+
```

### Integration Points with Existing System

| Component | Current Role | Orbit Integration Point |
|-----------|--------------|------------------------|
| **data/gold/*.parquet** | Gold layer storage, Power BI source | DuckDBRetriever reads directly via DuckDB views |
| **DataQueryService** | Claude text-to-SQL for FastAPI | Exposed via `/api/query/data` for Orbit HTTP adapter |
| **MetadataQueryService** | Rule-based lineage queries | Exposed via `/api/query/metadata` for Orbit HTTP adapter |
| **GoldQueryEngine** | DuckDB interface for pipeline | Pattern reused by DuckDBRetriever |
| **PipelineConfig** | Path management | Used by DuckDBRetriever for gold_path() |
| **generate_schema_ddl()** | DDL for text-to-SQL prompts | Used by DuckDBRetriever for schema context |

### New Components Required

| Component | Location | Purpose | Dependencies |
|-----------|----------|---------|--------------|
| **DuckDBRetriever** | `orbit/retrievers/duckdb.py` | Orbit retriever for parquet queries | duckdb, anthropic, PipelineConfig |
| **jobforge.yaml** | `orbit/config/adapters/` | Adapter configuration for JobForge | None |
| **wiq_intents.yaml** | `orbit/config/intents/` | Domain-specific intent templates | None |
| **orbit-integration.md** | `docs/` | Integration documentation | None |

---

## System Architecture Overview (Original)

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

## v4.0 Scalability Considerations

| Concern | Current (100 tables) | v4.0 (~150 tables) | Future (500+ tables) |
|---------|----------------------|--------------------|-----------------------|
| Quality metrics calculation | Single-threaded Polars | Parallel per table | Consider Dask/Ray |
| Compliance audit | Sequential | Sequential (acceptable) | Batch with priority queue |
| O*NET API calls | Serial with retry | Batch with asyncio.gather | Rate-limited worker pool |
| Catalog JSON files | Individual files | Individual files | Consider JSON-lines or single DB |
| Policy provenance | Full document scan | Indexed paragraphs | Vector embeddings for semantic search |

---

## Anti-Patterns to Avoid (All Versions)

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

### Anti-Pattern 6: Duplicating Query Logic in Orbit

**What:** Rebuilding DataQueryService logic inside DuckDBRetriever
**Why bad:** Two implementations to maintain; potential drift
**Instead:** DuckDBRetriever can use HTTP adapter to call existing JobForge API, or share code via imports

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
| **Conversational gateway** | Orbit | Custom build | Pre-built UI, intent routing, multi-LLM |
| **Data quality validation** | Pandera[polars] | Great Expectations | Code-first, Pydantic-style (v4.0) |

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

**Orbit Integration:**
- [Orbit GitHub Repository](https://github.com/schmitech/orbit)
- [Orbit Adapters Documentation](https://github.com/schmitech/orbit/blob/main/docs/adapters/adapters.md)
- [MotherDuck - Semantic Layer with DuckDB](https://motherduck.com/blog/semantic-layer-duckdb-tutorial/)

**v4.0 Governance:**
- [GC DQMF Guidance](https://www.canada.ca/en/government/system/digital-government/digital-government-innovations/information-management/guidance-data-quality.html)
- [DAMA DMBOK Framework](https://dama.org/learning-resources/dama-data-management-body-of-knowledge-dmbok/)
- [Pandera Polars Documentation](https://pandera.readthedocs.io/en/latest/polars.html)
