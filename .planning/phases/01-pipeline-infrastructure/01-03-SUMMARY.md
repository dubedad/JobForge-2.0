---
phase: 01-pipeline-infrastructure
plan: 03
subsystem: pipeline
tags: [duckdb, polars, metadata-catalog, sql-query, end-to-end-tests, dama-dmbok]

# Dependency graph
requires:
  - 01-02 (PipelineEngine, layer classes, transition logging)
provides:
  - CatalogManager for table metadata persistence
  - GoldQueryEngine for DuckDB SQL queries on gold layer
  - End-to-end tests verifying all Phase 1 success criteria
  - Phase 1 complete: pipeline infrastructure ready
affects:
  - Phase 2 (data ingestion will use catalog and query interfaces)
  - Phase 5 (data governance will extend catalog metadata)
  - All phases using gold layer data

# Tech tracking
tech-stack:
  added: []
  patterns: [metadata-catalog, duckdb-views, sql-on-parquet, pytest-fixtures]

key-files:
  created:
    - src/jobforge/pipeline/catalog.py
    - src/jobforge/pipeline/query.py
    - tests/test_pipeline_e2e.py
    - tests/fixtures/sample_noc.csv
    - tests/__init__.py
  modified:
    - src/jobforge/pipeline/__init__.py

key-decisions:
  - "CatalogManager saves JSON to catalog/tables/{table_name}.json"
  - "GoldQueryEngine uses DuckDB views for parquet files"
  - "Persistent DuckDB connection within engine instance for efficiency"

patterns-established:
  - "Table metadata as JSON with Pydantic model_dump_json/model_validate_json"
  - "DuckDB CREATE VIEW for gold parquet registration"
  - "pytest fixtures for config/pipeline with tmp_path isolation"

# Metrics
duration: 5min
completed: 2026-01-18
---

# Phase 1 Plan 3: Metadata Catalog Summary

**CatalogManager for table metadata, GoldQueryEngine for DuckDB SQL, and end-to-end tests proving pipeline flows source to gold with provenance**

## Performance

- **Duration:** 5 min
- **Started:** 2026-01-18T19:00:00Z
- **Completed:** 2026-01-18T19:05:00Z
- **Tasks:** 3
- **Files modified:** 6

## Accomplishments

- CatalogManager saves and loads table metadata to catalog/tables/
- GoldQueryEngine registers gold parquet files as DuckDB views
- SQL queries return Polars DataFrames with provenance columns
- End-to-end tests verify all four Phase 1 success criteria
- Pipeline infrastructure complete and ready for Phase 2

## Task Commits

Each task was committed atomically:

1. **Task 1: Create Catalog Manager** - `57ace48` (feat)
2. **Task 2: Create DuckDB Query Interface** - `6161de9` (feat)
3. **Task 3: Create End-to-End Tests** - `880a139` (test)
4. **Exports Update** - `87cda51` (chore)

## Files Created/Modified

- `src/jobforge/pipeline/catalog.py` - CatalogManager, generate_table_metadata, update_catalog_on_transition
- `src/jobforge/pipeline/query.py` - GoldQueryEngine with SQL queries on gold parquet
- `tests/__init__.py` - Test package marker
- `tests/fixtures/sample_noc.csv` - 10-row NOC sample data for testing
- `tests/test_pipeline_e2e.py` - 6 tests covering all Phase 1 success criteria
- `src/jobforge/pipeline/__init__.py` - Updated exports for catalog and query modules

## Key Implementation Details

### CatalogManager

- `generate_table_metadata(parquet_path, layer, domain)` - Reads parquet schema/stats
- `save_table_metadata(metadata)` - Writes to catalog/tables/{name}.json
- `load_table_metadata(table_name)` - Reads and validates with Pydantic
- `list_tables(layer=None)` - Lists tables, optional layer filter
- `get_lineage_logs(batch_id=None)` - Queries transition logs from catalog/lineage/

### GoldQueryEngine

- `register_gold_tables()` - Creates DuckDB views for all gold parquet files
- `query(sql)` - Executes SQL, returns Polars DataFrame
- `query_with_provenance(sql)` - Ensures provenance columns in result
- `get_lineage(table_name)` - Groups by _source_file with row counts
- Context manager support for connection lifecycle

### End-to-End Tests

| Test | Verifies |
|------|----------|
| test_full_pipeline_flow | Source->staged->bronze->silver->gold with provenance |
| test_layer_transitions_logged | Transition logs queryable by batch_id |
| test_gold_queryable_via_duckdb | SQL COUNT and DISTINCT queries work |
| test_provenance_columns_present | _source_file, _batch_id, _layer, _ingested_at |
| test_multiple_runs_independent | Batch isolation between runs |
| test_catalog_tracks_metadata | Lineage logs sorted by time |

## Decisions Made

1. **CatalogManager JSON storage** - Table metadata saved as `{table_name}.json` in catalog/tables/ for easy debugging and human readability.

2. **DuckDB views not tables** - Using `CREATE VIEW` for gold parquet files keeps data in parquet format, no duplication.

3. **Persistent connection** - GoldQueryEngine maintains one DuckDB connection for all queries, avoiding overhead of reconnecting.

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

None - all tasks completed successfully on first attempt.

## User Setup Required

None - no external service configuration required.

## Phase 1 Completion

This plan completes Phase 1 (Pipeline Infrastructure). All success criteria verified by tests:

1. **Pipeline can accept a source file and write it through all four layers** - test_full_pipeline_flow
2. **Each layer produces parquet files with provenance columns** - test_provenance_columns_present
3. **Layer transitions are logged and queryable** - test_layer_transitions_logged
4. **Gold layer output is queryable via DuckDB SQL** - test_gold_queryable_via_duckdb

## Next Phase Readiness

- Pipeline infrastructure complete with all components
- CatalogManager and GoldQueryEngine exported from jobforge.pipeline
- Ready for Phase 2 (Data Ingestion) to use PipelineEngine.run_full_pipeline()
- Sample NOC data fixture available for testing

---
*Phase: 01-pipeline-infrastructure*
*Completed: 2026-01-18*
