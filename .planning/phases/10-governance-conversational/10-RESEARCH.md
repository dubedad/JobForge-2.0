# Phase 10: Governance and Conversational Interface - Research

**Researched:** 2026-01-20
**Domain:** Compliance Traceability Logging, Conversational Data/Metadata Queries
**Confidence:** MEDIUM

## Summary

Phase 10 builds on JobForge's existing governance infrastructure (LineageGraph, LineageQueryEngine, CatalogueGenerator) to deliver three compliance traceability logs and two conversational query interfaces. The compliance logs follow a Requirements Traceability Matrix (RTM) pattern, mapping WiQ artifacts to external frameworks (DADM, DAMA DMBOK, Classification Policy). The conversational interfaces extend the existing rule-based LineageQueryEngine pattern for metadata queries and add a hybrid approach using Claude API with structured outputs for data queries over DuckDB.

The research reveals that:
1. **DADM compliance** requires mapping to specific directive sections (6.1.x, 6.2.x, 6.3.x, etc.) with documented evidence of algorithmic impact assessment, transparency notices, and data quality measures
2. **DAMA DMBOK compliance** aligns with 11 knowledge areas; WiQ already covers Data Governance, Data Architecture, Metadata Management, and Data Quality through existing catalog structure
3. **Conversational data queries** benefit from a hybrid approach: Claude API with structured outputs for SQL generation, DuckDB for query execution on parquet files
4. **Conversational metadata queries** extend the existing rule-based LineageQueryEngine with additional patterns for provenance, lineage, and governance questions

**Primary recommendation:** Use the RTM pattern for all three compliance logs (JSON-based traceability matrices). For the conversational interface, use **Orbit** ([schmitech/orbit](https://github.com/schmitech/orbit)) as the gateway layer — it provides intent-aware routing, multi-LLM support, and pre-built UIs (React, CLI, embeddable widget). JobForge exposes HTTP APIs for data and metadata queries; Orbit handles intent classification and response formatting.

## Standard Stack

The established libraries/tools for this domain:

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| anthropic | 0.43+ | Claude API for text-to-SQL | Structured outputs (beta 2025-11-13) guarantee schema compliance for SQL generation |
| duckdb | 1.1+ | SQL query execution on parquet | Already in project; star schema compatible; fast analytical queries |
| networkx | 3.x | Lineage graph (existing) | Already in use; provides graph traversal for metadata queries |
| pydantic | 2.x | Data models for compliance logs | Already in use; provides validation, JSON serialization |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| structlog | 24.x | Audit logging | Already in use; structured logging for compliance audit trail |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| Claude API | LangChain SQLDatabaseChain | LangChain adds abstraction layer; direct Claude API simpler for focused use case |
| Claude API | Vanna.ai | Vanna requires training on schema; Claude with structured outputs is zero-config |
| DuckDB | Polars direct | DuckDB provides SQL interface matching user expectations; Polars requires API knowledge |

**Installation:**
```bash
pip install anthropic duckdb
# networkx, pydantic, structlog already in project
```

## Orbit: Conversational Gateway

**Repository:** [schmitech/orbit](https://github.com/schmitech/orbit)

### What Orbit Provides

Orbit is a self-hosted gateway that unifies LLM providers with data sources through a single interface:

| Capability | Details |
|------------|---------|
| **LLM Support** | 20+ providers (OpenAI, Anthropic, Google) + local (Ollama, vLLM, llama.cpp) |
| **Intent Routing** | Natural language → SQL, Elasticsearch DSL, MongoDB filters, HTTP API calls |
| **RAG Adapters** | SQL, MongoDB, Elasticsearch, Pinecone, Qdrant, Chroma, Redis, HTTP APIs |
| **Pre-built UIs** | React web app, Python CLI, embeddable JavaScript widget, Node.js SDK |
| **API Compatibility** | OpenAI-compatible endpoint for drop-in replacement |

### How Orbit Enables Phase 10

```
┌─────────────────────────────────────────────────────────────────┐
│                         USER                                     │
│              (React UI / CLI / Widget / API)                    │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                      ORBIT GATEWAY                               │
│  ┌───────────────────────────────────────────────────────────┐  │
│  │              Intent Classification                         │  │
│  │   "How many software developers?" → DATA_QUERY            │  │
│  │   "Where does dim_noc come from?" → METADATA_QUERY        │  │
│  │   "Is WiQ DADM compliant?" → COMPLIANCE_QUERY             │  │
│  └───────────────────────────────────────────────────────────┘  │
│                    │              │              │               │
│              ┌─────┴─────┐  ┌────┴────┐  ┌─────┴─────┐         │
│              │ DuckDB    │  │  HTTP   │  │  HTTP     │         │
│              │ Retriever │  │ Adapter │  │ Adapter   │         │
│              │ (new)     │  │ (meta)  │  │ (comply)  │         │
│              └─────┬─────┘  └────┬────┘  └─────┬─────┘         │
└────────────────────┼─────────────┼─────────────┼────────────────┘
                     │             │             │
                     ▼             ▼             ▼
              ┌───────────┐  ┌──────────┐  ┌──────────┐
              │  DuckDB   │  │ JobForge │  │ JobForge │
              │  Parquet  │  │ /lineage │  │/compliance│
              │  (gold)   │  │   API    │  │   API    │
              └───────────┘  └──────────┘  └──────────┘
```

### What JobForge Needs to Build

**For Orbit integration:**

1. **HTTP API endpoints** (FastAPI or Starlette):
   - `POST /api/query/data` - Accepts question, returns SQL + results
   - `POST /api/query/metadata` - Accepts question, returns lineage/provenance
   - `GET /api/compliance/{framework}` - Returns compliance log (DADM, DAMA, Classification)

2. **DuckDBRetriever for Orbit** (extends Orbit's BaseRetriever):
   ```python
   class DuckDBRetriever(BaseRetriever):
       """Orbit retriever for DuckDB parquet queries."""

       def initialize(self):
           self.conn = duckdb.connect(":memory:")
           # Register all gold tables as views
           for parquet in Path("data/gold").glob("*.parquet"):
               table_name = parquet.stem
               self.conn.execute(f"CREATE VIEW {table_name} AS SELECT * FROM '{parquet}'")

       def retrieve(self, query: str, collection_name: str) -> list[dict]:
           # Use Claude structured outputs for text-to-SQL
           sql = self._generate_sql(query)
           return self.conn.execute(sql).fetchdf().to_dict(orient="records")
   ```

3. **Intent templates for WiQ domain**:
   ```yaml
   # config/adapters/jobforge.yaml
   name: jobforge-wiq
   enabled: true
   type: retriever
   datasource: duckdb
   adapter: intent
   implementation: retrievers.duckdb.DuckDBRetriever
   config:
     parquet_path: "data/gold/"
     schema_file: "data/catalog/schemas/wiq_schema.json"
     domain_templates:
       - occupation_queries.yaml
       - forecast_queries.yaml
       - attribute_queries.yaml
   ```

### Why Orbit Over Custom Build

| Aspect | Custom Build | Orbit |
|--------|--------------|-------|
| **UI Development** | Build React app, CLI, widget from scratch | Pre-built, tested, documented |
| **Multi-LLM** | Implement provider switching | Built-in with unified API |
| **Intent Routing** | Build classifier from scratch | Template-based, configurable |
| **Maintenance** | Own all code | Community-maintained |
| **Time to Demo** | Weeks | Days |

### Orbit Deployment

```bash
# Clone Orbit
git clone https://github.com/schmitech/orbit.git
cd orbit

# Add JobForge adapter config
cp jobforge-adapter.yaml config/adapters/

# Start with Docker
docker-compose up -d

# Or run locally
./bin/orbit.sh start
```

### Gap: DuckDB Retriever Not Built-In

Orbit supports SQLite, PostgreSQL, MySQL but **not DuckDB**. Creating `DuckDBRetriever`:

1. Extend `BaseRetriever` (same pattern as SQLiteRetriever)
2. Use DuckDB's Python API for parquet queries
3. Register in Orbit's retriever factory
4. Configure via `adapters.yaml`

This is ~100 lines of Python, following established patterns.

## Architecture Patterns

### Recommended Project Structure
```
src/jobforge/
  governance/
    __init__.py
    graph.py              # (existing) LineageGraph class
    query.py              # (existing) LineageQueryEngine for metadata
    catalogue.py          # (existing) CatalogueGenerator
    models.py             # (existing) LineageNode, LineageEdge
    compliance/
      __init__.py
      models.py           # ComplianceRequirement, TraceabilityEntry, ComplianceLog
      dadm.py             # DADMTraceabilityLog with section mappings
      dama.py             # DAMATraceabilityLog with knowledge area mappings
      classification.py   # ClassificationTraceabilityLog
    conversational/
      __init__.py
      data_query.py       # DataQueryEngine using Claude + DuckDB
      metadata_query.py   # MetadataQueryEngine extending LineageQueryEngine
```

### Pattern 1: Compliance Traceability Matrix (RTM)

**What:** A JSON-based mapping from external framework requirements to WiQ artifacts demonstrating compliance
**When to use:** For DADM, DAMA DMBOK, and Classification Policy compliance logs
**Example:**
```python
from pydantic import BaseModel, Field
from datetime import datetime
from enum import Enum

class ComplianceStatus(str, Enum):
    COMPLIANT = "compliant"
    PARTIAL = "partial"
    NOT_APPLICABLE = "not_applicable"
    NOT_IMPLEMENTED = "not_implemented"

class TraceabilityEntry(BaseModel):
    """Single requirement-to-evidence mapping."""
    requirement_id: str = Field(description="External requirement ID (e.g., DADM 6.2.3)")
    requirement_text: str = Field(description="Requirement description from source")
    section: str = Field(description="Chapter/section in source framework")
    status: ComplianceStatus
    evidence_type: str = Field(description="Type of evidence (artifact, process, documentation)")
    evidence_references: list[str] = Field(description="Paths/IDs of artifacts demonstrating compliance")
    notes: str = Field(default="", description="Additional context or implementation notes")
    last_verified: datetime

class ComplianceLog(BaseModel):
    """Complete compliance traceability log."""
    framework_name: str
    framework_version: str
    generated_at: datetime
    entries: list[TraceabilityEntry]
    summary: dict[ComplianceStatus, int]
```

### Pattern 2: Claude Text-to-SQL with Structured Outputs

**What:** Use Claude API with structured outputs to generate SQL from natural language, then execute on DuckDB
**When to use:** For conversational data queries over WiQ gold tables
**Example:**
```python
import anthropic
import duckdb
from pydantic import BaseModel

class SQLQuery(BaseModel):
    """Structured output for SQL generation."""
    sql: str
    explanation: str
    tables_used: list[str]

def query_data(question: str, schema_ddl: str) -> dict:
    """Generate and execute SQL from natural language question."""
    client = anthropic.Anthropic()

    # Generate SQL with structured output
    response = client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=1024,
        system="""You are a SQL expert. Given a database schema and question,
        generate a SQL query that answers the question. The database uses DuckDB syntax.
        Only generate SELECT queries - never modify data.""",
        messages=[{
            "role": "user",
            "content": f"""Database schema:
{schema_ddl}

Question: {question}

Generate a SQL query to answer this question."""
        }],
        # Structured output ensures valid JSON
        extra_headers={"anthropic-beta": "structured-outputs-2025-11-13"},
        response_format={
            "type": "json_schema",
            "json_schema": {
                "name": "sql_response",
                "schema": SQLQuery.model_json_schema()
            }
        }
    )

    result = SQLQuery.model_validate_json(response.content[0].text)

    # Execute on DuckDB
    conn = duckdb.connect()
    # Register parquet files as tables
    for table in result.tables_used:
        conn.execute(f"CREATE VIEW {table} AS SELECT * FROM 'data/gold/{table}.parquet'")

    df = conn.execute(result.sql).fetchdf()
    return {
        "query": result.sql,
        "explanation": result.explanation,
        "results": df.to_dict(orient="records"),
        "row_count": len(df)
    }
```

### Pattern 3: Extended Rule-Based Metadata Query

**What:** Extend existing LineageQueryEngine with additional patterns for provenance and governance queries
**When to use:** For conversational metadata queries about lineage, provenance, catalogue
**Example:**
```python
# Additional patterns for MetadataQueryEngine
METADATA_PATTERNS = [
    # Existing lineage patterns from LineageQueryEngine...

    # Provenance patterns
    (re.compile(r"where did (\w+) data come from", re.I), _handle_provenance),
    (re.compile(r"what is the source of (\w+)", re.I), _handle_provenance),

    # Catalogue patterns
    (re.compile(r"describe (?:table )?(\w+)", re.I), _handle_describe_table),
    (re.compile(r"what columns (?:are )?in (\w+)", re.I), _handle_columns),
    (re.compile(r"what tables contain (\w+)", re.I), _handle_search_columns),

    # Governance patterns
    (re.compile(r"who owns (\w+)", re.I), _handle_ownership),
    (re.compile(r"when was (\w+) last updated", re.I), _handle_last_updated),
    (re.compile(r"how many rows in (\w+)", re.I), _handle_row_count),

    # Compliance patterns
    (re.compile(r"is (\w+) dadm compliant", re.I), _handle_dadm_status),
    (re.compile(r"show (?:the )?dadm compliance", re.I), _handle_dadm_summary),
]
```

### Anti-Patterns to Avoid
- **Embedding LLM in every query:** Use rule-based patterns for predictable questions (lineage, metadata); reserve LLM for open-ended data queries
- **Building custom SQL parser:** Use DuckDB's query validation; don't hand-roll SQL sanitization
- **Real-time compliance checks:** Generate compliance logs as batch operation, not per-query
- **Storing compliance evidence inline:** Reference artifacts by path/ID, don't embed full content

## Don't Hand-Roll

Problems that look simple but have existing solutions:

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| SQL injection prevention | Manual string escaping | DuckDB parameterized queries | DuckDB handles escaping; read-only views prevent mutations |
| Schema-to-DDL conversion | Custom formatter | DuckDB `DESCRIBE` + WiQ schema JSON | Schema already documented in JSON format |
| Graph traversal for lineage | Custom BFS/DFS | NetworkX `ancestors()`, `descendants()` | Already implemented in LineageGraph |
| Compliance log format | Custom JSON structure | RTM pattern with Pydantic models | Industry-standard format for traceability |
| Text-to-SQL validation | Custom SQL parser | Claude structured outputs + DuckDB validation | Claude guarantees schema; DuckDB validates syntax |

**Key insight:** The compliance logs are really Requirements Traceability Matrices (RTMs) - a well-established pattern. Don't invent a new structure; use the standard requirement-to-evidence mapping pattern.

## Common Pitfalls

### Pitfall 1: Conflating Data vs Metadata Queries
**What goes wrong:** Using same query engine for "how many software developers in 2025?" (data) vs "where does dim_noc come from?" (metadata)
**Why it happens:** Both feel like "asking the system a question"
**How to avoid:** Route queries based on type: data queries use Claude + DuckDB; metadata queries use rule-based LineageQueryEngine
**Warning signs:** LLM generating SQL for lineage questions; rule-based engine trying to answer analytical questions

### Pitfall 2: Over-Promising DADM Compliance
**What goes wrong:** Claiming "DADM compliant" when system only demonstrates partial coverage
**Why it happens:** Not mapping requirements to actual directive sections with evidence
**How to avoid:** Map each DADM section (6.1.x, 6.2.x, etc.) explicitly; mark gaps as NOT_IMPLEMENTED
**Warning signs:** Generic "we follow DADM" claims without chapter-and-verse references

### Pitfall 3: Hallucinated SQL Columns
**What goes wrong:** Claude generates SQL referencing columns that don't exist
**Why it happens:** Schema not fully provided in prompt; model guessing based on table names
**How to avoid:** Always include full DDL schema in prompt; validate generated SQL against schema before execution
**Warning signs:** DuckDB errors about unknown columns; queries returning unexpected results

### Pitfall 4: Treating Compliance as One-Time
**What goes wrong:** Compliance log generated once and never updated
**Why it happens:** No trigger to regenerate when artifacts change
**How to avoid:** Include compliance log generation in pipeline run; timestamp entries with last_verified
**Warning signs:** Compliance log shows stale timestamps; new tables not appearing in logs

### Pitfall 5: Exposing Raw SQL Errors to Users
**What goes wrong:** DuckDB syntax errors shown directly to users
**Why it happens:** No error handling layer between query execution and response
**How to avoid:** Catch DuckDB exceptions; return user-friendly message with suggestion to rephrase
**Warning signs:** Stack traces in user-facing responses; cryptic SQL error messages

## Code Examples

Verified patterns from official sources:

### Claude Structured Outputs for SQL Generation
```python
# Source: Anthropic Docs - structured-outputs-2025-11-13
import anthropic

client = anthropic.Anthropic()

response = client.messages.create(
    model="claude-sonnet-4-20250514",
    max_tokens=1024,
    extra_headers={"anthropic-beta": "structured-outputs-2025-11-13"},
    system="You are a SQL expert. Generate only SELECT queries for DuckDB.",
    messages=[{"role": "user", "content": f"Schema:\n{schema}\n\nQuestion: {question}"}],
    response_format={
        "type": "json_schema",
        "json_schema": {
            "name": "sql_query",
            "schema": {
                "type": "object",
                "properties": {
                    "sql": {"type": "string"},
                    "explanation": {"type": "string"}
                },
                "required": ["sql", "explanation"]
            }
        }
    }
)
```

### DuckDB Parquet Query Pattern
```python
# Source: DuckDB documentation
import duckdb

conn = duckdb.connect(":memory:")

# Create views for each gold table (read-only)
conn.execute("""
    CREATE VIEW dim_noc AS
    SELECT * FROM 'data/gold/dim_noc.parquet'
""")
conn.execute("""
    CREATE VIEW cops_employment AS
    SELECT * FROM 'data/gold/cops_employment.parquet'
""")

# Execute generated SQL
result = conn.execute("SELECT class_title, COUNT(*) FROM dim_noc GROUP BY 1").fetchdf()
```

### DADM Traceability Entry Example
```python
# Based on DADM Directive section 6.2.3
TraceabilityEntry(
    requirement_id="DADM-6.2.3",
    requirement_text="Provide a meaningful explanation to clients of how and why the decision was made",
    section="6.2 Transparency",
    status=ComplianceStatus.COMPLIANT,
    evidence_type="artifact",
    evidence_references=[
        "data/catalog/lineage/*.json",  # Lineage logs
        "src/jobforge/governance/query.py",  # Explainable query engine
    ],
    notes="Lineage query engine provides provenance explanation for any data point",
    last_verified=datetime.now(timezone.utc)
)
```

### DAMA DMBOK Knowledge Area Mapping
```python
# DAMA DMBOK 11 Knowledge Areas mapped to WiQ artifacts
DAMA_MAPPINGS = {
    "1_data_governance": {
        "name": "Data Governance",
        "wiq_artifacts": ["src/jobforge/governance/"],
        "status": ComplianceStatus.COMPLIANT,
    },
    "2_data_architecture": {
        "name": "Data Architecture",
        "wiq_artifacts": ["data/catalog/schemas/wiq_schema.json"],
        "status": ComplianceStatus.COMPLIANT,
    },
    "3_data_modeling_design": {
        "name": "Data Modeling and Design",
        "wiq_artifacts": ["data/catalog/schemas/"],
        "status": ComplianceStatus.COMPLIANT,
    },
    "4_data_storage_operations": {
        "name": "Data Storage and Operations",
        "wiq_artifacts": ["data/gold/*.parquet", "src/jobforge/pipeline/"],
        "status": ComplianceStatus.COMPLIANT,
    },
    "5_data_security": {
        "name": "Data Security",
        "wiq_artifacts": [],
        "status": ComplianceStatus.NOT_APPLICABLE,
        "notes": "WiQ uses public occupational data; no PII"
    },
    "6_data_integration": {
        "name": "Data Integration and Interoperability",
        "wiq_artifacts": ["src/jobforge/ingestion/", "src/jobforge/external/"],
        "status": ComplianceStatus.COMPLIANT,
    },
    "7_metadata_management": {
        "name": "Metadata Management",
        "wiq_artifacts": ["data/catalog/tables/", "data/catalog/lineage/"],
        "status": ComplianceStatus.COMPLIANT,
    },
    "8_data_quality": {
        "name": "Data Quality",
        "wiq_artifacts": ["src/jobforge/pipeline/transforms.py"],
        "status": ComplianceStatus.COMPLIANT,
    },
    "9_reference_master_data": {
        "name": "Reference and Master Data",
        "wiq_artifacts": ["data/gold/dim_noc.parquet", "data/gold/dim_occupations.parquet"],
        "status": ComplianceStatus.COMPLIANT,
    },
    "10_data_warehousing_bi": {
        "name": "Data Warehousing and Business Intelligence",
        "wiq_artifacts": ["data/gold/", "src/jobforge/deployment/"],
        "status": ComplianceStatus.COMPLIANT,
    },
    "11_document_content": {
        "name": "Document and Content Management",
        "wiq_artifacts": [],
        "status": ComplianceStatus.NOT_APPLICABLE,
        "notes": "WiQ focuses on structured data, not document management"
    },
}
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| LangChain SQLDatabaseChain | Claude structured outputs | 2025 | Simpler implementation, guaranteed schema compliance |
| Custom prompt engineering | Structured outputs beta | Nov 2025 | No more parsing JSON from freeform text |
| Manual compliance documentation | RTM pattern with automation | Always | Auditable, maintainable compliance logs |
| LLM for all queries | Hybrid: rule-based + LLM | 2025 | Lower latency for predictable queries, LLM for open-ended |

**Deprecated/outdated:**
- LangChain SQLDatabaseChain: Still works but structured outputs are simpler for focused use cases
- Manual SQL validation: DuckDB + structured outputs handles this automatically
- Compliance spreadsheets: JSON-based RTMs are version-controllable and queryable

## Open Questions

Things that couldn't be fully resolved:

1. **Classification Policy Source**
   - What we know: NOC is the national occupational classification standard
   - What's unclear: Specific "Classification Policy, Process and Practice" document for federal job classification
   - Recommendation: Map to NOC structure requirements; ask user for specific policy document reference

2. **DADM Algorithmic Impact Assessment (AIA)**
   - What we know: DADM 6.1.1-6.1.3 requires AIA before production
   - What's unclear: Whether WiQ's imputation qualifies as "automated decision system"
   - Recommendation: Document that WiQ is decision-support (provides data), not decision-making; may not require AIA

3. **Query Routing Logic**
   - What we know: Need to distinguish data queries from metadata queries
   - What's unclear: Best approach for ambiguous queries ("tell me about dim_noc")
   - Recommendation: Default to metadata interpretation; add explicit "query data" prefix for data queries

4. **Claude API Cost Management**
   - What we know: Each data query requires Claude API call
   - What's unclear: Expected query volume; cost implications
   - Recommendation: Cache common queries; implement query result caching with TTL

## Sources

### Primary (HIGH confidence)
- [DADM Directive - Treasury Board](https://www.tbs-sct.canada.ca/pol/doc-eng.aspx?id=32592) - Official directive text, section numbers
- [Anthropic Structured Outputs](https://platform.claude.com/docs/en/build-with-claude/structured-outputs) - Claude API structured output documentation
- [Anthropic SQL Cookbook](https://github.com/anthropics/anthropic-cookbook/blob/main/misc/how_to_make_sql_queries.ipynb) - Text-to-SQL patterns
- [Orbit - schmitech/orbit](https://github.com/schmitech/orbit) - Conversational gateway with intent routing
- [Orbit Adapters Documentation](https://github.com/schmitech/orbit/blob/main/docs/adapters/adapters.md) - SQL adapter patterns
- Existing codebase: `governance/graph.py`, `governance/query.py` - Established patterns

### Secondary (MEDIUM confidence)
- [DAMA DMBOK Framework - Atlan](https://atlan.com/dama-dmbok-framework/) - 11 knowledge areas overview
- [DAMA International](https://dama.org/learning-resources/dama-data-management-body-of-knowledge-dmbok/) - Official DMBOK reference
- [Requirements Traceability Matrix - Perforce](https://www.perforce.com/resources/alm/requirements-traceability-matrix) - RTM pattern
- [National Occupational Classification](https://noc.esdc.gc.ca/) - NOC structure and standards
- [Orbit Tutorial](https://github.com/schmitech/orbit/blob/main/docs/tutorial.md) - Setup and intent routing

### Tertiary (LOW confidence)
- [Text-to-SQL State of Art - VLDB 2025](https://www.vldb.org/pvldb/vol18/p5466-luo.pdf) - Academic survey (may be stale)
- [Vanna.ai DuckDB](https://github.com/vanna-ai/vanna) - Alternative approach (not recommended for this use case)
- [Audit Logging Patterns](https://microservices.io/patterns/observability/audit-logging.html) - General patterns

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH - Claude structured outputs verified, DuckDB already in use
- Architecture: HIGH - Orbit provides battle-tested intent routing and UI layer
- Compliance mappings: MEDIUM - DADM sections verified; DAMA knowledge areas verified; Classification Policy needs user input
- Conversational patterns: HIGH - Orbit handles UI/routing; JobForge just exposes HTTP API
- Orbit integration: MEDIUM - DuckDBRetriever needs to be built; follows established patterns

**Research date:** 2026-01-20 (updated with Orbit research)
**Valid until:** 30 days (DADM directive under review; Orbit actively maintained)

---

## Alignment with Existing Infrastructure

### What Already Exists
1. **LineageGraph** (`governance/graph.py`): NetworkX DAG with 106 nodes, 79 edges; `get_upstream()`, `get_downstream()`, `get_path()`
2. **LineageQueryEngine** (`governance/query.py`): Rule-based NL query with 7 patterns; `query()` method
3. **CatalogueGenerator** (`governance/catalogue.py`): Generates TableMetadata from WiQ schema
4. **TableMetadata** (`pipeline/models.py`): 24 table metadata files in `data/catalog/tables/`
5. **LayerTransitionLog**: 130+ lineage JSON files in `data/catalog/lineage/`
6. **DuckDB**: Already used for parquet queries in pipeline

### What Needs to Be Built

**Compliance Logs (GOV-02, GOV-03, GOV-04):**
1. `compliance/models.py` - ComplianceRequirement, TraceabilityEntry, ComplianceLog
2. `compliance/dadm.py` - DADMTraceabilityLog with section 6.x mappings
3. `compliance/dama.py` - DAMATraceabilityLog with 11 knowledge area mappings
4. `compliance/classification.py` - ClassificationTraceabilityLog for NOC-based classification

**JobForge HTTP API (for Orbit integration):**
1. `api/routes.py` - FastAPI/Starlette routes for data, metadata, and compliance queries
2. `api/data_query.py` - DataQueryService using Claude + DuckDB (same logic, exposed via HTTP)
3. `api/metadata_query.py` - MetadataQueryService wrapping LineageQueryEngine

**Orbit Integration (GOV-05, GOV-06):**
1. `DuckDBRetriever` - Orbit retriever for parquet queries (~100 lines)
2. `jobforge-adapter.yaml` - Orbit adapter configuration for WiQ
3. Intent templates - Domain-specific query templates for occupations, forecasts, attributes

### Integration Points
- Read from: `config.catalog_tables_path()` for table metadata
- Read from: `config.catalog_lineage_path()` for lineage logs
- Read from: `config.gold_path()` for parquet files (DuckDB)
- Write to: `config.catalog_path() / "compliance/"` for compliance logs
- Expose: HTTP API at `localhost:8000/api/` for Orbit to call
- Deploy: Orbit gateway at `localhost:3000` with JobForge adapters

### Revised Plan Structure

| Plan | Focus | Deliverables |
|------|-------|--------------|
| **10-01** | Compliance Logs | RTM models, DADM/DAMA/Classification logs, CLI commands |
| **10-02** | JobForge HTTP API | FastAPI app, data query endpoint, metadata query endpoint |
| **10-03** | Orbit Integration | DuckDBRetriever, adapter config, intent templates, deployment |
