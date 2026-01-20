---
phase: 10-governance-conversational
plan: 02
subsystem: api
tags: [fastapi, claude-api, text-to-sql, metadata-query, conversational]
dependency-graph:
  requires:
    - 10-01 (compliance module)
    - 04-03 (governance query engine)
  provides:
    - HTTP API for conversational queries
    - /api/query/data endpoint (Claude text-to-SQL)
    - /api/query/metadata endpoint (lineage + catalogue)
    - /api/compliance/{framework} endpoint
  affects:
    - Orbit integration
    - External query clients
tech-stack:
  added:
    - anthropic>=0.43.0
    - fastapi>=0.115.0
  patterns:
    - Claude structured outputs for SQL generation
    - DuckDB views over parquet for query execution
    - Rule-based pattern matching for metadata queries
key-files:
  created:
    - src/jobforge/api/__init__.py
    - src/jobforge/api/data_query.py
    - src/jobforge/api/metadata_query.py
    - src/jobforge/api/routes.py
    - src/jobforge/api/schema_ddl.py
    - tests/api/__init__.py
    - tests/api/test_data_query.py
    - tests/api/test_metadata_query.py
    - tests/api/test_routes.py
  modified:
    - pyproject.toml
decisions:
  - id: 10-02-D1
    decision: Use Claude claude-sonnet-4-20250514 with structured outputs for SQL generation
    rationale: Guarantees valid JSON response matching SQLQuery schema
  - id: 10-02-D2
    decision: Extend LineageQueryEngine with catalogue patterns in MetadataQueryService
    rationale: Reuse existing rule-based engine, add describe/columns/count patterns
  - id: 10-02-D3
    decision: Register gold parquet files as DuckDB views for query execution
    rationale: Memory-efficient, leverages DuckDB parquet scanning
metrics:
  duration: 18 minutes
  completed: 2026-01-20
  tests: 36 tests (12 data_query + 11 metadata_query + 13 routes)
---

# Phase 10 Plan 02: Conversational Query HTTP Endpoints Summary

HTTP API for conversational data and metadata queries using Claude text-to-SQL and rule-based lineage patterns, with FastAPI endpoints for Orbit integration.

## Execution Summary

| Task | Name | Commit | Key Files |
|------|------|--------|-----------|
| 1 | Data Query Service with Claude Text-to-SQL | a18cb64 | schema_ddl.py, data_query.py, test_data_query.py |
| 2 | Metadata Query Service and API Routes | 899cfa7 | metadata_query.py, routes.py, test_routes.py |
| 3 | CLI Command and Package Integration | 3114cec | api/__init__.py, commands.py, test_routes.py |

## What Was Built

### 1. Data Query Service (src/jobforge/api/data_query.py)

Converts natural language questions to SQL using Claude structured outputs:

```python
from jobforge.api import DataQueryService

service = DataQueryService()
result = service.query("How many unit groups are in dim_noc?")
# Returns: DataQueryResult(sql="SELECT COUNT(*) as cnt FROM dim_noc", results=[{cnt: 516}], ...)
```

Key components:
- `SQLQuery` model: Structured output schema for Claude
- `DataQueryResult` model: Response including SQL, explanation, results
- `generate_schema_ddl()`: Generates DDL from gold parquet for prompting
- DuckDB views over parquet files for query execution

### 2. Metadata Query Service (src/jobforge/api/metadata_query.py)

Rule-based pattern matching for catalogue and lineage queries:

```python
from jobforge.api import MetadataQueryService

service = MetadataQueryService()
answer = service.query("how many gold tables?")  # "There are 24 tables in the gold layer."
answer = service.query("describe dim_noc")        # Table metadata with columns
answer = service.query("where does dim_noc come from?")  # Falls through to LineageQueryEngine
```

Extended patterns beyond LineageQueryEngine:
- `describe table_name` - Table metadata from catalog
- `what columns in table_name` - Column listing with types
- `how many tables` - Gold layer table count
- `list tables` - All gold tables grouped by prefix
- `how many rows in table_name` - Row count from parquet
- `what is the schema of table_name` - DDL format

### 3. FastAPI Routes (src/jobforge/api/routes.py)

HTTP API endpoints for query access:

| Endpoint | Method | Description |
|----------|--------|-------------|
| /api/query/data | POST | Natural language to SQL (requires ANTHROPIC_API_KEY) |
| /api/query/metadata | POST | Lineage and catalogue queries |
| /api/compliance/{framework} | GET | DADM/DAMA/Classification compliance logs |
| /api/tables | GET | List gold tables |
| /api/health | GET | Health check |

### 4. CLI Command

```bash
jobforge api                    # Start on localhost:8000
jobforge api -p 8080            # Custom port
jobforge api --reload           # Development mode
```

## Architecture Decisions

### D1: Claude Structured Outputs for SQL

Used `anthropic-beta: structured-outputs-2025-11-13` header to guarantee valid JSON matching SQLQuery schema. The model generates SQL, explanation, and tables_used in a single structured response.

### D2: Pattern Extension Architecture

MetadataQueryService wraps LineageQueryEngine and adds catalogue patterns:
1. Try extended patterns first (describe, columns, etc.)
2. Fall back to lineage engine for upstream/downstream queries
3. Return help message for unrecognized patterns

### D3: DuckDB Views Over Parquet

Gold tables are registered as DuckDB views pointing to parquet files:
```sql
CREATE VIEW dim_noc AS SELECT * FROM 'data/gold/dim_noc.parquet'
```
This enables SQL queries without data loading, leveraging DuckDB's parquet scanner.

## Verification Results

```bash
# All API tests pass
pytest tests/api/ -v
# 36 passed (12 data_query + 11 metadata_query + 13 routes)

# API responds correctly
curl http://localhost:8000/api/health
# {"status": "ok"}

curl -X POST http://localhost:8000/api/query/metadata \
     -H "Content-Type: application/json" \
     -d '{"question": "how many gold tables?"}'
# {"question": "how many gold tables?", "answer": "There are 24 tables in the gold layer."}
```

## Dependencies Added

- `anthropic>=0.43.0` - Claude API client for text-to-SQL
- `fastapi>=0.115.0` - HTTP framework for API endpoints

## Deviations from Plan

None - plan executed as written. The compliance endpoint was already functional because Plan 10-01 was executed prior to this plan.

## Next Phase Readiness

API layer complete. Ready for:
- Orbit integration via HTTP endpoints
- Live demo with conversational queries
- External client access to WiQ data

## Files Created/Modified

**Created:**
- `src/jobforge/api/__init__.py` - Package exports
- `src/jobforge/api/schema_ddl.py` - DDL generator
- `src/jobforge/api/data_query.py` - Claude text-to-SQL service
- `src/jobforge/api/metadata_query.py` - Rule-based metadata service
- `src/jobforge/api/routes.py` - FastAPI application and routes
- `tests/api/__init__.py`
- `tests/api/test_data_query.py` - 12 tests
- `tests/api/test_metadata_query.py` - 11 tests
- `tests/api/test_routes.py` - 13 tests

**Modified:**
- `pyproject.toml` - Added anthropic, fastapi dependencies

---
*Summary generated: 2026-01-20*
*Execution time: 18 minutes*
*Tests: 36 passed*
