# Technology Stack

**Project:** JobForge 2.0 - Workforce Intelligence Platform
**Researched:** 2026-01-18 (Updated 2026-01-20 for Orbit integration)
**Overall Confidence:** HIGH (verified via PyPI/official docs)

---

## Executive Summary

This stack is optimized for a Government of Canada workforce intelligence platform with medallion architecture, Power BI deployment, and conversational RAG. The recommendations prioritize:

1. **Microsoft Fabric ecosystem** for Power BI semantic model deployment (semantic-link-labs)
2. **Modern Python data processing** (Polars + DuckDB) over legacy Pandas
3. **Orbit for conversational UI** with HTTP adapter pattern to JobForge API
4. **RDFLib for knowledge graphs** with SKOS vocabulary support
5. **OpenLineage for data governance** artifacts and lineage tracking

---

## Orbit Integration (v3.0 Milestone)

### Summary

Orbit integration requires minimal stack additions because JobForge 2.0 already includes the core dependencies (DuckDB 1.4+, anthropic 0.43+, FastAPI). The primary work is configuration and adapter development, not library installation.

**Key finding:** Orbit does NOT have a built-in DuckDBRetriever. Use HTTP adapter pattern to route queries through JobForge's existing FastAPI endpoints. This keeps DuckDB logic in JobForge and treats Orbit as a UI/routing layer only.

### Required Addition (Optional for Development)

| Package | Version | Purpose | Rationale |
|---------|---------|---------|-----------|
| schmitech-orbit-client | 1.1.6 | CLI testing interface | Test Orbit integration without full UI deployment |

**Installation:**
```bash
pip install schmitech-orbit-client==1.1.6
```

**Note:** This is optional. JobForge API works standalone without Orbit.

### Already in Project (No Changes Needed)

| Package | Current Version | Purpose | Status |
|---------|-----------------|---------|--------|
| duckdb | >=1.4.0 | SQL on Parquet | Current LTS is 1.4.3 (Dec 2025) - compatible |
| anthropic | >=0.43.0 | Claude Structured Outputs | Supports structured-outputs-2025-11-13 beta |
| fastapi | >=0.115.0 | HTTP API endpoints | Already exposes /api/query/* endpoints |
| pydantic | >=2.12.0 | Schema validation | Used for SQLQuery response model |
| httpx | >=0.27.0 | Async HTTP | Already in dependencies |

### Architecture: HTTP Adapter Pattern

```
User Question
     |
     v
+------------------+
|  Orbit Gateway   |  <-- Intent classification, UI, conversation history
|  localhost:3000  |
+--------+---------+
         |
    HTTP calls to JobForge API
         |
         v
+------------------+
|  JobForge API    |  <-- Claude text-to-SQL, DuckDB queries
|  localhost:8000  |
+--------+---------+
         |
         v
+------------------+
|  Gold Parquet    |  <-- 24 tables, star schema
|  data/gold/*.parquet
+------------------+
```

### Why HTTP Adapter Over Custom DuckDBRetriever

| Approach | Pros | Cons |
|----------|------|------|
| **HTTP Adapter (recommended)** | Keep DuckDB logic in JobForge; Orbit is pure UI; no Orbit source modification | Extra HTTP hop (~2ms) |
| Custom DuckDBRetriever | Slightly faster; native Orbit integration | Must maintain code in two repos; Orbit upgrades break adapter |

**Decision:** Use HTTP adapter. The latency difference is negligible vs. Claude API call time (~500-2000ms), and it keeps all data logic in JobForge.

### Orbit Version Details

| Component | Version | Source | Confidence |
|-----------|---------|--------|------------|
| Orbit Server | v2.3.0 | [GitHub releases](https://github.com/schmitech/orbit) | HIGH |
| orbit-client (CLI) | 1.1.6 | [Libraries.io](https://libraries.io/pypi/schmitech-orbit-client) | HIGH |
| Docker image | schmitech/orbit:basic | [Docker README](https://github.com/schmitech/orbit/blob/main/docker/README.md) | HIGH |

### Orbit Installation

```bash
# Option A: Docker (recommended for production)
docker pull schmitech/orbit:basic
docker run -d --name orbit \
  -p 5173:5173 -p 3000:3000 \
  -v $(pwd)/orbit/config:/orbit/config \
  schmitech/orbit:basic

# Option B: Local (for development)
git clone https://github.com/schmitech/orbit.git
cd orbit
cp env.example .env
./install/setup.sh
source venv/bin/activate
./bin/orbit.sh start
```

**System Requirements:**
- Python 3.12+ (Orbit server)
- Node.js 18+ (Orbit web UI)
- 4GB+ RAM for Docker
- 2GB+ disk space

### Claude Structured Outputs Configuration

```python
response = client.messages.create(
    model="claude-sonnet-4-20250514",
    max_tokens=1024,
    extra_headers={"anthropic-beta": "structured-outputs-2025-11-13"},
    response_format={
        "type": "json_schema",
        "json_schema": {
            "name": "sql_query",
            "schema": SQLQuery.model_json_schema(),
        }
    },
    # ...
)
```

**Performance Notes:**
- First request with new schema: +100-300ms (grammar compilation)
- Subsequent requests: No overhead (cached 24 hours)
- Model support: Claude Sonnet 4.5, Opus 4.1 (Haiku 4.5 coming)

### What NOT to Add for Orbit

| Package | Why Not |
|---------|---------|
| langchain | Overkill - Claude Structured Outputs is simpler for text-to-SQL |
| vanna | Requires schema training - Claude with DDL prompt is zero-config |
| raglite | Document RAG - WiQ is structured SQL queries |
| Custom DuckDBRetriever | HTTP adapter provides same functionality with better separation |

---

## Recommended Stack

### Core Data Processing

| Technology | Version | Purpose | Why | Confidence |
|------------|---------|---------|-----|------------|
| **Polars** | 1.37.1 | DataFrame operations, ETL transformations | 3-10x faster than Pandas, native Parquet support, lazy evaluation, Rust-based parallelization. Government-scale data requires performance. | HIGH |
| **DuckDB** | 1.4.3 | SQL analytics on Parquet, medallion layer queries | In-process OLAP, projection/filter pushdown to Parquet, 600x faster than CSV reads. Zero-copy Arrow integration with Polars. | HIGH |
| **PyArrow** | (bundled) | Parquet I/O, Arrow IPC | Both Polars and DuckDB use Arrow natively. Ensures zero-copy data exchange between processing engines. | HIGH |

**Rationale:** The Polars + DuckDB combination is the 2025 standard for high-performance Python ETL. Polars handles DataFrame transformations with lazy evaluation and multi-threading; DuckDB provides SQL interface for complex analytics queries. Both read/write Parquet natively with columnar optimizations.

### Power BI Semantic Model Deployment

| Technology | Version | Purpose | Why | Confidence |
|------------|---------|---------|-----|------------|
| **semantic-link-labs** | 0.12.9 | Semantic model deployment, TOM access, DAX execution | Microsoft's official library for programmatic Power BI deployment. Supports Direct Lake migration, model metadata manipulation, cross-workspace deployment. | HIGH |
| **semantic-link (sempy)** | (Fabric runtime) | Read/write Power BI data, DAX queries | Core SemPy library included in Fabric notebooks. Use for data retrieval from semantic models. | HIGH |

**Critical Note:** semantic-link-labs requires **Python 3.10 or 3.11** (not 3.12+). Plan Python version accordingly.

**Deployment Pattern:**
```python
# semantic-link-labs for deployment
from sempy_labs import deploy_semantic_model, connect_semantic_model

# Deploy Direct Lake model to workspace
with connect_semantic_model(workspace="prod", dataset="JobForge") as tom:
    # Manipulate TOM objects
    tom.model.tables['Occupations'].refresh()
```

**TMDL Integration:** Power BI Desktop (January 2025+) supports TMDL view for human-readable semantic model definitions. Use TMDL for version control; semantic-link-labs for runtime deployment.

### Knowledge Graph / Vocabulary

| Technology | Version | Purpose | Why | Confidence |
|------------|---------|---------|-----|------------|
| **RDFLib** | 7.5.0 | RDF graph operations, SKOS vocabulary, SPARQL | De facto Python RDF library. Built-in SKOS namespace support. JSON-LD, Turtle, N-Triples serialization. | HIGH |
| **pySHACL** | (companion) | RDF validation against SHACL shapes | Validate NOC/O*NET mappings against defined constraints | MEDIUM |

**Use Case:** Index NOC and O*NET vocabularies as SKOS concept schemes for semantic search and vocabulary alignment.

```python
from rdflib import Graph, Namespace
from rdflib.namespace import SKOS

g = Graph()
NOC = Namespace("https://noc.esdc.gc.ca/")
g.bind("noc", NOC)
g.bind("skos", SKOS)
```

### RAG / Conversational Interface

| Technology | Version | Purpose | Why | Confidence |
|------------|---------|---------|-----|------------|
| **LlamaIndex** | 0.14.12 | RAG orchestration, document indexing, query engines | Superior retrieval accuracy (35% improvement in 2025 benchmarks). Designed for document-heavy applications. Multiple index types (vector, tree, KG). | HIGH |
| **Qdrant** | 1.16.2 (client) | Production vector database | Rust-based, 3-4x faster than ChromaDB, HNSW with metadata filtering, horizontal scaling, ACID transactions. Ready for GC production workloads. | HIGH |

**Alternative Considered:** LangChain excels at multi-step agentic workflows but has more overhead. LlamaIndex is optimal for document retrieval + Q&A which matches JobForge's conversational use case.

**Hybrid Pattern:** Use LlamaIndex for retrieval, optionally add LangChain for complex agentic workflows later.

```python
from llama_index.core import VectorStoreIndex
from llama_index.vector_stores.qdrant import QdrantVectorStore

# Production-ready RAG with Qdrant backend
vector_store = QdrantVectorStore(
    collection_name="jobforge_docs",
    client=qdrant_client
)
index = VectorStoreIndex.from_vector_store(vector_store)
query_engine = index.as_query_engine()
```

### Data Governance / Lineage

| Technology | Version | Purpose | Why | Confidence |
|------------|---------|---------|-----|------------|
| **OpenLineage** | 1.42.1 | Lineage event emission, pipeline metadata | Open standard adopted by Airflow, dbt, Spark. Vendor-neutral, JSON schema-based. | HIGH |
| **SQLLineage** | 1.5.7 | Column-level SQL lineage extraction | Parse SQL for lineage, networkx graph storage. Production-stable. | HIGH |

**Governance Architecture:**
- Emit OpenLineage events from each medallion layer transformation
- SQLLineage extracts column-level lineage from transformation SQL
- Export to Purview/Denodo formats (see below)

### Microsoft Purview Integration

| Technology | Version | Purpose | Why | Confidence |
|------------|---------|---------|-----|------------|
| **azure-purview-datamap** | 1.0.0b2 | Catalog API, asset registration, lineage push | Official SDK for Purview Data Map. Beta but actively developed. | MEDIUM |
| **azure-identity** | (companion) | AAD authentication | Required for Purview SDK authentication | HIGH |

**Note:** The older `azure-purview-catalog` (1.0.0b4) has not been updated since June 2022. Use `azure-purview-datamap` for new development.

```python
from azure.purview.datamap import DataMapClient
from azure.identity import DefaultAzureCredential

client = DataMapClient(
    endpoint="https://your-purview.purview.azure.com",
    credential=DefaultAzureCredential()
)
```

### Denodo Integration

| Technology | Version | Purpose | Why | Confidence |
|------------|---------|---------|-----|------------|
| **Denodo AI SDK** | (latest) | Data virtualization, metadata export | Official Denodo Python SDK. Natural language query interface, business metadata enrichment. | MEDIUM |
| **requests** | (standard) | REST API calls to Denodo | Denodo exposes REST endpoints for data access | HIGH |

**Note:** Denodo connectivity typically uses JDBC/ODBC or REST APIs. The AI SDK is newer (2025) and designed for generative AI use cases.

### Data Validation

| Technology | Version | Purpose | Why | Confidence |
|------------|---------|---------|-----|------------|
| **Pydantic** | 2.12.5 | Data validation, schema enforcement | Standard for Python data validation. Type hints, JSON schema generation. | HIGH |
| **pandera** | (companion) | DataFrame validation | Validate Polars/Pandas DataFrames against schemas. Statistical hypothesis testing. | MEDIUM |

### Supporting Libraries

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| **httpx** | latest | Async HTTP client | API calls to Power BI, Denodo REST endpoints |
| **tenacity** | latest | Retry logic | Resilient API calls with exponential backoff |
| **structlog** | latest | Structured logging | JSON logs for GC compliance/audit |
| **python-dotenv** | latest | Environment config | Local development secrets management |
| **typer** | latest | CLI interface | Command-line tools for ETL orchestration |

---

## Alternatives Considered

| Category | Recommended | Alternative | Why Not Alternative |
|----------|-------------|-------------|---------------------|
| DataFrames | Polars | Pandas | Pandas 3-10x slower, single-threaded, higher memory. Use Pandas only for ML library compatibility. |
| SQL Analytics | DuckDB | SQLite | SQLite lacks columnar storage, Parquet pushdown, parallel execution. |
| Vector DB | Qdrant | ChromaDB | ChromaDB lacks sharding, compressed indexes. Fine for prototyping but not GC production scale. |
| Vector DB | Qdrant | FAISS | FAISS is a library not a database. No metadata filtering, persistence, or scaling. |
| RAG Framework | LlamaIndex | LangChain | LangChain adds complexity for pure retrieval. Use LlamaIndex for document Q&A, add LangChain only if agentic workflows needed. |
| Knowledge Graph | RDFLib | Neo4j | Neo4j requires separate server. RDFLib is pure Python, W3C standard RDF/SKOS support, simpler for vocabulary use case. |
| Lineage | OpenLineage | Custom | OpenLineage is the industry standard. Custom lineage creates vendor lock-in. |
| Power BI Deploy | semantic-link-labs | pyadomd/pytabular | pyadomd is Windows-only, inactive development. semantic-link-labs is Microsoft-supported, Fabric-native. |
| Conversational UI | Orbit | Custom React | Orbit provides tested UI, intent routing, multi-LLM support. Custom build takes weeks vs hours. |

---

## What NOT to Use

### Avoid: Pandas for Large ETL
Pandas is single-threaded and memory-inefficient. For datasets >1GB (typical for NOC/O*NET), use Polars. Convert to Pandas only at ML model boundaries.

### Avoid: ChromaDB for Production
ChromaDB is excellent for prototyping but lacks production features (sharding, compression). Start with ChromaDB for development, migrate to Qdrant for production.

### Avoid: pyadomd / XMLA Direct
pyadomd is Windows-only, hasn't been updated in 12+ months, and unsupported in Fabric. Use semantic-link-labs which wraps XMLA with a Pythonic API.

### Avoid: azure-purview-catalog
The older Purview Catalog SDK (1.0.0b4) hasn't been updated since June 2022. Use `azure-purview-datamap` instead.

### Avoid: Delta Lake (for this project)
Delta Lake is excellent for Databricks but adds complexity for a Parquet-based medallion architecture without Databricks/Spark. DuckDB + Parquet provides ACID-like guarantees through atomic writes.

### Avoid: Spark/PySpark
PySpark requires cluster infrastructure. DuckDB + Polars achieves comparable performance for single-node workloads up to ~100GB. Only consider Spark if data exceeds single-node capacity.

### Avoid: LangChain for Text-to-SQL
Claude Structured Outputs (Nov 2025) provides schema-guaranteed JSON without abstraction overhead. LangChain SQLDatabaseChain adds unnecessary complexity for this use case.

---

## Python Version

**Recommended: Python 3.11**

| Constraint | Requirement |
|------------|-------------|
| semantic-link-labs | Python <3.12, >=3.10 |
| Polars | Python >=3.10 |
| DuckDB | Python 3.9-3.14 |
| LlamaIndex | Python >=3.10 |
| Pydantic | Python >=3.8 |
| Orbit (server) | Python >=3.12 (runs separately in Docker) |

Python 3.11 is the sweet spot: compatible with all libraries, stable, and performant. Orbit server runs in its own environment (Docker) with Python 3.12.

---

## Installation

### Core Dependencies

```bash
# Create virtual environment with Python 3.11
python -m venv .venv --python=python3.11
source .venv/bin/activate  # or .venv\Scripts\activate on Windows

# Core data processing
pip install polars==1.37.1 duckdb==1.4.3 pyarrow

# Power BI deployment (Fabric notebooks preferred, but installable locally)
pip install semantic-link-labs==0.12.9

# Knowledge graph
pip install rdflib==7.5.0 pyshacl

# RAG stack
pip install llama-index==0.14.12 qdrant-client==1.16.2

# Data governance
pip install openlineage-python==1.42.1 sqllineage==1.5.7

# Purview integration
pip install azure-purview-datamap azure-identity

# Validation
pip install pydantic==2.12.5 pandera

# Supporting
pip install httpx tenacity structlog python-dotenv typer

# Orbit CLI (optional, for testing)
pip install schmitech-orbit-client==1.1.6
```

### Development Dependencies

```bash
pip install pytest pytest-cov ruff mypy pre-commit
```

### requirements.txt

```
# Core Data Processing
polars>=1.37.0,<2.0.0
duckdb>=1.4.0,<2.0.0
pyarrow>=14.0.0

# Power BI Deployment
semantic-link-labs>=0.12.0,<1.0.0

# Knowledge Graph
rdflib>=7.5.0,<8.0.0
pyshacl>=0.25.0

# RAG Stack
llama-index>=0.14.0,<1.0.0
qdrant-client>=1.16.0,<2.0.0

# Data Governance
openlineage-python>=1.42.0,<2.0.0
sqllineage>=1.5.0,<2.0.0

# Azure/Purview
azure-purview-datamap>=1.0.0b2
azure-identity>=1.15.0

# Validation
pydantic>=2.12.0,<3.0.0
pandera>=0.18.0

# Supporting
httpx>=0.27.0
tenacity>=8.2.0
structlog>=24.0.0
python-dotenv>=1.0.0
typer>=0.12.0
```

---

## Architecture Alignment

| JobForge Component | Primary Stack |
|--------------------|---------------|
| Staged/Bronze/Silver/Gold ETL | Polars + DuckDB + Parquet |
| Power BI Semantic Model | semantic-link-labs + TMDL |
| Vocabulary Index (NOC/ONET) | RDFLib + SKOS |
| Conversational RAG | LlamaIndex + Qdrant |
| Conversational UI | Orbit (HTTP adapter to JobForge API) |
| Data Dictionary Export | Pydantic schemas + OpenLineage |
| Lineage Documentation | OpenLineage + SQLLineage |
| Purview Integration | azure-purview-datamap |
| Denodo Integration | Denodo AI SDK / REST |

---

## Sources

### Official Documentation (HIGH Confidence)
- [PyPI - semantic-link-labs 0.12.9](https://pypi.org/project/semantic-link-labs/)
- [PyPI - Polars 1.37.1](https://pypi.org/project/polars/)
- [PyPI - DuckDB 1.4.3](https://pypi.org/project/duckdb/)
- [PyPI - RDFLib 7.5.0](https://pypi.org/project/rdflib/)
- [PyPI - LlamaIndex 0.14.12](https://pypi.org/project/llama-index/)
- [PyPI - Qdrant Client 1.16.2](https://pypi.org/project/qdrant-client/)
- [PyPI - OpenLineage 1.42.1](https://pypi.org/project/openlineage-python/)
- [PyPI - Pydantic 2.12.5](https://pypi.org/project/pydantic/)
- [Microsoft Learn - Semantic Link](https://learn.microsoft.com/en-us/fabric/data-science/semantic-link-power-bi)
- [Microsoft Learn - Purview Python SDK](https://learn.microsoft.com/en-us/purview/data-gov-python-sdk)
- [DuckDB - Parquet Documentation](https://duckdb.org/docs/stable/data/parquet/overview)
- [DuckDB 1.4.3 LTS Announcement](https://duckdb.org/2025/12/09/announcing-duckdb-143)

### Orbit Integration (HIGH Confidence)
- [schmitech/orbit GitHub](https://github.com/schmitech/orbit) - Orbit repository, v2.3.0 release
- [Orbit Docker README](https://github.com/schmitech/orbit/blob/main/docker/README.md) - Docker deployment guide
- [schmitech-orbit-client on Libraries.io](https://libraries.io/pypi/schmitech-orbit-client) - Version 1.1.6 details

### Claude API (HIGH Confidence)
- [Anthropic Structured Outputs Docs](https://platform.claude.com/docs/en/build-with-claude/structured-outputs) - Official documentation
- [Hands-On with Anthropic Structured Outputs](https://towardsdatascience.com/hands-on-with-anthropics-new-structured-output-capabilities/) - Practical examples

### Framework Comparisons (MEDIUM Confidence)
- [LangChain vs LlamaIndex 2025 Comparison](https://latenode.com/blog/platform-comparisons-alternatives/automation-platform-comparisons/langchain-vs-llamaindex-2025-complete-rag-framework-comparison)
- [Polars vs Pandas Performance 2025](https://dev.to/dataformathub/pandas-vs-polars-why-the-2025-evolution-changes-everything-5ad1)
- [ChromaDB vs Qdrant Comparison](https://aloa.co/ai/comparisons/vector-database-comparison/chroma-vs-qdrant)
- [DuckDB Performance with Parquet](https://www.datacamp.com/tutorial/duckdb-to-speed-up-data-pipelines)

### Power BI Ecosystem (HIGH Confidence)
- [semantic-link-labs GitHub](https://github.com/microsoft/semantic-link-labs)
- [Programmatic Semantic Model Deployment](https://community.fabric.microsoft.com/t5/Power-BI-Community-Blog/Programmatically-deploy-Semantic-Models-and-Reports-via-Semantic/ba-p/4624464)
- [TMDL for Power BI 2025](https://endjin.com/blog/2025/01/why-power-bi-developers-should-care-about-the-tabular-model-definition-language-tmdl)
- [Power BI November 2025 Feature Summary](https://powerbi.microsoft.com/en-us/blog/power-bi-november-2025-feature-summary/)

### Data Governance (MEDIUM Confidence)
- [OpenLineage Python Documentation](https://openlineage.io/docs/client/python/)
- [Denodo AI SDK](https://community.denodo.com/docs/html/document/denodoconnects/latest/en/Denodo%20AI%20SDK%20-%20User%20Manual)
- [Azure Purview DataMap SDK](https://learn.microsoft.com/en-us/python/api/overview/azure/purview-datamap-readme)
